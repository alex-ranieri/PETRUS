"""Human claims on synthetic saved sources; no LLM or domain inference."""

import json
import sqlite3

import pytest
from petrus_engine.research import sha256
from petrus_engine.service import Engine
from test_embeddings import env as env
from test_research_evidence import save
from test_research_evidence import workspace as workspace


def create(engine, session, statement="  Preliminary TEST hypothesis ç\n  ", note=""):
    return engine.call(
        "research_claim_create", {"session_id": session, "statement": statement, "researcher_note": note}
    )


def link(engine, claim, evidence, relation="supports"):
    return engine.call(
        "research_claim_evidence_link",
        {"claim_id": claim["id"], "saved_evidence_id": evidence["id"], "relation": relation},
    )["item"]


def trail(engine, session):
    return engine.call("research_trail_list", {"session_id": session, "limit": 100})["items"]


def test_create_exact_text_defaults_migration_and_no_generation(workspace, monkeypatch):
    engine, session = workspace

    def forbidden(*args):
        raise AssertionError("Claims never call a model")

    monkeypatch.setattr("petrus_engine.llm.local.configured_llm", forbidden)
    monkeypatch.setattr("petrus_engine.rag.providers.configured_provider", forbidden)
    assert engine.call("research_claim_list", {"session_id": session})["items"] == []
    note = "  Human ç\r\n漢字  "
    claim = create(engine, session, note=note)
    assert claim["statement"] == "  Preliminary TEST hypothesis ç\n  " and claim["researcher_note"] == note
    assert claim["review_status"] == "draft" and claim["archived_at"] is None and not claim["links"]
    with engine.db.connect() as db:
        assert (
            db.execute(
                "SELECT count(*) FROM schema_migrations WHERE version='007_research_claims.sql'"
            ).fetchone()[0]
            == 1
        )
    detail = engine.call(
        "research_trail_get", {"session_id": session, "event_id": trail(engine, session)[-1]["id"]}
    )
    assert (
        detail["actor_type"] == "user"
        and detail["claim_id"] == claim["id"]
        and detail["payload_version"] == 1
    )
    assert detail["metadata"]["statement_snapshot"] == claim["statement"]
    assert detail["metadata"]["researcher_note_snapshot"] == note


@pytest.mark.parametrize("statement", [None, "", " \n\t\u2003", 12, "x" * 10001, "nul\x00"])
def test_invalid_statement(workspace, statement):
    engine, session = workspace
    with pytest.raises(ValueError):
        create(engine, session, statement)
    assert engine.call("research_claim_list", {"session_id": session})["items"] == []


@pytest.mark.parametrize(
    "params", [{"review_status": "reviewed"}, {"reasoning": "secret"}, {"statement": "x", "unknown": 1}]
)
def test_create_cannot_inject_status_or_unknown_fields(workspace, params):
    engine, session = workspace
    with pytest.raises(ValueError):
        engine.call("research_claim_create", {"session_id": session, "statement": "Test", **params})


def test_exact_versions_noop_and_payload_limits(workspace):
    engine, session = workspace
    first = create(engine, session, note="Initial human note")
    statement = "漢" * 10000
    note = " ç\n" * 33333 + "x"
    second = engine.call(
        "research_claim_update", {"id": first["id"], "statement": statement, "researcher_note": note}
    )
    assert (
        second["statement"] == statement
        and second["researcher_note"] == note
        and second["review_status"] == "draft"
    )
    before = trail(engine, session)
    assert (
        engine.call(
            "research_claim_update", {"id": first["id"], "statement": statement, "researcher_note": note}
        )
        == second
    )
    assert trail(engine, session) == before
    details = [
        engine.call("research_trail_get", {"session_id": session, "event_id": e["id"]})["metadata"]
        for e in before[-2:]
    ]
    assert details[0]["new_statement_snapshot"] == statement and details[0]["old_statement_sha256"] == sha256(
        first["statement"]
    )
    assert details[1]["new_note_snapshot"] == note and details[1]["old_note_sha256"] == sha256(
        "Initial human note"
    )
    with pytest.raises(ValueError):
        engine.call("research_claim_update", {"id": first["id"], "researcher_note": "x" * 100001})
    assert engine.call("research_claim_get", {"id": first["id"]}) == second


