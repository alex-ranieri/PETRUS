import json
import logging
import queue
import re
import secrets
import threading
from collections import OrderedDict
from copy import deepcopy
from dataclasses import asdict
from pathlib import Path

from petrus_engine.database import Database
from petrus_engine.graph import build_graph
from petrus_engine.jobs.scanner import Scanner
from petrus_engine.pdf.worker import cancel_parsers
from petrus_engine.references import resolve_all
from petrus_engine.scientific import ScientificService

log = logging.getLogger(__name__)
VISIBLE = "EXISTS(SELECT 1 FROM paper_files pf WHERE pf.paper_id=p.id)"
STATUS = "CASE WHEN NOT EXISTS(SELECT 1 FROM paper_files f WHERE f.paper_id=p.id AND f.available=1) THEN 'unavailable' ELSE p.metadata_status END"
PAPER_SELECT = f"""SELECT p.*, {STATUS} AS status,
 (SELECT group_concat(name, '; ') FROM
  (SELECT a.name FROM authors a JOIN paper_authors pa ON pa.author_id=a.id WHERE pa.paper_id=p.id ORDER BY pa.author_order)) AS authors,
 (SELECT group_concat(c.name, ', ') FROM collections c JOIN collection_papers cp ON cp.collection_id=c.id WHERE cp.paper_id=p.id) AS collections
 FROM papers p"""


