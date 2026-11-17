"""Local append-only research history. No replay engine, prompts or invalid candidates."""

import json
import math
import re
from dataclasses import asdict

from petrus_engine.rag.query import plan_query
from petrus_engine.rag.retrieval import CANDIDATES, RRF_K, SECTION_BOOST
from petrus_engine.rag.validation import CODES, validate_answer
from petrus_engine.research import ResearchEvidenceService, canonical, fingerprint, sha256, timestamp

PAYLOAD_LIMIT = 2_500_000
ANSWER_LIMIT = 2_000_000
ACTORS = {
    "claim_created": "user",
    "claim_statement_updated": "user",
    "claim_note_updated": "user",
    "claim_review_status_changed": "user",
    "claim_evidence_linked": "user",
    "claim_evidence_relation_changed": "user",
    "claim_evidence_unlinked": "user",
    "claim_archived": "user",
    "claim_restored": "user",
    "session_created": "user",
    "question_asked": "user",
    "retrieval_completed": "system",
    "ask_accepted": "ai",
    "ask_abstained": "ai",
    "ask_rejected": "system",
    "ask_generation_failed": "system",
    "ask": "user",
    "evidence_saved": "user",
    "evidence_decision_changed": "user",
    "evidence_note_updated": "user",
    "evidence_removed": "user",
    "trail_tracking_started": "system",
}
FORBIDDEN = {
    "reasoning",
    "reasoning_content",
    "system_prompt",
    "raw_candidate",
    "raw_candidates",
    "raw_error",
    "raw_output",
}
SOURCE_KEYS = (
    "paper_id",
    "paper_sha256",
    "paper_title_snapshot",
    "paper_doi_snapshot",
    "evidence_unit_id",
    "section_heading_snapshot",
    "evidence_role",
    "provenance_level",
    "page_start",
    "page_end",
    "supports_paginated_evidence",
    "text_sha256",
    "created_at",
)


def append_event(db, session_id, kind, payload, *, actor=None, object_type=None, object_id=None):
    ResearchEvidenceService.require_session(db, session_id)
    if kind not in ACTORS:
        raise ValueError("trail.invalidEvent")
    actor = ACTORS[kind] if actor is None else actor
    if actor not in ("user", "ai", "system") or (
        actor != ACTORS[kind] and not (kind == "ask_abstained" and actor == "system")
    ):
        raise ValueError("trail.invalidActor")

    if not isinstance(payload, dict):
        raise ValueError("trail.invalidPayload")

    def check(value):
        if isinstance(value, dict):
            if FORBIDDEN & value.keys():
                raise ValueError("trail.invalidPayload")
            for child in value.values():
                check(child)
        elif isinstance(value, list):
            for child in value:
                check(child)

    check(payload)
    encoded = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False)
    if len(encoded.encode()) > PAYLOAD_LIMIT:
        raise ValueError("trail.payloadTooLarge")
    created = timestamp().replace("T", " ").removesuffix("Z")
    cursor = db.execute(
        """INSERT INTO research_events(session_id,event_type,actor_type,object_type,object_id,
        payload_version,legacy,payload_json,created_at) VALUES(?,?,?,?,?,1,0,?,?)""",
        (
            session_id,
            kind,
            actor,
            object_type,
            str(object_id) if object_id is not None else None,
            encoded,
            created,
        ),
    )
    return cursor.lastrowid


def source_snapshot(row, include_text=False):
    result = {key: row[key] for key in SOURCE_KEYS}
    if include_text:
        result["text_snapshot"] = row["text_snapshot"]
    return result


def record_evidence(db, row, kind, **changes):
    payload = {key: row[key] for key in ("id", "session_id", "paper_id", "evidence_fingerprint")}
    payload.update(source_snapshot(row))
    payload.update(
        {
            key: row[key]
            for key in ("origin_type", "research_event_id", "question_snapshot", "evidence_label_snapshot")
        }
    )
    payload.update(changes)
    if kind == "evidence_saved":
        payload["source_snapshot"] = source_snapshot(row, include_text=True)
    if kind == "evidence_removed":
        saved = db.execute(
            "SELECT id,legacy FROM research_events WHERE session_id=? AND object_type='research_evidence' AND object_id=? AND event_type='evidence_saved' ORDER BY id LIMIT 1",
            (row["session_id"], str(row["id"])),
        ).fetchone()
        if saved:
            payload["evidence_saved_event_id"] = saved["id"]
        # Old saved events have no durable source text: capture the existing snapshot now, never rewrite the old event.
        if not saved or saved["legacy"]:
            payload["source_snapshot"] = source_snapshot(row, include_text=True)
    identifier = append_event(
        db, row["session_id"], kind, payload, object_type="research_evidence", object_id=row["id"]
    )
    db.execute("UPDATE research_sessions SET updated_at=? WHERE id=?", (timestamp(), row["session_id"]))
    return identifier