def test_link_relation_review_independent_states_and_bidirectional(workspace):
    engine, session = workspace
    source = save(engine, session)["item"]
    claim = create(engine, session)
    with pytest.raises(ValueError, match="reviewNeedsEvidence"):
        engine.call("research_claim_update", {"id": claim["id"], "review_status": "reviewed"})
    relation = link(engine, claim, source)
    assert relation["current_decision"] == "uncertain" and relation["relation"] == "supports"
    assert (
        relation["evidence_fingerprint"] == source["evidence_fingerprint"]
        and relation["paper_sha256"] == source["paper_sha256"]
    )
    assert relation["page_start"] == 2 and relation["provenance_level"] == "coordinate"
    assert (
        engine.call("research_evidence_get", {"id": source["id"]})["related_claims"][0]["id"] == claim["id"]
    )
    before = trail(engine, session)
    assert link(engine, claim, source, "context") == relation  # duplicate never silently changes relation
    assert trail(engine, session) == before
    for kind in ("contradicts", "context", "supports"):
        updated = engine.call("research_claim_evidence_update", {"id": relation["id"], "relation": kind})
        assert updated["relation"] == kind
    reviewed = engine.call("research_claim_update", {"id": claim["id"], "review_status": "reviewed"})
    assert reviewed["review_status"] == "reviewed" and not reviewed["review_warning"]
    assert engine.call("research_evidence_get", {"id": source["id"]})["decision"] == "uncertain"
    engine.call(
        "research_evidence_update", {"id": source["id"], "decision": "excluded", "user_note": "Human note"}
    )
    assert engine.call("research_claim_get", {"id": claim["id"]})["links"][0]["relation"] == "supports"
    engine.call("research_claim_evidence_unlink", {"id": relation["id"]})
    empty = engine.call("research_claim_get", {"id": claim["id"]})
    assert empty["review_status"] == "reviewed" and empty["review_warning"]
    assert engine.call("research_evidence_get", {"id": source["id"]})["related_claims"] == []
    assert (
        engine.call("research_claim_update", {"id": claim["id"], "review_status": "draft"})["review_status"]
        == "draft"
    )


def test_cross_session_and_sql_constraints(workspace):
    engine, session = workspace
    claim = create(engine, session)
    other = engine.call("new_session", {"title": "Other"})["id"]
    source = save(engine, other)["item"]
    with pytest.raises(ValueError, match="crossSessionLink"):
        link(engine, claim, source)
    local = save(engine, session)["item"]
    relation = link(engine, claim, local)
    with engine.db.connect() as db:
        for mutation, args in [
            (
                "UPDATE research_claim_evidence SET saved_evidence_id=? WHERE id=?",
                (source["id"], relation["id"]),
            ),
            ("UPDATE research_claim_evidence SET session_id=? WHERE id=?", (other, relation["id"])),
            ("UPDATE research_claims SET session_id=? WHERE id=?", (other, claim["id"])),
            ("UPDATE research_claim_evidence SET relation='automated' WHERE id=?", (relation["id"],)),
            ("UPDATE research_claims SET review_status='proven' WHERE id=?", (claim["id"],)),
            ("UPDATE research_claims SET session_id=999 WHERE id=?", (claim["id"],)),
        ]:
            with pytest.raises(sqlite3.IntegrityError):
                db.execute(mutation, args)


