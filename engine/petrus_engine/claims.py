"""Explicit human statements and classifications. No generation or semantic judge."""

import json

from petrus_engine.research import ResearchEvidenceService, sha256, timestamp
from petrus_engine.trail import append_event, source_snapshot

STATEMENT_LIMIT = 10000
NOTE_LIMIT = 100000
LINK_LIMIT = 100
RELATIONS = ("supports", "contradicts", "context")
EVENTS = (
    "claim_created",
    "claim_statement_updated",
    "claim_note_updated",
    "claim_review_status_changed",
    "claim_evidence_linked",
    "claim_evidence_relation_changed",
    "claim_evidence_unlinked",
    "claim_archived",
    "claim_restored",
)
LINK_FIELDS = (
    "evidence_fingerprint",
    "paper_sha256",
    "text_sha256",
    "paper_title_snapshot",
    "section_heading_snapshot",
    "page_start",
    "page_end",
    "provenance_level",
    "supports_paginated_evidence",
)


def parameters(params, required, optional=()):
    if (
        not isinstance(params, dict)
        or set(params) - set(required) - set(optional)
        or set(required) - set(params)
    ):
        raise ValueError("claims.invalidFields")
    for key in ("id", "session_id", "claim_id", "saved_evidence_id", "after_id"):
        if key in params and (type(params[key]) is not int or params[key] < 1):
            raise ValueError("claims.invalidId")


def text(value, *, statement=False):
    if (
        not isinstance(value, str)
        or len(value) > (STATEMENT_LIMIT if statement else NOTE_LIMIT)
        or "\x00" in value
    ):
        raise ValueError("claims.invalidStatement" if statement else "claims.invalidNote")
    if statement and not value.strip():
        raise ValueError("claims.invalidStatement")
    return value


