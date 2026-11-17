"""Human workspace, source verification and durable provenance; no real LLM calls."""

import json
import sqlite3
from dataclasses import replace

import pytest
from petrus_engine.rag.index import current_units
from petrus_engine.research import fingerprint, sha256
from petrus_engine.service import Engine
from test_embeddings import env as env


@pytest.fixture
def workspace(env):
    engine, _ = env
    session = engine.call("new_session", {"title": "Workspace"})["id"]
    return engine, session


def save(engine, session, unit="span:2", **params):
    return engine.call("research_evidence_save", {"session_id": session, "unit_id": unit, **params})


def events(engine, session):
    return engine.call("session", {"id": session})["events"]


def test_migration_reopen_and_constraints(workspace):
    engine, session = workspace
    result = save(engine, session)["item"]
    with engine.db.connect() as db:
        assert (
            db.execute(
                "select count(*) from schema_migrations where version='005_research_evidence.sql'"
            ).fetchone()[0]
            == 1
        )
        with pytest.raises(sqlite3.IntegrityError):
            db.execute("update research_evidence set decision='ai_included' where id=?", (result["id"],))
    reopened = Engine(engine.data_dir, start_worker=False)
    try:
        assert reopened.call("research_evidence_get", {"id": result["id"]}) == result
        assert reopened.call("research_evidence_list", {"session_id": session})["counts"]["total"] == 1
    finally:
        reopened.close()


@pytest.mark.parametrize(
    "unit_id,provenance,page,paginated",
    [
        ("span:2", "coordinate", 2, True),
        ("span:4", "exact_page_alignment", 4, True),
        ("section:3", "section_only", None, False),
        ("chunk:1", "basic_page_text", 1, False),
    ],
)
def test_verified_source_snapshot(workspace, unit_id, provenance, page, paginated):
    engine, session = workspace
    unit = current_units(engine.db)[unit_id]
    result = save(engine, session, unit_id, decision="included", user_note="AI NOTE")["item"]
    assert result["provenance_level"] == provenance
    assert result["page_start"] == result["page_end"] == page
    assert result["supports_paginated_evidence"] is paginated
    assert result["paper_doi_snapshot"] is None
    assert result["text_snapshot"] == unit.text
    assert result["text_sha256"] == sha256(unit.text)
    assert result["section_heading_snapshot"] == unit.heading
    assert result["decision"] == "uncertain" and result["user_note"] == ""
    assert result["origin_type"] == "retrieved_source"
    assert result["source_available"] is True


def test_deterministic_fingerprint_survives_numeric_identity_replacement(workspace):
    engine, session = workspace
    unit = current_units(engine.db)["span:2"]
    digest, _ = fingerprint(unit, "paperhash")
    assert (
        fingerprint(replace(unit, unit_id="span:999", section_id=500, source_span_id=999), "paperhash")[0]
        == digest
    )
    assert fingerprint(replace(unit, text=unit.text + " changed"), "paperhash")[0] != digest
    first = save(engine, session)
    duplicate = save(engine, session)
    assert first["created"] is True and duplicate == {"created": False, "item": first["item"]}
    assert len([e for e in events(engine, session) if e["event_type"] == "evidence_saved"]) == 1
    with engine.db.connect() as db:
        db.execute("""INSERT INTO source_spans(id,paper_id,section_id,page,text,source_type)
            SELECT 999,paper_id,section_id,page,text,source_type FROM source_spans WHERE id=2""")
        db.execute("DELETE FROM source_spans WHERE id=2")
    # Numeric link becomes NULL but snapshot and fingerprint remain interpretable.
    assert save(engine, session, "span:999")["item"]["id"] == first["item"]["id"]
    other = engine.call("new_session", {"title": "Other"})["id"]
    assert save(engine, other, "span:999")["item"]["id"] != first["item"]["id"]


@pytest.mark.parametrize("decision", ["included", "excluded", "uncertain"])
def test_human_decision_note_exact_noop_events_and_filters(workspace, decision):
    engine, session = workspace
    item = save(engine, session)["item"]
    note = "  Nota humana ç 漢字\r\n\n  spaces retained  "
    updated = engine.call(
        "research_evidence_update", {"id": item["id"], "decision": decision, "user_note": note}
    )
    assert updated["user_note"] == note and updated["decision"] == decision
    assert updated["updated_at"] != item["updated_at"]
    assert updated["text_snapshot"] == item["text_snapshot"]
    before = events(engine, session)
    assert (
        engine.call("research_evidence_update", {"id": item["id"], "decision": decision, "user_note": note})
        == updated
    )
    assert events(engine, session) == before
    kinds = [e["event_type"] for e in before]
    assert kinds.count("evidence_note_updated") == 1
    assert kinds.count("evidence_decision_changed") == (decision != "uncertain")
    assert (
        engine.call("research_evidence_list", {"session_id": session, "decision": decision})["counts"][
            decision
        ]
        == 1
    )
    other = "included" if decision != "included" else "excluded"
    assert engine.call("research_evidence_list", {"session_id": session, "decision": other})["items"] == []
    for event in before:
        payload = json.loads(event["payload_json"])
        assert "text_snapshot" not in payload and "user_note" not in payload and "reasoning" not in payload
        if event["event_type"] == "evidence_note_updated":
            assert payload["new_note_snapshot"] == note
        else:
            assert "new_note_snapshot" not in payload