class Engine:
    def __init__(self, data_dir: Path, start_worker=True):
        self._ask_receipts = OrderedDict()
        self.data_dir = data_dir
        self.db = Database(data_dir / "petrus.sqlite3")
        self.scientific = ScientificService(self.db, self.get_settings)
        self.queue = queue.Queue()
        self.stop = threading.Event()
        self.worker = None
        with self.db.connect() as db:
            db.execute(
                "UPDATE jobs SET status='interrupted',message='Scan interrupted. Rescan to continue.',finished_at=CURRENT_TIMESTAMP WHERE status IN ('queued','running')"
            )
            db.execute("UPDATE papers SET metadata_status='discovered' WHERE metadata_status='processing'")
        if start_worker:
            self.worker = threading.Thread(target=self._work, daemon=True, name="petrus-ingestion")
            self.worker.start()
            self.watcher = threading.Thread(target=self._watch, daemon=True, name="petrus-watcher")
            self.watcher.start()
            if self.get_settings().get("auto_scan", False):
                with self.db.connect() as db:
                    ids = [row[0] for row in db.execute("SELECT id FROM libraries")]
                for library_id in ids:
                    self.enqueue_scan(library_id)

    def close(self):
        self.stop.set()
        cancel_parsers()
        self.queue.put(None)

    def _watch(self):
        # Portable polling watcher; job-level deduplication prevents overlapping scans.
        while not self.stop.wait(60):
            try:
                if self.get_settings().get("watch_folders", False):
                    with self.db.connect() as db:
                        ids = [r[0] for r in db.execute("SELECT id FROM libraries")]
                    for library_id in ids:
                        self.enqueue_scan(library_id)
            except Exception:
                log.exception("watcher_failed")

    def _work(self):
        scanner = Scanner(self.db, self.stop, self.scientific)
        while not self.stop.is_set():
            item = self.queue.get()
            if item is None:
                return
            library_id, job_id = item
            try:
                with self.db.connect() as db:
                    job = dict(db.execute("SELECT * FROM jobs WHERE id=?", (job_id,)).fetchone())
                if job["job_type"] == "scientific":
                    self._scientific_job(job, scanner)
                else:
                    scanner.run(library_id, job_id, verify_integrity=job["job_type"] == "integrity")
            except Exception:
                log.exception("scan_failed library_id=%s", library_id)
                scanner.update_job(
                    job_id,
                    status="failed",
                    message="Could not scan this folder. Check availability and permissions.",
                )
            finally:
                self.queue.task_done()

    def enqueue_scan(self, library_id, verify=False):
        with self.db.connect() as db:
            if not db.execute("SELECT 1 FROM libraries WHERE id=?", (library_id,)).fetchone():
                raise ValueError("Library was not found.")
            prior = db.execute(
                "SELECT id FROM jobs WHERE library_id=? AND status IN ('queued','running')", (library_id,)
            ).fetchone()
            if prior:
                return {"job_id": prior[0]}
            job_id = db.execute(
                "INSERT INTO jobs(library_id,job_type) VALUES(?,?)",
                (library_id, "integrity" if verify else "scan"),
            ).lastrowid
        self.queue.put((library_id, job_id))
        return {"job_id": job_id}

    def enqueue_scientific(self, params):
        if self.get_settings()["scientific_parser"] != "grobid":
            raise ValueError("errors.enableGrobid")
        paper_id = params.get("paper_id")
        library_id = params.get("library_id")
        with self.db.connect() as db:
            if paper_id is not None:
                file = db.execute(
                    "SELECT library_id FROM paper_files WHERE paper_id=? ORDER BY available DESC LIMIT 1",
                    (paper_id,),
                ).fetchone()
                if not file:
                    raise ValueError("errors.paperNotFound")
                library_id = file[0]
            if not db.execute("SELECT 1 FROM libraries WHERE id=?", (library_id,)).fetchone():
                raise ValueError("errors.libraryNotFound")
            prior = db.execute(
                "SELECT id FROM jobs WHERE library_id=? AND paper_id IS ? AND job_type='scientific' AND status IN ('queued','running')",
                (library_id, paper_id),
            ).fetchone()
            if prior:
                return {"job_id": prior[0]}
            job_id = db.execute(
                "INSERT INTO jobs(library_id,paper_id,job_type) VALUES(?,?,'scientific')",
                (library_id, paper_id),
            ).lastrowid
        self.queue.put((library_id, job_id))
        return {"job_id": job_id}

    def _scientific_job(self, job, scanner):
        with self.db.connect() as db:
            ids = [
                r[0]
                for r in db.execute(
                    "SELECT DISTINCT paper_id FROM paper_files WHERE library_id=? AND paper_id IS NOT NULL"
                    + (" AND paper_id=?" if job["paper_id"] is not None else ""),
                    (job["library_id"], job["paper_id"])
                    if job["paper_id"] is not None
                    else (job["library_id"],),
                )
            ]
        scanner.update_job(
            job["id"],
            status="running",
            stage="scientific_parsing",
            total=len(ids),
            message_key="jobs.scientific",
        )
        errors = 0
        for index, paper_id in enumerate(ids):
            if self.stop.is_set():
                return
            if not self.scientific.process(paper_id):
                errors += 1
            scanner.update_job(job["id"], completed=index + 1, errors=errors)
        with self.db.connect() as db:
            resolve_all(db)
            db.execute(
                "UPDATE jobs SET status=?,stage='indexed',message_key='jobs.scientificDone',finished_at=CURRENT_TIMESTAMP WHERE id=?",
                ("warning" if errors else "completed", job["id"]),
            )

    def get_settings(self):
        settings = {
            "theme": "system",
            "auto_scan": False,
            "watch_folders": False,
            "ai_provider": "None",
            "ai_endpoint": "",
            "ai_model": "",
            "language": "system",
            "scientific_parser": "simple",
            "grobid_endpoint": "http://127.0.0.1:8070",
            "grobid_fallback": True,
            "llm_provider": "none",
            "llm_endpoint": "",
            "llm_model": "",
            "llm_temperature": 0.1,
            "llm_query_expansion": False,
            "llm_reasoning": "off",
            "llm_context_length": 8192,
            "llm_max_output_tokens": 1600,
            "llm_timeout_seconds": 90,
            "embedding_provider": "none",
            "embedding_endpoint": "",
            "embedding_model": "",
            "embedding_max_chars": 6000,
        }
        with self.db.connect() as db:
            settings.update(
                {row["key"]: json.loads(row["value"]) for row in db.execute("SELECT * FROM settings")}
            )
        return settings

    def snapshot(self):
        with self.db.connect() as db:
            libraries = [
                dict(row)
                for row in db.execute("""SELECT l.*,
                (SELECT count(*) FROM paper_files f WHERE f.library_id=l.id) AS file_count
                FROM libraries l ORDER BY l.created_at,l.id""")
            ]
            stats = dict(
                db.execute(f"""SELECT count(*) AS papers,
                coalesce(sum(p.index_status='indexed'),0) AS indexed,
                coalesce(sum(({STATUS}) IN ('warning','failed','unavailable')),0) AS attention
                FROM papers p WHERE {VISIBLE}""").fetchone()
            )
            issues = [
                dict(row)
                for row in db.execute("""SELECT f.*,l.name AS library_name
                FROM paper_files f JOIN libraries l ON l.id=f.library_id WHERE f.error IS NOT NULL ORDER BY f.id DESC LIMIT 100""")
            ]
            collections = [
                dict(row)
                for row in db.execute("""SELECT c.*,count(cp.paper_id) AS paper_count
                FROM collections c LEFT JOIN collection_papers cp ON cp.collection_id=c.id GROUP BY c.id ORDER BY c.name""")
            ]
            jobs = [
                dict(row)
                for row in db.execute("""SELECT j.*,l.name AS library_name FROM jobs j
                JOIN libraries l ON l.id=j.library_id ORDER BY j.id DESC LIMIT 12""")
            ]
            sessions = [dict(row) for row in db.execute("SELECT * FROM research_sessions ORDER BY id DESC")]
            facets = {
                key: [
                    r[0]
                    for r in db.execute(
                        f"SELECT DISTINCT {column} FROM {table} WHERE {column} IS NOT NULL ORDER BY {column}"
                    )
                ]
                for key, table, column in [
                    ("years", "papers", "publication_year"),
                    ("journals", "papers", "journal"),
                    ("authors", "authors", "name"),
                ]
            }
        with self.db.connect() as db:
            issues_total = db.execute("SELECT count(*) FROM paper_files WHERE error IS NOT NULL").fetchone()[
                0
            ]
        stats["collections"] = len(collections)
        with self.db.connect() as db:
            stats["attention"] += db.execute(
                "SELECT count(*) FROM paper_files WHERE paper_id IS NULL AND error IS NOT NULL"
            ).fetchone()[0]
        return {
            "libraries": libraries,
            "stats": stats,
            "collections": collections,
            "jobs": jobs,
            "sessions": sessions,
            "issues": issues,
            "issues_total": issues_total,
            "facets": facets,
            "settings": self.get_settings(),
            "data_dir": str(self.data_dir),
            "grobid": {"state": self.scientific.grobid.state, "endpoint": self.scientific.grobid.endpoint},
            "database_path": str(self.db.path),
        }

    def list_papers(self, params):
        conditions = [VISIBLE]
        values = []
        query = str(params.get("query") or "").strip()[:500]
        if query:
            tokens = re.findall(r"\w+", query, re.UNICODE)[:30]
            if not tokens:
                return {"papers": [], "total": 0}
            fts = " AND ".join('"' + token + '"*' for token in tokens)
            conditions.append("p.id IN (SELECT rowid FROM paper_search WHERE paper_search MATCH ?)")
            values.append(fts)
        for field, column in [("year", "p.publication_year"), ("journal", "p.journal")]:
            if params.get(field):
                conditions.append(f"{column}=?")
                values.append(params[field])
        if params.get("status") == "attention":
            conditions.append(f"({STATUS}) IN ('warning','failed','unavailable')")
        elif params.get("status"):
            conditions.append(f"({STATUS})=?")
            values.append(params["status"])
        if params.get("author"):
            conditions.append(
                "p.id IN (SELECT pa.paper_id FROM paper_authors pa JOIN authors a ON a.id=pa.author_id WHERE a.name=?)"
            )
            values.append(params["author"])
        if params.get("collection"):
            conditions.append("p.id IN (SELECT paper_id FROM collection_papers WHERE collection_id=?)")
            values.append(int(params["collection"]))
        where = " WHERE " + " AND ".join(conditions)
        limit = min(max(int(params.get("limit", 100)), 1), 200)
        offset = max(int(params.get("offset", 0)), 0)
        with self.db.connect() as db:
            total = db.execute("SELECT count(*) FROM papers p" + where, values).fetchone()[0]
            papers = [
                dict(row)
                for row in db.execute(
                    PAPER_SELECT + where + " ORDER BY p.updated_at DESC,p.id DESC LIMIT ? OFFSET ?",
                    (*values, limit, offset),
                )
            ]
        return {"papers": papers, "total": total}

    def paper_detail(self, paper_id):
        with self.db.connect() as db:
            paper = db.execute(PAPER_SELECT + " WHERE p.id=?", (paper_id,)).fetchone()
            if not paper:
                raise ValueError("Paper was not found.")
            result = dict(paper)
            result["files"] = [
                dict(r) for r in db.execute("SELECT * FROM paper_files WHERE paper_id=?", (paper_id,))
            ]
            result["memberships"] = [
                r[0]
                for r in db.execute(
                    "SELECT collection_id FROM collection_papers WHERE paper_id=?", (paper_id,)
                )
            ]
            result["references"] = [
                dict(r)
                for r in db.execute(
                    'SELECT * FROM "references" WHERE source_paper_id=? ORDER BY citation_order', (paper_id,)
                )
            ]
            result["sections"] = [
                dict(r)
                for r in db.execute(
                    "SELECT * FROM sections WHERE paper_id=? ORDER BY section_order", (paper_id,)
                )
            ]
            result["source_spans"] = [
                dict(r)
                for r in db.execute(
                    "SELECT * FROM source_spans WHERE paper_id=? ORDER BY page,id", (paper_id,)
                )
            ]
            result["connections"] = [
                dict(r)
                for r in db.execute(
                    """SELECT DISTINCT p.id,p.title FROM papers p
                WHERE p.id!=? AND (p.id IN (SELECT b.paper_id FROM paper_authors a JOIN paper_authors b
                ON a.author_id=b.author_id WHERE a.paper_id=?) OR p.id IN (SELECT b.paper_id FROM collection_papers a
                JOIN collection_papers b ON a.collection_id=b.collection_id WHERE a.paper_id=?)) LIMIT 100""",
                    (paper_id, paper_id, paper_id),
                )
            ]
        return result

    def call(self, method, params):
        if method.startswith("research_claim_"):
            from petrus_engine.claims import ResearchClaimService

            operation = method.removeprefix("research_claim_")
            if operation not in (
                "create",
                "list",
                "get",
                "update",
                "archive",
                "restore",
                "evidence_link",
                "evidence_update",
                "evidence_unlink",
            ):
                raise ValueError("Unknown operation")
            return getattr(ResearchClaimService(self.db), operation)(params)
        if method in ("research_trail_list", "research_trail_get"):
            from petrus_engine.trail import ResearchTrailService

            trail = ResearchTrailService(self.db)
            return trail.list(params) if method == "research_trail_list" else trail.get(params)
        if method.startswith("research_evidence_"):
            from petrus_engine.research import ResearchEvidenceService

            workspace = ResearchEvidenceService(self.db)
            operation = method.removeprefix("research_evidence_")
            if operation == "save":
                receipt = params.get("response_id")
                if receipt is not None and (
                    not isinstance(receipt, str) or receipt not in self._ask_receipts
                ):
                    raise ValueError("research.expiredResponse")
                return workspace.save(params, self._ask_receipts.get(receipt))
            if operation in ("list", "get", "update", "remove"):
                return getattr(workspace, operation)(params)
            raise ValueError("Unknown operation")
        if method == "llm_models":
            from petrus_engine.llm.catalog import model_catalog

            return model_catalog(params.get("endpoint", "http://127.0.0.1:1234"))
        if method in ("ask", "llm_status", "save_ask_event"):
            from petrus_engine.llm.local import configured_llm
            from petrus_engine.rag.ask import AskPetrusService
            from petrus_engine.rag.providers import configured_provider

            settings = self.get_settings()
            if method == "save_ask_event":
                response = params.get("response")
                if (
                    not isinstance(response, dict)
                    or not isinstance(response.get("question"), str)
                    or not isinstance(response.get("answer"), str)
                ):
                    raise ValueError("ask_invalid_event")
                from petrus_engine.rag.ask import INSUFFICIENT, validate_answer
                from petrus_engine.rag.index import current_units
                from petrus_engine.rag.query import plan_query
                from petrus_engine.rag.validation import snapshot_execution

                execution = snapshot_execution(response.get("execution_metadata"))
                units = current_units(self.db)
                evidence = response.get("evidence", [])
                if not isinstance(evidence, list) or len(evidence) > 8:
                    raise ValueError("ask_invalid_event")
                for item in evidence:
                    if not isinstance(item, dict):
                        raise ValueError("ask_invalid_event")
                    unit = units.get(item.get("unit_id"))
                    if (
                        unit is None
                        or unit.evidence_role in ("bibliography", "metadata")
                        or unit.paper_id != item.get("paper_id")
                        or unit.text != item.get("text")
                    ):
                        raise ValueError("ask_stale_evidence")
                    if unit.page_start != item.get("page_start") or unit.page_end != item.get("page_end"):
                        raise ValueError("ask_invalid_event")
                if sum(len(e.get("text", "")) for e in evidence) > 12000:
                    raise ValueError("ask_invalid_event")
                if len({e.get("evidence_id") for e in evidence}) != len(evidence):
                    raise ValueError("ask_invalid_event")
                validate_answer(response, {e["evidence_id"] for e in evidence})
                if (
                    response["insufficient_evidence"]
                    and response["answer"] != INSUFFICIENT[plan_query(response["question"]).detected_language]
                ):
                    raise ValueError("ask_invalid_event")
                evidence = [
                    {
                        k: item[k]
                        for k in (
                            "evidence_id",
                            "unit_id",
                            "paper_id",
                            "paper_title",
                            "section",
                            "page_start",
                            "page_end",
                            "text",
                            "provenance",
                            "evidence_role",
                            "supports_paginated_evidence",
                        )
                        if k in item
                    }
                    for item in evidence
                ]
                incoming = response.get("retrieval_metadata", {})
                if not isinstance(incoming, dict):
                    raise ValueError("ask_invalid_event")
                retrieval = {
                    k: incoming[k]
                    for k in (
                        "retrieved",
                        "selected",
                        "context_characters",
                        "include_bibliography",
                        "max_hits_per_paper",
                        "model_id",
                    )
                    if isinstance(incoming.get(k), (str, int, float, bool))
                }
                retrieval["query_plan"] = asdict(plan_query(response["question"]))
                prior_plan = incoming.get("query_plan", {})
                if isinstance(prior_plan, dict) and isinstance(prior_plan.get("expanded_terms"), list):
                    retrieval["query_plan"]["expanded_terms"] = [
                        v[:300] for v in prior_plan["expanded_terms"][:3] if isinstance(v, str)
                    ]
                payload = {
                    "question": response["question"],
                    "answer": response["answer"],
                    "evidence_ids": [e["evidence_id"] for e in evidence],
                    "evidence": evidence,
                    "paper_ids": sorted({e["paper_id"] for e in evidence}),
                    "retrieval_metadata": retrieval,
                    "model_id": retrieval.get("model_id"),
                    "insufficient_evidence": response["insufficient_evidence"],
                    "execution_metadata": execution,
                }
                with self.db.connect() as db:
                    from petrus_engine.trail import append_event

                    context = self._ask_receipts.get(response.get("response_id"))
                    reference = context.get("trail_result_event_id") if context else None
                    tracked = (
                        db.execute(
                            "SELECT session_id,payload_json FROM research_events WHERE id=?", (reference,)
                        ).fetchone()
                        if reference
                        else None
                    )
                    reuse = tracked is not None and tracked["session_id"] == params["session_id"]
                    if reuse:
                        from petrus_engine.research import sha256

                        if json.loads(tracked["payload_json"]).get("answer_sha256") != sha256(
                            response["answer"]
                        ):
                            raise ValueError("ask_invalid_event")
                        payload = {
                            "ask_result_event_id": reference,
                            "answer_sha256": sha256(response["answer"]),
                        }
                    event_id = append_event(
                        db,
                        int(params["session_id"]),
                        "ask",
                        payload,
                        object_type="ask_result" if reuse else "ask_snapshot",
                        object_id=reference if reuse else None,
                    )
                    return {"event_id": event_id}
            if method == "llm_status":
                llm = configured_llm(settings)
                return llm.status() if llm else {"state": "disabled"}
            session_id = params.get("session_id")
            trail, question_id = None, None
            if session_id is not None:
                from petrus_engine.trail import ResearchTrailService

                trail = ResearchTrailService(self.db)
                question_id = trail.begin(session_id, params.get("question"))
            try:
                llm = configured_llm(settings)
                provider = configured_provider(settings)
                ask = AskPetrusService(self.db, provider, llm, settings.get("llm_query_expansion", False))
                observation = None
                if trail:
                    from petrus_engine.trail import RetrievalObservation

                    observation = RetrievalObservation(ask.retriever, self.db)
                    ask.retriever = observation
                response = ask.ask(params.get("question"))
            except Exception:
                if trail:
                    try:
                        trail.fail(session_id, question_id)
                    except Exception:
                        raise ValueError("trail.persistenceFailed") from None
                raise
            if trail:
                try:
                    tracking = trail.finish(
                        session_id, question_id, response, observation, settings, llm, provider
                    )
                except Exception:
                    tracking = {
                        "state": "failed",
                        "question_event_id": question_id,
                        "warning": "trail.persistenceFailed",
                    }
                response = {**response, "trail": tracking}
            # UI origin receipt only: no changes to generation, retrieval or answer content.
            receipt = secrets.token_urlsafe(24)
            self._ask_receipts[receipt] = {
                "question": response["question"],
                "evidence": deepcopy(response["evidence"]),
                "execution_metadata": {
                    "final_status": response.get("execution_metadata", {}).get("final_status")
                },
                "trail_result_event_id": response.get("trail", {}).get("result_event_id"),
            }
            if len(self._ask_receipts) > 16:
                self._ask_receipts.popitem(last=False)
            return {**response, "response_id": receipt}
        if method in (
            "semantic_search",
            "hybrid_search",
            "embedding_index",
            "embedding_status",
            "embedding_remove_stale",
        ):
            from petrus_engine.rag.providers import configured_provider
            from petrus_engine.rag.retrieval import HybridRetriever, serialize_hit

            provider = configured_provider(self.get_settings())
            include_bibliography = params.get("include_bibliography", False)
            if type(include_bibliography) is not bool:
                raise ValueError("retrieval_invalid_bibliography_filter")
            retriever = HybridRetriever(self.db, provider, include_bibliography=include_bibliography)
            if method in ("semantic_search", "hybrid_search"):
                query, top_k = params.get("query"), params.get("top_k", 10)
                if not isinstance(query, str) or not query.strip() or len(query) > 2000:
                    raise ValueError("retrieval_invalid_query")
                if type(top_k) is not int or not 1 <= top_k <= 100:
                    raise ValueError("retrieval_invalid_top_k")

                from petrus_engine.rag.query import plan_query

                plan = plan_query(query)
                if (
                    method == "hybrid_search"
                    and self.get_settings().get("llm_query_expansion")
                    and plan.detected_language == "pt-BR"
                ):
                    try:
                        from petrus_engine.llm.local import configured_llm

                        llm = configured_llm(self.get_settings())
                        if llm:
                            plan.expanded_terms = llm.expand_query(query)
                    except Exception:
                        plan.warnings.append("query_expansion_unavailable")
                hits = (
                    retriever.hybrid_search(query, top_k, plan)
                    if method == "hybrid_search"
                    else retriever.semantic_search(query, top_k)
                )
                return {"hits": [serialize_hit(hit) for hit in hits], "query_plan": asdict(plan)}
            if retriever.service is None:
                if method == "embedding_status":
                    return {"state": "disabled", "enabled": False, "current": 0}
                raise ValueError("embedding_provider_not_configured")
            if method == "embedding_status":
                if params.get("check_connection"):
                    try:
                        provider.embed_query("PETRUS connection check")
                    except Exception as exc:
                        return {"state": "error", "error": str(exc), **retriever.service.status()}
                return {"state": "available", "enabled": True, **retriever.service.status()}
            if method == "embedding_remove_stale":
                return {"removed": retriever.service.remove_stale()}
            paper_id = params.get("paper_id")
            if type(paper_id) is not int or paper_id < 1:
                raise ValueError("embedding_paper_id_required")
            return retriever.service.index_paper(paper_id)
        if method == "snapshot":
            return self.snapshot()
        if method == "papers":
            return self.list_papers(params)
        if method == "paper":
            return self.paper_detail(int(params["id"]))
        if method == "add_library":
            path = Path(params["path"]).expanduser().resolve(strict=True)
            if not path.is_dir():
                raise ValueError("Choose a folder containing PDFs.")
            with self.db.connect() as db:
                db.execute(
                    "INSERT OR IGNORE INTO libraries(name,root_path) VALUES(?,?)", (path.name, str(path))
                )
                library_id = db.execute(
                    "SELECT id FROM libraries WHERE root_path=?", (str(path),)
                ).fetchone()[0]
            return self.enqueue_scan(library_id)
        if method == "rescan":
            return self.enqueue_scan(int(params["id"]))
        if method == "verify_integrity":
            return self.enqueue_scan(int(params["id"]), verify=True)
        if method == "reprocess_scientific":
            return self.enqueue_scientific(params)
        if method == "grobid_health":
            self.scientific.configure()
            return self.scientific.grobid.health()
        if method == "remove_library":
            library_id = int(params["id"])
            with self.db.connect() as db:
                if db.execute(
                    "SELECT 1 FROM jobs WHERE library_id=? AND status IN ('running','queued')", (library_id,)
                ).fetchone():
                    raise ValueError("Wait for this scan to finish before removing the library.")
                db.execute("DELETE FROM libraries WHERE id=?", (library_id,))
                resolve_all(db)
            return True
        if method == "save_settings":
            allowed = {
                "theme": str,
                "auto_scan": bool,
                "watch_folders": bool,
                "ai_provider": str,
                "ai_endpoint": str,
                "ai_model": str,
                "language": str,
                "scientific_parser": str,
                "grobid_endpoint": str,
                "grobid_fallback": bool,
                "llm_provider": str,
                "llm_endpoint": str,
                "llm_model": str,
                "llm_temperature": (int, float),
                "llm_query_expansion": bool,
                "llm_reasoning": str,
                "llm_context_length": int,
                "llm_max_output_tokens": int,
                "llm_timeout_seconds": int,
                "embedding_provider": str,
                "embedding_endpoint": str,
                "embedding_model": str,
                "embedding_max_chars": int,
            }
            llm_provider = params.get("llm_provider", self.get_settings()["llm_provider"])
            with self.db.connect() as db:
                for key, value in params.items():
                    if key not in allowed or not isinstance(value, allowed[key]):
                        raise ValueError("Invalid setting.")
                    if key == "theme" and value not in ("system", "light", "dark"):
                        raise ValueError("Invalid appearance.")
                    if key == "language" and value not in ("system", "en", "pt-BR"):
                        raise ValueError("errors.invalidSetting")
                    if key == "scientific_parser" and value not in ("simple", "grobid"):
                        raise ValueError("errors.invalidSetting")
                    if key == "llm_provider" and value not in ("none", "lmstudio", "openai_compatible"):
                        raise ValueError("llm_unsupported_provider")
                    if key == "llm_endpoint" and value:
                        from petrus_engine.rag.providers import local_endpoint

                        if llm_provider != "openai_compatible":
                            from petrus_engine.llm.native import native_endpoint

                            native_endpoint(value)
                        else:
                            local_endpoint(value)
                    if key == "llm_reasoning" and value not in ("off", "on", "low", "medium", "high"):
                        raise ValueError("llm_invalid_reasoning")
                    if key == "llm_context_length" and (type(value) is not int or not 512 <= value <= 262144):
                        raise ValueError("llm_invalid_context_length")
                    if key == "llm_max_output_tokens" and (
                        type(value) is not int or not 128 <= value <= 8192
                    ):
                        raise ValueError("llm_invalid_output_limit")
                    if key == "llm_timeout_seconds" and (type(value) is not int or not 5 <= value <= 600):
                        raise ValueError("llm_invalid_timeout")
                    if key == "llm_temperature" and (
                        isinstance(value, bool) or not 0 <= value <= (1 if llm_provider == "lmstudio" else 2)
                    ):
                        raise ValueError("llm_invalid_temperature")
                    if key == "embedding_provider" and value not in ("none", "lmstudio"):
                        raise ValueError("embedding_unsupported_provider")
                    if key == "embedding_endpoint" and value:
                        from petrus_engine.rag.providers import local_endpoint

                        local_endpoint(value)
                    if key == "embedding_max_chars" and (type(value) is not int or not 1 <= value <= 100000):
                        raise ValueError("embedding_invalid_text_limit")
                    if key == "grobid_endpoint":
                        from petrus_engine.pdf.grobid import GrobidService

                        GrobidService(value)
                    db.execute("INSERT OR REPLACE INTO settings VALUES(?,?)", (key, json.dumps(value)))
            return self.get_settings()
        if method == "new_session":
            title = str(params.get("title", "")).strip()[:300]
            if not title:
                raise ValueError("Give your research session a title.")
            with self.db.connect() as db:
                session_id = db.execute(
                    """INSERT INTO research_sessions(title,research_question,description)
                    VALUES(?,?,?)""",
                    (
                        title,
                        str(params.get("question", ""))[:5000],
                        str(params.get("description", ""))[:10000],
                    ),
                ).lastrowid
                from petrus_engine.trail import append_event

                append_event(
                    db,
                    session_id,
                    "session_created",
                    {"title": title},
                    object_type="session",
                    object_id=session_id,
                )
            return {"id": session_id}
        if method == "session":
            with self.db.connect() as db:
                row = db.execute("SELECT * FROM research_sessions WHERE id=?", (params["id"],)).fetchone()
                if not row:
                    raise ValueError("Session was not found.")
                return {
                    **dict(row),
                    "events": [
                        dict(r)
                        for r in db.execute(
                            "SELECT * FROM research_events WHERE session_id=? ORDER BY id DESC",
                            (params["id"],),
                        )
                    ],
                }
        if method == "create_collection":
            name = str(params.get("name", "")).strip()[:100]
            if not name:
                raise ValueError("Enter a collection name.")
            with self.db.connect() as db:
                db.execute("INSERT INTO collections(name) VALUES(?)", (name,))
            return True
        if method == "set_collection":
            with self.db.connect() as db:
                if params["selected"]:
                    db.execute(
                        "INSERT OR IGNORE INTO collection_papers VALUES(?,?)",
                        (params["collection_id"], params["paper_id"]),
                    )
                else:
                    db.execute(
                        "DELETE FROM collection_papers WHERE collection_id=? AND paper_id=?",
                        (params["collection_id"], params["paper_id"]),
                    )
            return True
        if method == "save_notes":
            with self.db.connect() as db:
                db.execute(
                    "UPDATE papers SET notes=? WHERE id=?", (str(params["notes"])[:100000], params["id"])
                )
            return True
        if method == "content":
            with self.db.connect() as db:
                row = db.execute(
                    "SELECT page,text FROM chunks WHERE paper_id=? AND page=?",
                    (params["id"], params.get("page", 1)),
                ).fetchone()
                count = db.execute(
                    "SELECT count(*) FROM chunks WHERE paper_id=?", (params["id"],)
                ).fetchone()[0]
                return {"page": dict(row) if row else None, "extracted_pages": count}
        if method == "graph":
            from petrus_engine.graph.relatedness import RelatednessService
            from petrus_engine.rag.index import current_units
            from petrus_engine.rag.providers import configured_provider

            provider = configured_provider(self.get_settings())
            with self.db.connect() as db:
                graph = build_graph(db)
                if provider:
                    ids = {int(n["id"]) for n in graph["nodes"]}
                    relations = RelatednessService(db).semantic_relations(
                        ids, current_units(self.db), provider
                    )
                    for relation in relations:
                        a, b = relation["source_paper_id"], relation["target_paper_id"]
                        graph["edges"].append(
                            {
                                "id": f"semantic-{a}-{b}",
                                "source": str(a),
                                "target": str(b),
                                "type": "SEMANTIC_SIMILARITY",
                                "relation": "SEMANTIC_SIMILARITY",
                                "score": relation["score"],
                                "metadata": relation["metadata"],
                            }
                        )
                return graph
        if method == "file_path":
            with self.db.connect() as db:
                rows = db.execute(
                    "SELECT file_path FROM paper_files WHERE paper_id=? AND available=1 ORDER BY id",
                    (params["id"],),
                ).fetchall()
            for row in rows:
                if Path(row[0]).is_file():
                    return row[0]
            raise ValueError("File is not currently available locally. Reconnect the folder and rescan.")
        raise ValueError("Unknown engine operation.")