def test_snapshot_reuse_source_removal_and_unavailable(workspace):
    engine, session = workspace
    source = save(engine, session)["item"]
    claim = create(engine, session)
    relation = link(engine, claim, source)
    with engine.db.connect() as db:
        saved = db.execute("SELECT id FROM research_events WHERE event_type='evidence_saved'").fetchone()[0]
    assert relation["source_snapshot_event_id"] == saved
    second = create(engine, session)
    assert link(engine, second, source)["source_snapshot_event_id"] == saved
    engine.call("research_claim_update", {"id": claim["id"], "review_status": "reviewed"})
    with engine.db.connect() as db:
        db.execute("UPDATE paper_files SET available=0 WHERE paper_id=?", (source["paper_id"],))
    unavailable = engine.call("research_claim_get", {"id": claim["id"]})
    assert (
        unavailable["review_warning"]
        and not unavailable["links"][0]["source_available"]
        and not unavailable["links"][0]["source_removed"]
    )
    engine.call("research_evidence_remove", {"id": source["id"]})
    removed = engine.call("research_claim_get", {"id": claim["id"]})
    assert removed["links"][0]["source_removed"] and removed["review_status"] == "reviewed"
    assert removed["links"][0]["paper_title_snapshot"] == source["paper_title_snapshot"]
    history = engine.call("research_trail_get", {"session_id": session, "event_id": saved})
    assert history["metadata"]["source_snapshot"]["text_snapshot"] == source["text_snapshot"]


def test_legacy_snapshot_captured_once_and_survives_reprocessing(workspace):
    engine, session = workspace
    source = save(engine, session)["item"]
    with engine.db.connect() as db:
        db.execute("DROP TRIGGER research_events_no_update")
        db.execute("UPDATE research_events SET legacy=1,payload_json='{}' WHERE event_type='evidence_saved'")
    first = create(engine, session)
    relation = link(engine, first, source)
    event = engine.call(
        "research_trail_get", {"session_id": session, "event_id": relation["source_snapshot_event_id"]}
    )
    assert (
        event["event_type"] == "claim_evidence_linked"
        and event["metadata"]["source_snapshot"]["text_snapshot"] == source["text_snapshot"]
    )
    second = create(engine, session)
    assert link(engine, second, source)["source_snapshot_event_id"] == relation["source_snapshot_event_id"]
    with engine.db.connect() as db:
        db.execute("UPDATE source_spans SET text='Replacement source' WHERE id=2")
        db.execute("DELETE FROM source_spans WHERE id=2")
    assert (
        engine.call("research_claim_get", {"id": first["id"]})["links"][0]["text_sha256"]
        == source["text_sha256"]
    )
    engine.call("research_evidence_remove", {"id": source["id"]})
    assert engine.call("research_trail_get", {"session_id": session, "event_id": event["id"]}) == event


def test_archive_restore_filters_noop_and_reopen(workspace):
    engine, session = workspace
    source = save(engine, session)["item"]
    claim = create(engine, session)
    link(engine, claim, source)
    archived = engine.call("research_claim_archive", {"id": claim["id"]})
    assert archived["archived_at"] and archived["links"]
    assert engine.call("research_claim_list", {"session_id": session})["items"] == []
    assert (
        engine.call("research_claim_list", {"session_id": session, "filter": "archived"})["items"][0]["id"]
        == claim["id"]
    )
    before = trail(engine, session)
    assert (
        engine.call("research_claim_archive", {"id": claim["id"]}) == archived
        and trail(engine, session) == before
    )
    with pytest.raises(ValueError, match="archivedReadOnly"):
        engine.call("research_claim_update", {"id": claim["id"], "statement": "Edit"})
    restored = engine.call("research_claim_restore", {"id": claim["id"]})
    assert restored["archived_at"] is None
    before = trail(engine, session)
    again = Engine(engine.data_dir, start_worker=False)
    try:
        assert again.call("research_claim_get", {"id": claim["id"]}) == restored
        assert trail(again, session) == before
    finally:
        again.close()
    with engine.db.connect() as db:
        with pytest.raises(sqlite3.IntegrityError):
            db.execute("UPDATE research_events SET payload_json='{}'")
        with pytest.raises(sqlite3.IntegrityError):
            db.execute("DELETE FROM research_events")
        db.execute("DELETE FROM research_sessions WHERE id=?", (session,))
        assert db.execute("SELECT count(*) FROM research_claim_evidence").fetchone()[0] == 0


