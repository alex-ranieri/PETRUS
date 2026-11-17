"""Human-owned saved evidence. Source snapshots come from verified current units."""

import hashlib
import json
from datetime import datetime, timezone

from petrus_engine.rag.index import current_units

DECISIONS = ("included", "excluded", "uncertain")
SOURCE_FIELDS = {
    "unit_id": "unit_id",
    "paper_id": "paper_id",
    "text": "text",
    "page_start": "page_start",
    "page_end": "page_end",
    "provenance": "provenance_level",
    "supports_paginated_evidence": "supports_paginated_evidence",
    "evidence_role": "evidence_role",
}


def timestamp():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ")


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def sha256(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def fingerprint(unit, paper_hash):
    # Semantic source identity survives replacement of numeric span/section IDs.
    identity = {
        "heading": unit.heading,
        "section_type": unit.section_type,
        "source": unit.provenance_source,
        "part_start": unit.part_start,
        "part_end": unit.part_end,
    }
    return sha256(
        canonical(
            {
                "paper_sha256": paper_hash,
                "text_sha256": sha256(unit.text),
                "page_start": unit.page_start,
                "page_end": unit.page_end,
                "provenance_level": unit.provenance_level,
                "source_identity": identity,
            }
        )
    ), identity


class ResearchEvidenceService:
    def __init__(self, database):
        self.database = database

    @staticmethod
    def require_session(db, session_id):
        if (
            type(session_id) is not int
            or not db.execute("SELECT 1 FROM research_sessions WHERE id=?", (session_id,)).fetchone()
        ):
            raise ValueError("research.sessionNotFound")

    @staticmethod
    def row(db, identifier):
        row = db.execute(
            """SELECT e.*, EXISTS(SELECT 1 FROM paper_files f
            WHERE f.paper_id=e.paper_id AND f.available=1) AS source_available
            FROM research_evidence e WHERE e.id=?""",
            (identifier,),
        ).fetchone()
        if row is None:
            raise ValueError("research.evidenceNotFound")
        result = dict(row)
        for key in ("source_available", "supports_paginated_evidence"):
            result[key] = bool(result[key])
        result["related_claims"] = [
            dict(r)
            for r in db.execute(
                "SELECT c.id,c.review_status,c.archived_at FROM research_claims c JOIN research_claim_evidence l ON l.claim_id=c.id WHERE l.saved_evidence_id=? ORDER BY c.updated_at DESC,c.id DESC",
                (identifier,),
            )
        ]
        return result

    @staticmethod
    def event(db, row, kind, **changes):
        from petrus_engine.trail import record_evidence

        return record_evidence(db, row, kind, **changes)

    def save(self, params, context=None):
        session_id = params.get("session_id")
        incoming = params.get("evidence", {})
        if not isinstance(incoming, dict):
            raise ValueError("research.invalidEvidence")
        unit_id = params.get("unit_id", incoming.get("unit_id"))
        if not isinstance(unit_id, str):
            raise ValueError("research.invalidEvidence")
        with self.database.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            self.require_session(db, session_id)
            event_id = params.get("research_event_id")
            if event_id is not None:
                from petrus_engine.trail import origin_context

                persisted = origin_context(db, event_id)

                def identities(value):
                    return [
                        (
                            item.get("evidence_id"),
                            item.get("unit_id"),
                            item.get("paper_id"),
                            sha256(item["text"]) if "text" in item else item.get("text_sha256"),
                        )
                        for item in value.get("evidence", [])
                    ]

                if context and (
                    persisted.get("question") != context.get("question")
                    or identities(persisted) != identities(context)
                ):
                    raise ValueError("research.invalidOrigin")
                context = persisted
            elif context and context.get("trail_result_event_id"):
                reference = context["trail_result_event_id"]
                if db.execute("SELECT 1 FROM research_events WHERE id=?", (reference,)).fetchone():
                    event_id = reference
            label = params.get("evidence_label", incoming.get("evidence_id"))
            source = None
            if context is not None:
                source = next(
                    (
                        e
                        for e in context.get("evidence", [])
                        if e.get("evidence_id") == label and e.get("unit_id") == unit_id
                    ),
                    None,
                )
                if source is None:
                    raise ValueError("research.invalidOrigin")
            elif params.get("origin_type") == "ask_answer" or params.get("response_id"):
                raise ValueError("research.invalidOrigin")
            unit = current_units(self.database).get(unit_id)
            if unit is None:
                raise ValueError("research.staleEvidence")
            # Compare trusted Ask context AND any supplied source fields to current records.
            for candidate in (incoming, source or {}, params):
                for field, attr in SOURCE_FIELDS.items():
                    if field in candidate and candidate[field] != getattr(unit, attr):
                        raise ValueError("research.staleEvidence")
            if source and source.get("text_sha256") and source["text_sha256"] != sha256(unit.text):
                raise ValueError("research.staleEvidence")
            paper = db.execute(
                "SELECT file_hash,title,doi FROM papers WHERE id=?", (unit.paper_id,)
            ).fetchone()
            digest, identity = fingerprint(unit, paper["file_hash"])
            if source and (
                (source.get("paper_sha256") and source["paper_sha256"] != paper["file_hash"])
                or (source.get("evidence_fingerprint") and source["evidence_fingerprint"] != digest)
            ):
                raise ValueError("research.staleEvidence")
            existing = db.execute(
                "SELECT id FROM research_evidence WHERE session_id=? AND evidence_fingerprint=?",
                (session_id, digest),
            ).fetchone()
            if existing:
                return {"item": self.row(db, existing["id"]), "created": False}
            now = timestamp()
            accepted = context and context.get("execution_metadata", {}).get("final_status") == "accepted"
            values = {
                "session_id": session_id,
                "paper_id": unit.paper_id,
                "evidence_fingerprint": digest,
                "paper_sha256": paper["file_hash"],
                "paper_title_snapshot": paper["title"],
                "paper_doi_snapshot": paper["doi"],
                "evidence_unit_id": unit.unit_id,
                "source_span_id": unit.source_span_id,
                "section_id": unit.section_id,
                "section_heading_snapshot": unit.heading,
                "evidence_role": unit.evidence_role,
                "provenance_level": str(unit.provenance_level),
                "page_start": unit.page_start,
                "page_end": unit.page_end,
                "supports_paginated_evidence": int(unit.supports_paginated_evidence),
                "text_snapshot": unit.text,
                "text_sha256": sha256(unit.text),
                "source_identity_json": canonical(identity),
                "origin_type": "ask_answer" if accepted else "retrieved_source",
                "research_event_id": event_id,
                "question_snapshot": context.get("question") if context else None,
                "evidence_label_snapshot": label if context else None,
                "created_at": now,
                "updated_at": now,
            }
            cursor = db.execute(
                f"INSERT INTO research_evidence({','.join(values)}) VALUES({','.join('?' for _ in values)})",
                tuple(values.values()),
            )
            row = self.row(db, cursor.lastrowid)
            self.event(db, row, "evidence_saved", decision="uncertain")
            return {"item": row, "created": True}

    def list(self, params):
        with self.database.connect() as db:
            self.require_session(db, params.get("session_id"))
            decision = params.get("decision", "all")
            if decision not in ("all", *DECISIONS):
                raise ValueError("research.invalidDecision")
            ids = db.execute(
                """SELECT id FROM research_evidence WHERE session_id=?
                AND (?='all' OR decision=?) ORDER BY created_at DESC,id DESC""",
                (params["session_id"], decision, decision),
            ).fetchall()
            counts = {key: 0 for key in DECISIONS}
            for row in db.execute(
                "SELECT decision,count(*) n FROM research_evidence WHERE session_id=? GROUP BY decision",
                (params["session_id"],),
            ):
                counts[row["decision"]] = row["n"]
            return {
                "items": [self.row(db, row["id"]) for row in ids],
                "counts": {**counts, "total": sum(counts.values())},
            }

    def get(self, params):
        with self.database.connect() as db:
            return self.row(db, params.get("id"))

    def update(self, params):
        changes = {k: v for k, v in params.items() if k in ("decision", "user_note")}
        if not changes or set(params) - {"id", "decision", "user_note"}:
            raise ValueError("research.invalidUpdate")
        if "decision" in changes and changes["decision"] not in DECISIONS:
            raise ValueError("research.invalidDecision")
        if "user_note" in changes and (
            not isinstance(changes["user_note"], str) or len(changes["user_note"]) > 100000
        ):
            raise ValueError("research.invalidNote")
        with self.database.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            row = self.row(db, params.get("id"))
            for key, value in changes.items():
                if value == row[key]:
                    continue
                db.execute(
                    f"UPDATE research_evidence SET {key}=?,updated_at=? WHERE id=?",
                    (value, timestamp(), row["id"]),
                )
                metadata = (
                    {"previous": row[key], "new": value, "old_decision": row[key], "new_decision": value}
                    if key == "decision"
                    else {
                        "old_note_sha256": sha256(row[key]),
                        "new_note_sha256": sha256(value),
                        "new_note_snapshot": value,
                    }
                )
                self.event(
                    db,
                    row,
                    "evidence_decision_changed" if key == "decision" else "evidence_note_updated",
                    **metadata,
                )
            return self.row(db, row["id"])

    def remove(self, params):
        with self.database.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            row = self.row(db, params.get("id"))
            self.event(db, row, "evidence_removed", decision=row["decision"])
            db.execute("DELETE FROM research_evidence WHERE id=?", (row["id"],))
            return {"removed": row["id"]}