class RetrievalObservation:
    """Observe existing calls/results without extra retrieval, altered scores or model calls."""

    def __init__(self, retriever, database):
        self.retriever, self.database = retriever, database
        self.sources, self.hits, self.completed = [], {}, False
        for name in ("lexical_search", "semantic_search"):
            original = getattr(retriever, name)

            def observe(*args, _original=original, _name=name, **kwargs):
                hits = _original(*args, **kwargs)
                self.sources.append(
                    {
                        "source": _name,
                        "returned_count": len(hits),
                        "unit_ids": [hit.unit.unit_id for hit in hits],
                        "query_sha256": sha256(args[0] if args else kwargs["query"]),
                    }
                )
                return hits

            setattr(retriever, name, observe)

    def hybrid_search(self, *args, **kwargs):
        hits = self.retriever.hybrid_search(*args, **kwargs)
        try:
            with self.database.connect() as db:
                hashes = {
                    row["id"]: row["file_hash"] for row in db.execute("SELECT id,file_hash FROM papers")
                }
            for hit in hits:
                unit = hit.unit
                self.hits[unit.unit_id] = {
                    "unit_id": unit.unit_id,
                    "paper_id": unit.paper_id,
                    "paper_sha256": hashes.get(unit.paper_id),
                    "text_sha256": sha256(unit.text),
                    "evidence_fingerprint": fingerprint(unit, hashes[unit.paper_id])[0]
                    if unit.paper_id in hashes
                    else None,
                    "provenance": str(unit.provenance_level),
                    "page_start": unit.page_start,
                    "page_end": unit.page_end,
                    "evidence_role": unit.evidence_role,
                    "supports_paginated_evidence": unit.supports_paginated_evidence,
                    "lexical_rank": hit.lexical_rank,
                    "semantic_rank": hit.semantic_rank,
                    "score": hit.score if math.isfinite(hit.score) else None,
                    "hybrid_score": hit.hybrid_score,
                    "section_boost": hit.section_boost,
                }
            self.completed = True
        except Exception:
            # Observability must never turn a successful retrieval into a fallback.
            self.hits, self.completed = {}, False
        return hits


def safe_plan(value, question):
    plan = asdict(plan_query(question))
    if isinstance(value, dict):
        for key in plan:
            candidate = value.get(key)
            if key in ("expanded_terms", "warnings"):
                if isinstance(candidate, list) and all(isinstance(x, str) for x in candidate):
                    plan[key] = candidate
            elif isinstance(candidate, str):
                plan[key] = candidate
    return plan