@pytest.mark.parametrize(
    "operation", ["create", "update", "link", "relation", "unlink", "review", "archive", "restore"]
)
def test_atomic_mutation_rollback_if_event_fails(workspace, operation):
    engine, session = workspace
    source = save(engine, session)["item"]
    claim = create(engine, session)
    relation = link(engine, claim, source)
    if operation == "restore":
        engine.call("research_claim_archive", {"id": claim["id"]})
    with engine.db.connect() as db:
        before = list(db.iterdump())
        db.execute(
            "CREATE TRIGGER fail_claim_event BEFORE INSERT ON research_events WHEN NEW.event_type LIKE 'claim_%' BEGIN SELECT RAISE(ABORT,'fixture audit failure'); END"
        )
    calls = {
        "create": ("create", {"session_id": session, "statement": "New"}),
        "update": ("update", {"id": claim["id"], "statement": "Changed", "researcher_note": "Changed"}),
        "link": (
            "evidence_link",
            {
                "claim_id": claim["id"],
                "saved_evidence_id": save(engine, session, "span:4")["item"]["id"],
                "relation": "context",
            },
        ),
        "relation": ("evidence_update", {"id": relation["id"], "relation": "context"}),
        "unlink": ("evidence_unlink", {"id": relation["id"]}),
        "review": ("update", {"id": claim["id"], "review_status": "reviewed"}),
        "archive": ("archive", {"id": claim["id"]}),
        "restore": ("restore", {"id": claim["id"]}),
    }
    # Capture the complete database after fixture setup but before the failing operation.
    with engine.db.connect() as db:
        before = list(db.iterdump())
    method, params = calls[operation]
    with pytest.raises(sqlite3.IntegrityError, match="fixture audit failure"):
        engine.call("research_claim_" + method, params)
    with engine.db.connect() as db:
        assert list(db.iterdump()) == before


@pytest.mark.parametrize(
    "method,params",
    [
        ("create", {"session_id": True, "statement": "x"}),
        ("get", {"id": "1"}),
        ("update", {"id": 1, "reasoning": "hidden"}),
        ("list", {"session_id": 1, "filter": "auto"}),
        ("evidence_link", {"claim_id": 1, "saved_evidence_id": 1, "relation": "ai_supports"}),
    ],
)
def test_invalid_fields_ids_and_enums(workspace, method, params):
    engine, session = workspace
    with pytest.raises(ValueError):
        engine.call("research_claim_" + method, params)


def test_pagination_status_counts_and_read_only(workspace):
    engine, session = workspace
    claims = [create(engine, session, statement=f"Test {i}") for i in range(4)]
    before = trail(engine, session)
    first = engine.call("research_claim_list", {"session_id": session, "limit": 2})
    second = engine.call(
        "research_claim_list", {"session_id": session, "limit": 2, "after_id": first["next_after_id"]}
    )
    assert [c["id"] for c in first["items"] + second["items"]] == [c["id"] for c in reversed(claims)]
    assert first["counts"] == {"all": 4, "draft": 4, "reviewed": 0, "archived": 0}
    assert trail(engine, session) == before


def test_constraints_limits_and_no_hidden_metadata(workspace, monkeypatch):
    engine, session = workspace
    claim = create(engine, session)
    source = save(engine, session)["item"]
    relation = link(engine, claim, source)
    monkeypatch.setattr("petrus_engine.claims.LINK_LIMIT", 1)
    second = save(engine, session, "span:4")["item"]
    before = trail(engine, session)
    with pytest.raises(ValueError, match="tooManyLinks"):
        link(engine, claim, second)
    with engine.db.connect() as db:
        names = [r[1] for r in db.execute("PRAGMA table_info(research_claim_evidence)") if r[1] != "id"]
        columns = ",".join(names)
        with pytest.raises(sqlite3.IntegrityError):
            db.execute(
                f"INSERT INTO research_claim_evidence({columns}) SELECT {columns} FROM research_claim_evidence WHERE id=?",
                (relation["id"],),
            )
        with pytest.raises(sqlite3.IntegrityError):
            db.execute(
                "UPDATE research_claim_evidence SET source_snapshot_event_id=999999 WHERE id=?",
                (relation["id"],),
            )
        payloads = [
            json.loads(r[0])
            for r in db.execute("SELECT payload_json FROM research_events WHERE event_type LIKE 'claim_%'")
        ]
        assert all(
            not {"reasoning", "reasoning_content", "system_prompt", "raw_candidate"} & set(p)
            for p in payloads
        )
    assert trail(engine, session) == before