class ResearchClaimService:
    def __init__(self, database):
        self.database = database

    @staticmethod
    def claim(db, identifier, *, writable=False):
        row = db.execute("SELECT * FROM research_claims WHERE id=?", (identifier,)).fetchone()
        if not row:
            raise ValueError("claims.notFound")
        if writable and row["archived_at"] is not None:
            raise ValueError("claims.archivedReadOnly")
        return dict(row)

    @staticmethod
    def event(db, row, kind, **data):
        return append_event(
            db,
            row["session_id"],
            kind,
            {"claim_id": row["id"], **data},
            object_type="research_claim",
            object_id=row["id"],
        )

    @staticmethod
    def touch(db, row):
        db.execute("UPDATE research_claims SET updated_at=? WHERE id=?", (timestamp(), row["id"]))

    @staticmethod
    def link_row(db, identifier):
        row = db.execute(
            """SELECT l.*,e.decision AS current_decision,e.paper_id AS current_paper_id,
            EXISTS(SELECT 1 FROM paper_files f WHERE f.paper_id=e.paper_id AND f.available=1) AS source_available
            FROM research_claim_evidence l LEFT JOIN research_evidence e ON e.id=l.saved_evidence_id
            WHERE l.id=?""",
            (identifier,),
        ).fetchone()
        if not row:
            raise ValueError("claims.linkNotFound")
        result = dict(row)
        result["source_removed"] = result["saved_evidence_id"] is None
        result["source_available"] = bool(result["source_available"])
        result["supports_paginated_evidence"] = bool(result["supports_paginated_evidence"])
        result["source_snapshot_available"] = bool(result["source_snapshot_event_id"])
        return result

    @staticmethod
    def link_metadata(row):
        return {
            key: row[key]
            for key in (
                "id",
                "saved_evidence_id",
                "relation",
                "decision_at_link",
                "paper_id_snapshot",
                "source_snapshot_event_id",
                *LINK_FIELDS,
            )
        }

    def detail(self, db, identifier):
        row = self.claim(db, identifier)
        row["links"] = [
            self.link_row(db, link[0])
            for link in db.execute(
                "SELECT id FROM research_claim_evidence WHERE claim_id=? ORDER BY created_at,id",
                (identifier,),
            )
        ]
        row["counts"] = {kind: sum(link["relation"] == kind for link in row["links"]) for kind in RELATIONS}
        row["evidence_count"] = len(row["links"])
        row["review_warning"] = row["review_status"] == "reviewed" and (
            not row["links"] or any(not link["source_available"] for link in row["links"])
        )
        return row

    def create(self, params):
        parameters(params, ("session_id", "statement"), ("researcher_note",))
        statement = text(params["statement"], statement=True)
        note = text(params.get("researcher_note", ""))
        with self.database.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            ResearchEvidenceService.require_session(db, params["session_id"])
            now = timestamp()
            identifier = db.execute(
                """INSERT INTO research_claims(session_id,statement,researcher_note,created_at,updated_at)
                VALUES(?,?,?,?,?)""",
                (params["session_id"], statement, note, now, now),
            ).lastrowid
            row = self.claim(db, identifier)
            self.event(
                db,
                row,
                "claim_created",
                statement_snapshot=statement,
                statement_sha256=sha256(statement),
                researcher_note_snapshot=note,
                new_note_sha256=sha256(note),
                review_status="draft",
            )
            return self.detail(db, identifier)

    def list(self, params):
        parameters(params, ("session_id",), ("filter", "limit", "after_id"))
        view = params.get("filter", "all")
        limit = params.get("limit", 50)
        if (
            view not in ("all", "draft", "reviewed", "archived")
            or type(limit) is not int
            or not 1 <= limit <= 100
        ):
            raise ValueError("claims.invalidFilter")
        with self.database.connect() as db:
            ResearchEvidenceService.require_session(db, params["session_id"])
            clauses = [
                "session_id=?",
                "archived_at IS NOT NULL" if view == "archived" else "archived_at IS NULL",
            ]
            args = [params["session_id"]]
            if view in ("draft", "reviewed"):
                clauses.append("review_status=?")
                args.append(view)
            if "after_id" in params:
                cursor = self.claim(db, params["after_id"])
                if cursor["session_id"] != params["session_id"]:
                    raise ValueError("claims.invalidId")
                clauses.append("(updated_at<? OR (updated_at=? AND id<?))")
                args.extend((cursor["updated_at"], cursor["updated_at"], cursor["id"]))
            rows = db.execute(
                "SELECT id FROM research_claims WHERE "
                + " AND ".join(clauses)
                + " ORDER BY updated_at DESC,id DESC LIMIT ?",
                (*args, limit + 1),
            ).fetchall()
            items = []
            for entry in rows[:limit]:
                row = self.detail(db, entry[0])
                del row["researcher_note"], row["links"]
                items.append(row)
            counts = {"all": 0, "draft": 0, "reviewed": 0, "archived": 0}
            for row in db.execute(
                "SELECT review_status,archived_at FROM research_claims WHERE session_id=?",
                (params["session_id"],),
            ):
                if row["archived_at"] is not None:
                    counts["archived"] += 1
                else:
                    counts["all"] += 1
                    counts[row["review_status"]] += 1
            return {
                "items": items,
                "counts": counts,
                "next_after_id": items[-1]["id"] if len(rows) > limit else None,
            }

    def get(self, params):
        parameters(params, ("id",))
        with self.database.connect() as db:
            return self.detail(db, params["id"])

    def update(self, params):
        parameters(params, ("id",), ("statement", "researcher_note", "review_status"))
        if len(params) == 1:
            raise ValueError("claims.invalidFields")
        if "statement" in params:
            text(params["statement"], statement=True)
        if "researcher_note" in params:
            text(params["researcher_note"])
        if "review_status" in params and params["review_status"] not in ("draft", "reviewed"):
            raise ValueError("claims.invalidReviewStatus")
        with self.database.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            row = self.claim(db, params["id"], writable=True)
            changed = False
            for field in ("statement", "researcher_note", "review_status"):
                if field not in params or params[field] == row[field]:
                    continue
                new = params[field]
                if (
                    field == "review_status"
                    and new == "reviewed"
                    and not db.execute(
                        "SELECT 1 FROM research_claim_evidence WHERE claim_id=?", (row["id"],)
                    ).fetchone()
                ):
                    raise ValueError("claims.reviewNeedsEvidence")
                db.execute(f"UPDATE research_claims SET {field}=? WHERE id=?", (new, row["id"]))
                if field == "statement":
                    self.event(
                        db,
                        row,
                        "claim_statement_updated",
                        old_statement_sha256=sha256(row[field]),
                        new_statement_sha256=sha256(new),
                        new_statement_snapshot=new,
                    )
                elif field == "researcher_note":
                    self.event(
                        db,
                        row,
                        "claim_note_updated",
                        old_note_sha256=sha256(row[field]),
                        new_note_sha256=sha256(new),
                        new_note_snapshot=new,
                    )
                else:
                    self.event(
                        db,
                        row,
                        "claim_review_status_changed",
                        old_review_status=row[field],
                        new_review_status=new,
                    )
                changed = True
            if changed:
                self.touch(db, row)
            return self.detail(db, row["id"])

    def archive(self, params, restore=False):
        parameters(params, ("id",))
        with self.database.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            row = self.claim(db, params["id"])
            if (row["archived_at"] is not None) != (not restore):
                now = timestamp()
                db.execute(
                    "UPDATE research_claims SET archived_at=?,updated_at=? WHERE id=?",
                    (None if restore else now, now, row["id"]),
                )
                self.event(
                    db,
                    row,
                    "claim_restored" if restore else "claim_archived",
                    review_status=row["review_status"],
                )
            return self.detail(db, row["id"])

    def restore(self, params):
        return self.archive(params, restore=True)

    @staticmethod
    def existing_snapshot(db, evidence):
        rows = db.execute(
            """SELECT id,payload_json FROM research_events WHERE session_id=? AND
            ((object_type='research_evidence' AND object_id=?) OR event_type='claim_evidence_linked') ORDER BY id""",
            (evidence["session_id"], str(evidence["id"])),
        )
        for row in rows:
            value = json.loads(row["payload_json"])
            snapshot = value.get("source_snapshot", {})
            if (
                value.get("evidence_fingerprint") == evidence["evidence_fingerprint"]
                and snapshot.get("text_sha256") == evidence["text_sha256"]
                and snapshot.get("paper_sha256") == evidence["paper_sha256"]
                and snapshot.get("text_snapshot") == evidence["text_snapshot"]
            ):
                return row["id"]
        return None

    def evidence_link(self, params):
        parameters(params, ("claim_id", "saved_evidence_id", "relation"))
        if params["relation"] not in RELATIONS:
            raise ValueError("claims.invalidRelation")
        with self.database.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            claim = self.claim(db, params["claim_id"], writable=True)
            evidence = ResearchEvidenceService.row(db, params["saved_evidence_id"])
            if evidence["session_id"] != claim["session_id"]:
                raise ValueError("claims.crossSessionLink")
            duplicate = db.execute(
                "SELECT id FROM research_claim_evidence WHERE claim_id=? AND evidence_fingerprint=?",
                (claim["id"], evidence["evidence_fingerprint"]),
            ).fetchone()
            if duplicate:
                return {"item": self.link_row(db, duplicate["id"]), "created": False}
            if (
                db.execute(
                    "SELECT count(*) FROM research_claim_evidence WHERE claim_id=?", (claim["id"],)
                ).fetchone()[0]
                >= LINK_LIMIT
            ):
                raise ValueError("claims.tooManyLinks")
            reference = self.existing_snapshot(db, evidence)
            now = timestamp()
            values = {key: evidence[key] for key in LINK_FIELDS}
            values.update(
                claim_id=claim["id"],
                session_id=claim["session_id"],
                saved_evidence_id=evidence["id"],
                relation=params["relation"],
                paper_id_snapshot=evidence["paper_id"],
                decision_at_link=evidence["decision"],
                source_snapshot_event_id=reference,
                created_at=now,
                updated_at=now,
            )
            identifier = db.execute(
                f"INSERT INTO research_claim_evidence({','.join(values)}) VALUES({','.join('?' for _ in values)})",
                tuple(values.values()),
            ).lastrowid
            row = self.link_row(db, identifier)
            extra = {} if reference else {"source_snapshot": source_snapshot(evidence, include_text=True)}
            event = self.event(
                db,
                claim,
                "claim_evidence_linked",
                claim_evidence_id=identifier,
                **self.link_metadata(row),
                **extra,
            )
            if not reference:
                db.execute(
                    "UPDATE research_claim_evidence SET source_snapshot_event_id=? WHERE id=?",
                    (event, identifier),
                )
            self.touch(db, claim)
            return {"item": self.link_row(db, identifier), "created": True}

    def evidence_update(self, params):
        parameters(params, ("id", "relation"))
        if params["relation"] not in RELATIONS:
            raise ValueError("claims.invalidRelation")
        with self.database.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            row = self.link_row(db, params["id"])
            claim = self.claim(db, row["claim_id"], writable=True)
            if params["relation"] != row["relation"]:
                db.execute(
                    "UPDATE research_claim_evidence SET relation=?,updated_at=? WHERE id=?",
                    (params["relation"], timestamp(), row["id"]),
                )
                self.event(
                    db,
                    claim,
                    "claim_evidence_relation_changed",
                    claim_evidence_id=row["id"],
                    **self.link_metadata(row),
                    old_relation=row["relation"],
                    new_relation=params["relation"],
                )
                self.touch(db, claim)
            return self.link_row(db, row["id"])

    def evidence_unlink(self, params):
        parameters(params, ("id",))
        with self.database.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            row = self.link_row(db, params["id"])
            claim = self.claim(db, row["claim_id"], writable=True)
            self.event(
                db, claim, "claim_evidence_unlinked", claim_evidence_id=row["id"], **self.link_metadata(row)
            )
            db.execute("DELETE FROM research_claim_evidence WHERE id=?", (row["id"],))
            self.touch(db, claim)
            return {"unlinked": row["id"]}