def test_remove_records_event_before_hard_delete_and_session_fk(workspace):
    engine, session = workspace
    item = save(engine, session)["item"]
    engine.call("research_evidence_remove", {"id": item["id"]})
    removal = events(engine, session)[0]
    assert removal["event_type"] == "evidence_removed"
    assert json.loads(removal["payload_json"])["evidence_fingerprint"] == item["evidence_fingerprint"]
    with pytest.raises(ValueError, match="research.evidenceNotFound"):
        engine.call("research_evidence_get", {"id": item["id"]})
    assert save(engine, session)["item"]["id"] > item["id"]
    with engine.db.connect() as db:
        db.execute("delete from research_sessions where id=?", (session,))
        assert db.execute("select count(*) from research_evidence").fetchone()[0] == 0
        assert db.execute("select count(*) from research_events").fetchone()[0] == 0
    with pytest.raises(ValueError, match="research.sessionNotFound"):
        save(engine, session)


def test_reprocess_and_unavailable_source_preserve_snapshot(workspace):
    engine, session = workspace
    item = save(engine, session)["item"]
    with engine.db.connect() as db:
        db.execute("update source_spans set text='reprocessed' where id=2")
        db.execute("update sections set heading='new heading' where id=2")
        db.execute("update paper_files set available=0 where paper_id=2")
    updated = engine.call("research_evidence_get", {"id": item["id"]})
    assert updated == {**item, "source_available": False}
    with engine.db.connect() as db:
        db.execute("delete from sections where id=2")
        db.execute("delete from papers where id=2")
    updated = engine.call("research_evidence_get", {"id": item["id"]})
    assert updated["paper_id"] is None and updated["section_id"] is None and updated["source_span_id"] is None
    for key in (
        "text_snapshot",
        "text_sha256",
        "paper_title_snapshot",
        "paper_sha256",
        "page_start",
        "section_heading_snapshot",
    ):
        assert updated[key] == item[key]


@pytest.mark.parametrize(
    "params",
    [
        {"unit_id": "span:999"},
        {"paper_id": 3},
        {"text": "fake text"},
        {"page_start": 99},
        {"page_end": 99},
        {"provenance": "section_only"},
        {"supports_paginated_evidence": False},
        {"evidence_role": "results"},
        {"origin_type": "ask_answer"},
        {"evidence": {"unit_id": "span:2", "text": "arbitrary frontend paper text"}},
        {"response_id": "forged"},
    ],
)
def test_forged_or_stale_frontend_evidence_rejected(workspace, params):
    engine, session = workspace
    with pytest.raises(ValueError):
        save(engine, session, **params)
    assert engine.call("research_evidence_list", {"session_id": session})["counts"]["total"] == 0


@pytest.mark.parametrize(
    "status,origin",
    [("accepted", "ask_answer"), ("rejected", "retrieved_source"), ("generation_failed", "retrieved_source")],
)
def test_ask_receipt_membership_question_local_label_and_no_reasoning(workspace, monkeypatch, status, origin):
    engine, session = workspace
    unit = current_units(engine.db)["span:2"]
    response = {
        "question": "Original question",
        "evidence": [
            {
                "evidence_id": "E6",
                "unit_id": unit.unit_id,
                "paper_id": unit.paper_id,
                "text": unit.text,
                "page_start": unit.page_start,
                "page_end": unit.page_end,
                "provenance": str(unit.provenance_level),
            }
        ],
        "execution_metadata": {"final_status": status},
        "answer": "unused",
    }
    monkeypatch.setattr("petrus_engine.rag.ask.AskPetrusService.ask", lambda *args: response)
    returned = engine.call("ask", {"question": "Original question"})
    token = returned["response_id"]
    saved = save(
        engine,
        session,
        response_id=token,
        evidence_label="E6",
        question_snapshot="FORGED",
        reasoning="PRIVATE",
    )["item"]
    assert saved["origin_type"] == origin and saved["question_snapshot"] == "Original question"
    assert saved["evidence_label_snapshot"] == "E6"
    assert "PRIVATE" not in json.dumps(saved)
    with pytest.raises(ValueError, match="research.invalidOrigin"):
        save(engine, session, response_id=token, evidence_label="E7")
    with pytest.raises(ValueError, match="research.invalidOrigin"):
        save(engine, session, "span:4", response_id=token, evidence_label="E6")
    with engine.db.connect() as db:
        db.execute("update source_spans set text='changed after answer' where id=2")
    with pytest.raises(ValueError, match="research.staleEvidence"):
        save(engine, session, response_id=token, evidence_label="E6")


def test_persisted_ask_origin_and_membership(workspace):
    engine, session = workspace
    unit = current_units(engine.db)["span:2"]
    payload = {
        "question": "Question",
        "execution_metadata": {"final_status": "accepted"},
        "evidence": [{"evidence_id": "E6", "unit_id": "span:2", "paper_id": 2, "text": unit.text}],
    }
    with engine.db.connect() as db:
        event_id = db.execute(
            "insert into research_events(session_id,event_type,payload_json) values(?,'ask',?)",
            (session, json.dumps(payload)),
        ).lastrowid
    item = save(engine, session, research_event_id=event_id, evidence_label="E6")["item"]
    assert item["research_event_id"] == event_id and item["question_snapshot"] == "Question"
    with pytest.raises(ValueError, match="research.invalidOrigin"):
        save(engine, session, "span:4", research_event_id=event_id, evidence_label="E6")


@pytest.mark.parametrize(
    "changes",
    [{"decision": "auto"}, {"user_note": None}, {"text_snapshot": "fake"}, {"user_note": "x" * 100001}],
)
def test_snapshot_not_editable_and_invalid_human_fields(workspace, changes):
    engine, session = workspace
    item = save(engine, session)["item"]
    with pytest.raises(ValueError):
        engine.call("research_evidence_update", {"id": item["id"], **changes})