class ResearchTrailService:
    def __init__(self, database):
        self.database = database

    def begin(self, session_id, question):
        if not isinstance(question, str) or not question.strip() or len(question) > 2000:
            raise ValueError("ask_invalid_question")
        plan = plan_query(question)
        with self.database.connect() as db:
            return append_event(
                db,
                session_id,
                "question_asked",
                {
                    "question": question,
                    "question_sha256": sha256(question),
                    "language": plan.detected_language,
                },
                object_type="question",
            )

    def finish(self, session_id, question_id, response, observation, settings, llm, provider):
        evidence = response.get("evidence", [])
        selected = []
        for item in evidence:
            observed = observation.hits.get(item["unit_id"]) if observation.completed else None
            identity = observed or {
                key: item.get(key)
                for key in (
                    "unit_id",
                    "paper_id",
                    "provenance",
                    "page_start",
                    "page_end",
                    "evidence_role",
                    "supports_paginated_evidence",
                )
            }
            selected.append(
                {**identity, "evidence_id": item["evidence_id"], "text_sha256": sha256(item["text"])}
            )
        retrieval = response.get("retrieval_metadata", {})
        fallback = "semantic_unavailable_lexical_fallback" in response.get("limitations", [])
        config = {
            "rrf_k": RRF_K,
            "candidate_budget_per_source": CANDIDATES,
            "requested_returned_hits": 30,
            "section_boost": SECTION_BOOST,
            "include_bibliography": False,
            "max_hits_per_paper": 2,
            "selection_max_units": 8,
            "selection_max_characters": 12000,
            "serialized_context_max_characters": 12000,
            "near_duplicate_jaccard_threshold": 0.92,
            "provenance_priority": {
                "coordinate": 0,
                "exact_page_alignment": 0,
                "section_only": 1,
                "basic_page_text": 2,
            },
            "embedding_provider_id": getattr(provider, "provider_id", None),
            "embedding_model_id": getattr(provider, "model_id", None),
            "embedding_dimension": getattr(provider, "dimension", None),
            "embedding_max_chars": settings.get("embedding_max_chars", 6000),
            "effective_strategy": "lexical_fallback" if fallback else ("hybrid" if provider else "lexical"),
            "ranking_observed": observation.completed,
            "expansion_used": bool(retrieval.get("query_plan", {}).get("expanded_terms")) and not fallback,
        }
        payload = {
            "question_event_id": question_id,
            "returned_candidate_count": retrieval.get("retrieved"),
            "selected_count": len(selected),
            "paper_ids": sorted({e["paper_id"] for e in selected}),
            "selected": selected,
            "observed_sources": observation.sources,
            "query_plan": safe_plan(retrieval.get("query_plan"), response["question"]),
            "configuration": config,
            "context_characters": retrieval.get("context_characters"),
        }
        payload["retrieval_context_sha256"] = sha256(
            canonical({"selected": selected, "query_plan": payload["query_plan"], "configuration": config})
        )
        execution = response.get("execution_metadata", {})
        status = execution.get("final_status", "generation_failed")
        abstained = status == "no_evidence" or (
            status == "accepted" and response.get("insufficient_evidence") is True
        )
        kind = (
            "ask_abstained"
            if abstained
            else {"accepted": "ask_accepted", "rejected": "ask_rejected"}.get(status, "ask_generation_failed")
        )
        errors = [
            CODES[e["category"]]
            for e in execution.get("final_validation_errors", [])
            if isinstance(e, dict) and e.get("category") in CODES
        ]
        result = {
            "question_event_id": question_id,
            "final_status": status,
            "generation_attempts": execution.get("generation_attempts", 0),
            "repair_attempted": execution.get("repair_attempted", False),
            "validation_codes": list(dict.fromkeys(errors)),
            "provider_id": getattr(llm, "provider_id", None),
            "model_id": getattr(llm, "model_id", None),
            "selected": selected,
            "citations": [],
            "insufficient_evidence": bool(response.get("insufficient_evidence")),
            "configuration": {
                key: settings.get(key)
                for key in (
                    "llm_provider",
                    "llm_endpoint",
                    "llm_model",
                    "llm_temperature",
                    "llm_reasoning",
                    "llm_context_length",
                    "llm_max_output_tokens",
                    "llm_timeout_seconds",
                    "llm_query_expansion",
                )
            },
        }
        error_code = execution.get("generation_error")
        if (
            isinstance(error_code, str)
            and len(error_code) <= 128
            and re.fullmatch(r"llm_[a-z_]+(?:_\d{3})?", error_code)
        ):
            result["generation_error_code"] = error_code
        if status == "accepted":
            _, _, validated_citations = validate_answer(response, {e["evidence_id"] for e in evidence})
            answer = response["answer"]
            if len(answer.encode()) > ANSWER_LIMIT:
                raise ValueError("trail.answerTooLarge")
            result.update(
                answer=answer,
                answer_sha256=sha256(answer),
                citations=validated_citations,
                citation_count=len(validated_citations),
            )
        elif abstained:
            # Core's localized, canonical no-evidence response is the only content here.
            from petrus_engine.rag.ask import INSUFFICIENT

            answer = INSUFFICIENT[plan_query(response["question"]).detected_language]
            result.update(answer=answer, answer_sha256=sha256(answer))
        with self.database.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            retrieval_id = append_event(
                db, session_id, "retrieval_completed", payload, object_type="question", object_id=question_id
            )
            result["retrieval_event_id"] = retrieval_id
            result_id = append_event(
                db,
                session_id,
                kind,
                result,
                actor="system" if status == "no_evidence" else None,
                object_type="question",
                object_id=question_id,
            )
            return {
                "state": "recorded",
                "session_id": session_id,
                "question_event_id": question_id,
                "retrieval_event_id": retrieval_id,
                "result_event_id": result_id,
            }

    def fail(self, session_id, question_id):
        with self.database.connect() as db:
            append_event(
                db,
                session_id,
                "ask_generation_failed",
                {
                    "question_event_id": question_id,
                    "final_status": "generation_failed",
                    "generation_error_code": "llm_generation_failed",
                },
                object_type="question",
                object_id=question_id,
            )

    @staticmethod
    def metadata(row):
        try:
            payload = json.loads(row["payload_json"] or "{}")
        except ValueError:
            return {}
        # Never expose arbitrary legacy/server diagnostic fields.
        allowed = {
            "claim_id",
            "claim_evidence_id",
            "saved_evidence_id",
            "statement_snapshot",
            "statement_sha256",
            "new_statement_snapshot",
            "old_statement_sha256",
            "new_statement_sha256",
            "researcher_note_snapshot",
            "review_status",
            "old_review_status",
            "new_review_status",
            "relation",
            "old_relation",
            "new_relation",
            "source_snapshot_event_id",
            "paper_id_snapshot",
            "decision_at_link",
            "title",
            "stage",
            "prior_activity_may_be_incomplete",
            "question",
            "question_sha256",
            "language",
            "question_event_id",
            "retrieval_event_id",
            "ask_result_event_id",
            "retrieval_context_sha256",
            "returned_candidate_count",
            "selected_count",
            "paper_ids",
            "selected",
            "observed_sources",
            "query_plan",
            "configuration",
            "context_characters",
            "final_status",
            "generation_attempts",
            "repair_attempted",
            "validation_codes",
            "generation_error_code",
            "provider_id",
            "model_id",
            "citations",
            "citation_count",
            "insufficient_evidence",
            "answer",
            "answer_sha256",
            "id",
            "session_id",
            "paper_id",
            "evidence_fingerprint",
            *SOURCE_KEYS,
            "origin_type",
            "research_event_id",
            "question_snapshot",
            "evidence_label_snapshot",
            "decision",
            "previous",
            "new",
            "old_decision",
            "new_decision",
            "old_note_sha256",
            "new_note_sha256",
            "new_note_snapshot",
            "source_snapshot",
            "evidence_saved_event_id",
        }
        result = {k: v for k, v in payload.items() if k in allowed}
        if row["event_type"] == "ask" and "evidence" in payload:
            result["selected"] = [
                {
                    k: e[k]
                    for k in ("evidence_id", "unit_id", "paper_id", "provenance", "page_start", "page_end")
                    if k in e
                }
                for e in payload.get("evidence", [])
                if isinstance(e, dict)
            ]
            result["final_status"] = payload.get("execution_metadata", {}).get("final_status")
            try:
                # Historical saved snapshots omitted limitations. Recheck their actual
                # answer/citations without inventing missing historical limitations.
                _, _, citations = validate_answer(
                    {**payload, "limitations": payload.get("limitations", [])},
                    {e["evidence_id"] for e in result["selected"]},
                )
                result.update(citations=citations, citation_count=len(citations))
            except (ValueError, KeyError):
                result.pop("answer", None)
                result.pop("answer_sha256", None)

        # New writers already whitelist nested metadata. Legacy structures are not forwarded wholesale.
        if row["legacy"]:
            for key in ("configuration", "query_plan", "source_snapshot", "observed_sources"):
                result.pop(key, None)
        return result

    def project(self, db, row, details=False):
        metadata = self.metadata(row)
        if not details:
            compact = {
                "claim_id",
                "claim_evidence_id",
                "saved_evidence_id",
                "review_status",
                "old_review_status",
                "new_review_status",
                "relation",
                "old_relation",
                "new_relation",
                "source_snapshot_event_id",
                "title",
                "selected_count",
                "citation_count",
                "returned_candidate_count",
                "paper_ids",
                "paper_id",
                "paper_title_snapshot",
                "section_heading_snapshot",
                "page_start",
                "page_end",
                "decision",
                "previous",
                "new",
                "old_decision",
                "new_decision",
                "final_status",
                "generation_attempts",
                "repair_attempted",
                "evidence_label_snapshot",
                "origin_type",
                "question_event_id",
                "retrieval_event_id",
                "ask_result_event_id",
                "research_event_id",
                "evidence_saved_event_id",
                "evidence_fingerprint",
                "new_note_sha256",
                "old_note_sha256",
            }
            metadata = {k: v for k, v in metadata.items() if k in compact}
        object_id = row["object_id"]
        available = (
            row["object_type"] == "research_evidence"
            and db.execute("SELECT 1 FROM research_evidence WHERE id=?", (object_id,)).fetchone() is not None
        )
        links = []
        full = self.metadata(row)
        for field in (
            "question_event_id",
            "retrieval_event_id",
            "ask_result_event_id",
            "research_event_id",
            "evidence_saved_event_id",
            "source_snapshot_event_id",
        ):
            value = full.get(field)
            reference = (
                db.execute("SELECT id,session_id FROM research_events WHERE id=?", (value,)).fetchone()
                if type(value) is int
                else None
            )
            if reference:
                links.append(
                    {"field": field, "event_id": reference["id"], "session_id": reference["session_id"]}
                )
        paper_ids = set(full.get("paper_ids", []))
        if type(full.get("paper_id")) is int:
            paper_ids.add(full["paper_id"])
        for identity in full.get("selected", []):
            if isinstance(identity, dict) and type(identity.get("paper_id")) is int:
                paper_ids.add(identity["paper_id"])
        paper_links = [
            {
                "paper_id": identifier,
                "available": bool(
                    db.execute(
                        "SELECT 1 FROM paper_files WHERE paper_id=? AND available=1", (identifier,)
                    ).fetchone()
                ),
            }
            for identifier in sorted(paper_ids)
            if type(identifier) is int
        ]
        return {
            **({"claim_id": int(object_id)} if row["object_type"] == "research_claim" else {}),
            "paper_links": paper_links,
            "id": row["id"],
            "session_id": row["session_id"],
            "event_type": "ask_saved_to_session" if row["event_type"] == "ask" else row["event_type"],
            "actor_type": row["actor_type"],
            "object_type": row["object_type"],
            "object_id": object_id,
            "created_at": row["created_at"],
            "payload_version": row["payload_version"],
            "legacy": bool(row["legacy"]),
            "payload_sha256": sha256(row["payload_json"] or ""),
            "metadata": metadata,
            "event_links": links,
            "evidence_available": bool(available),
        }

    def list(self, params):
        session = params.get("session_id")
        limit = params.get("limit", 50)
        actor = params.get("actor_type", "all")
        if type(limit) is not int or not 1 <= limit <= 100:
            raise ValueError("trail.invalidLimit")
        if actor not in ("all", "user", "ai", "system"):
            raise ValueError("trail.invalidActor")
        with self.database.connect() as db:
            ResearchEvidenceService.require_session(db, session)
            cursor = params.get("after_event_id")
            stamp = ""
            if cursor is not None:
                if type(cursor) is not int:
                    raise ValueError("trail.invalidCursor")
                row = db.execute(
                    "SELECT created_at FROM research_events WHERE id=? AND session_id=?", (cursor, session)
                ).fetchone()
                if not row:
                    raise ValueError("trail.invalidCursor")
                stamp = row["created_at"]
            rows = db.execute(
                """SELECT * FROM research_events WHERE session_id=? AND (?='all' OR actor_type=?)
                AND (? IS NULL OR created_at>? OR (created_at=? AND id>?)) ORDER BY created_at ASC,id ASC LIMIT ?""",
                (session, actor, actor, cursor, stamp, stamp, cursor, limit + 1),
            ).fetchall()
            has_more = len(rows) > limit
            rows = rows[:limit]
            return {
                "items": [self.project(db, row) for row in rows],
                "next_after_event_id": rows[-1]["id"] if has_more else None,
                "has_legacy_activity": bool(
                    db.execute(
                        "SELECT 1 FROM research_events WHERE session_id=? AND (legacy=1 OR event_type='trail_tracking_started') LIMIT 1",
                        (session,),
                    ).fetchone()
                ),
            }

    def get(self, params):
        with self.database.connect() as db:
            row = db.execute(
                "SELECT * FROM research_events WHERE session_id=? AND id=?",
                (params.get("session_id"), params.get("event_id")),
            ).fetchone()
            if not row:
                raise ValueError("trail.eventNotFound")
            return self.project(db, row, details=True)


def origin_context(db, event_id):
    row = db.execute("SELECT * FROM research_events WHERE id=?", (event_id,)).fetchone()
    if not row:
        raise ValueError("research.invalidOrigin")
    payload = json.loads(row["payload_json"])
    if row["event_type"] == "ask" and "evidence" in payload:
        return payload
    if row["event_type"] == "ask" and type(payload.get("ask_result_event_id")) is int:
        return origin_context(db, payload["ask_result_event_id"])
    if row["event_type"] not in ("ask_accepted", "ask_abstained", "ask_rejected", "ask_generation_failed"):
        raise ValueError("research.invalidOrigin")
    question = db.execute(
        "SELECT payload_json FROM research_events WHERE id=? AND event_type='question_asked'",
        (payload.get("question_event_id"),),
    ).fetchone()
    if not question:
        raise ValueError("research.invalidOrigin")
    return {
        "question": json.loads(question["payload_json"])["question"],
        "evidence": payload.get("selected", []),
        "execution_metadata": {"final_status": payload["final_status"]},
    }
