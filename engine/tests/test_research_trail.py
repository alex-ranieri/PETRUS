"""Research history contracts with real retrieval and synthetic model output only."""

import json
import sqlite3
from pathlib import Path

import pytest
from petrus_engine.database import Database
from petrus_engine.research import sha256
from petrus_engine.service import Engine
from petrus_engine.trail import PAYLOAD_LIMIT, ResearchTrailService, append_event
from test_03b import FakeLLMProvider, make_long_sources
from test_embeddings import env as env


@pytest.fixture
def setup_trail(env, monkeypatch):
    engine, _ = env
    make_long_sources(engine)
    model = FakeLLMProvider()
    model.provider_id = "synthetic-local"
    monkeypatch.setattr("petrus_engine.llm.local.configured_llm", lambda _: model)
    monkeypatch.setattr("petrus_engine.rag.providers.configured_provider", lambda _: None)
    session = engine.call("new_session", {"title": "Trail fixture"})["id"]
    return engine, session, model


def listed(engine, session, **params):
    return engine.call("research_trail_list", {"session_id": session, **params})


def detailed(engine, session, item):
    return engine.call("research_trail_get", {"session_id": session, "event_id": item["id"]})


def ask(engine, session, question="mosquito"):
    return engine.call("ask", {"question": question, "session_id": session})


def test_session_created_actor_version_and_read_only_projection(setup_trail):
    engine, session, _ = setup_trail
    with engine.db.connect() as db:
        before = list(db.iterdump())
    page = listed(engine, session)
    assert page["has_legacy_activity"] is False
    assert [(row["event_type"], row["actor_type"], row["payload_version"]) for row in page["items"]] == [
        ("session_created", "user", 1)
    ]
    assert detailed(engine, session, page["items"][0])["metadata"]["title"] == "Trail fixture"
    assert listed(engine, session) == page
    with engine.db.connect() as db:
        assert list(db.iterdump()) == before


@pytest.mark.parametrize(
    "mutation", ["UPDATE research_events SET payload_json='{}'", "DELETE FROM research_events"]
)
def test_database_append_only(setup_trail, mutation):
    engine, session, _ = setup_trail
    before = listed(engine, session)
    with engine.db.connect() as db, pytest.raises(sqlite3.IntegrityError, match="research_trail_append_only"):
        db.execute(mutation)
    assert listed(engine, session) == before


@pytest.mark.parametrize("actor", ["robot", "", 42])
def test_actor_validation(setup_trail, actor):
    engine, session, _ = setup_trail
    with engine.db.connect() as db, pytest.raises(ValueError, match="trail.invalidActor"):
        append_event(db, session, "question_asked", {}, actor=actor)


def test_session_fk_and_version_constraint(setup_trail):
    engine, session, _ = setup_trail
    with engine.db.connect() as db:
        with pytest.raises(sqlite3.IntegrityError):
            db.execute(
                "INSERT INTO research_events(session_id,event_type,payload_version) VALUES(?,'question_asked',2)",
                (session,),
            )
        with pytest.raises(sqlite3.IntegrityError):
            db.execute("INSERT INTO research_events(session_id,event_type) VALUES(999,'question_asked')")
        db.execute("DELETE FROM research_sessions WHERE id=?", (session,))
        assert db.execute("SELECT count(*) FROM research_events").fetchone()[0] == 0


def test_tracked_ask_actual_retrieval_no_automatic_saved_evidence(setup_trail):
    engine, session, model = setup_trail
    response = ask(engine, session)
    assert response["trail"]["state"] == "recorded"
    page = listed(engine, session)
    assert [row["event_type"] for row in page["items"]] == [
        "session_created",
        "question_asked",
        "retrieval_completed",
        "ask_accepted",
    ]
    assert [row["actor_type"] for row in page["items"]] == ["user", "user", "system", "ai"]
    question = detailed(engine, session, page["items"][1])["metadata"]
    assert question["question"] == "mosquito" and question["question_sha256"] == sha256("mosquito")
    retrieval = detailed(engine, session, page["items"][2])["metadata"]
    assert retrieval["selected_count"] == len(response["evidence"])
    assert retrieval["returned_candidate_count"] == response["retrieval_metadata"]["retrieved"]
    assert (
        retrieval["configuration"]["rrf_k"] == 60 and retrieval["configuration"]["ranking_observed"] is True
    )
    assert retrieval["observed_sources"][0]["source"] == "lexical_search"
    assert all(item["text_sha256"] and item["evidence_fingerprint"] for item in retrieval["selected"])
    assert "text" not in json.dumps(retrieval["selected"]).replace("text_sha256", "")
    assert "answer" not in page["items"][-1]["metadata"]  # details loaded separately
    result = detailed(engine, session, page["items"][-1])["metadata"]
    assert result["answer"] == response["answer"] and result["answer_sha256"] == sha256(response["answer"])
    assert result["model_id"] == model.model_id and result["citations"] == ["E1"]
    assert (
        result["question_event_id"] == page["items"][1]["id"]
        and result["retrieval_event_id"] == page["items"][2]["id"]
    )
    assert engine.call("research_evidence_list", {"session_id": session})["items"] == []
    assert len(model.calls) == 1


@pytest.mark.parametrize(
    "mode,kind,actor",
    [
        ("abstained", "ask_abstained", "ai"),
        ("no_evidence", "ask_abstained", "system"),
        ("rejected", "ask_rejected", "system"),
        ("failed", "ask_generation_failed", "system"),
        ("not_configured", "ask_generation_failed", "system"),
    ],
)
def test_distinct_results_and_no_invalid_candidates(setup_trail, monkeypatch, mode, kind, actor):
    engine, session, model = setup_trail
    question = "mosquito"
    if mode == "abstained":
        model.reply = {"answer": "No evidence", "insufficient_evidence": True, "limitations": []}
    elif mode == "no_evidence":
        question = "unfindable astronomy query"
    elif mode == "rejected":
        model.reply = "PRIVATE RAW INVALID CANDIDATE <think>PRIVATE REASONING</think> [E99]"
    elif mode == "failed":
        model.error = RuntimeError("PRIVATE SERVER ERROR")
    elif mode == "not_configured":
        monkeypatch.setattr("petrus_engine.llm.local.configured_llm", lambda _: None)
    response = ask(engine, session, question)
    assert response["trail"]["state"] == "recorded"
    item = listed(engine, session)["items"][-1]
    assert (item["event_type"], item["actor_type"]) == (kind, actor)
    metadata = detailed(engine, session, item)["metadata"]
    assert metadata["final_status"] == response["execution_metadata"]["final_status"]
    if kind in ("ask_rejected", "ask_generation_failed"):
        assert "answer" not in metadata
    with engine.db.connect() as db:
        payloads = " ".join(row[0] for row in db.execute("SELECT payload_json FROM research_events"))
    assert "PRIVATE" not in payloads and "reasoning_content" not in payloads and "<think>" not in payloads


def test_ask_without_session_is_nonpersistent(setup_trail):
    engine, session, model = setup_trail
    before = listed(engine, session)
    result = engine.call("ask", {"question": "mosquito"})
    assert "trail" not in result and len(model.calls) == 1
    assert listed(engine, session) == before
    with engine.db.connect() as db:
        assert db.execute("SELECT count(*) FROM research_sessions").fetchone()[0] == 1


def test_note_versions_decisions_and_source_history_after_removal(setup_trail):
    engine, session, _ = setup_trail
    response = ask(engine, session)
    source = response["evidence"][0]
    saved = engine.call(
        "research_evidence_save",
        {"session_id": session, "response_id": response["response_id"], "evidence": source},
    )["item"]
    assert saved["research_event_id"] == response["trail"]["result_event_id"]
    notes = ["  Human ç\r\n漢字  ", "Second human version\n  "]
    for decision, note in zip(["included", "uncertain"], notes):
        engine.call("research_evidence_update", {"id": saved["id"], "decision": decision, "user_note": note})
    engine.call("research_evidence_update", {"id": saved["id"], "decision": "included"})
    before = listed(engine, session)
    engine.call(
        "research_evidence_update", {"id": saved["id"], "decision": "included", "user_note": notes[-1]}
    )
    assert listed(engine, session) == before
    details = [detailed(engine, session, item) for item in before["items"]]
    changes = [item["metadata"] for item in details if item["event_type"] == "evidence_decision_changed"]
    assert [(item["old_decision"], item["new_decision"]) for item in changes] == [
        ("uncertain", "included"),
        ("included", "uncertain"),
        ("uncertain", "included"),
    ]
    versions = [item["metadata"] for item in details if item["event_type"] == "evidence_note_updated"]
    assert [item["new_note_snapshot"] for item in versions] == notes
    assert versions[0]["old_note_sha256"] == sha256("") and versions[1]["old_note_sha256"] == sha256(notes[0])
    assert versions[1]["new_note_sha256"] == sha256(notes[1])
    saved_event = next(item for item in details if item["event_type"] == "evidence_saved")
    assert saved_event["metadata"]["source_snapshot"]["text_snapshot"] == source["text"]
    engine.call("research_evidence_remove", {"id": saved["id"]})
    removal = detailed(engine, session, listed(engine, session)["items"][-1])
    assert removal["event_type"] == "evidence_removed" and not removal["evidence_available"]
    assert removal["metadata"]["paper_title_snapshot"] == source["paper_title"]
    assert removal["metadata"]["paper_sha256"] == saved["paper_sha256"]
    assert removal["metadata"]["decision"] == "included"
    assert removal["metadata"]["evidence_saved_event_id"] == saved_event["id"]
    assert "source_snapshot" not in removal["metadata"]  # one durable copy in original save event
    assert (
        detailed(engine, session, saved_event)["metadata"]["source_snapshot"]["text_snapshot"]
        == source["text"]
    )


def test_manual_answer_save_reuses_result_and_persisted_origin(setup_trail):
    engine, session, _ = setup_trail
    response = ask(engine, session)
    event_id = engine.call("save_ask_event", {"session_id": session, "response": response})["event_id"]
    row = listed(engine, session)["items"][-1]
    assert row["event_type"] == "ask_saved_to_session" and row["id"] == event_id
    metadata = detailed(engine, session, row)["metadata"]
    assert (
        metadata["ask_result_event_id"] == response["trail"]["result_event_id"] and "answer" not in metadata
    )
    saved = engine.call(
        "research_evidence_save",
        {
            "session_id": session,
            "research_event_id": event_id,
            "unit_id": response["evidence"][0]["unit_id"],
            "evidence_label": "E1",
        },
    )["item"]
    assert saved["origin_type"] == "ask_answer" and saved["question_snapshot"] == "mosquito"


def test_order_pagination_and_reopen_identical(setup_trail):
    engine, session, _ = setup_trail
    with engine.db.connect() as db:
        for _ in range(3):
            db.execute(
                "INSERT INTO research_events(session_id,event_type,created_at) VALUES(?,'session_created','2030-01-01 00:00:00')",
                (session,),
            )
    first = listed(engine, session, limit=2)
    next_page = listed(engine, session, limit=2, after_event_id=first["next_after_event_id"])
    ids = [i["id"] for i in first["items"] + next_page["items"]]
    assert ids == sorted(ids) and len(set(ids)) == 4
    before = listed(engine, session)
    restarted = Engine(engine.data_dir, start_worker=False)
    try:
        assert listed(restarted, session) == before
    finally:
        restarted.close()


@pytest.mark.parametrize(
    "params", [{"limit": 0}, {"limit": 101}, {"after_event_id": 999}, {"actor_type": "robot"}]
)
def test_invalid_list_contract(setup_trail, params):
    engine, session, _ = setup_trail
    with pytest.raises(ValueError):
        listed(engine, session, **params)


def test_payload_limits_and_atomic_note_rollback(setup_trail):
    engine, session, _ = setup_trail
    with engine.db.connect() as db:
        with pytest.raises(ValueError, match="trail.payloadTooLarge"):
            append_event(
                db, session, "evidence_note_updated", {"new_note_snapshot": "x" * (PAYLOAD_LIMIT + 1)}
            )
        with pytest.raises(sqlite3.IntegrityError, match="trail.invalidPayload"):
            db.execute(
                "INSERT INTO research_events(session_id,event_type,payload_json) VALUES(?,'question_asked',?)",
                (session, json.dumps({"x": "x" * PAYLOAD_LIMIT})),
            )
    saved = engine.call("research_evidence_save", {"session_id": session, "unit_id": "span:2"})["item"]
    note = "漢" * 100000
    updated = engine.call("research_evidence_update", {"id": saved["id"], "user_note": note})
    assert updated["user_note"] == note
    detail = detailed(engine, session, listed(engine, session)["items"][-1])
    assert detail["metadata"]["new_note_snapshot"] == note
    before = listed(engine, session)
    with engine.db.connect() as db:
        db.execute(
            "CREATE TRIGGER fail_note BEFORE INSERT ON research_events WHEN NEW.event_type='evidence_note_updated' BEGIN SELECT RAISE(ABORT,'fixture failed audit'); END"
        )
    with pytest.raises(sqlite3.IntegrityError):
        engine.call("research_evidence_update", {"id": saved["id"], "user_note": "must roll back"})
    assert engine.call("research_evidence_get", {"id": saved["id"]})["user_note"] == note
    assert listed(engine, session) == before


def test_trail_failure_after_generation_is_explicit_without_retry(setup_trail, monkeypatch):
    engine, session, model = setup_trail

    def fail(*args, **kwargs):
        raise sqlite3.OperationalError("PRIVATE SERVER ERROR")

    monkeypatch.setattr(ResearchTrailService, "finish", fail)
    response = ask(engine, session)
    assert response["execution_metadata"]["final_status"] == "accepted"
    assert (
        response["trail"]["state"] == "failed" and response["trail"]["warning"] == "trail.persistenceFailed"
    )
    assert len(model.calls) == 1
    assert [i["event_type"] for i in listed(engine, session)["items"]] == [
        "session_created",
        "question_asked",
    ]
    assert engine.call("research_evidence_list", {"session_id": session})["items"] == []


def test_old_session_boundary_no_speculative_backfill_or_snapshot_change(tmp_path):
    path = tmp_path / "data" / "petrus.sqlite3"
    path.parent.mkdir()
    migrations = Path("src-tauri/migrations")
    with sqlite3.connect(path) as db:
        db.execute("CREATE TABLE schema_migrations(version TEXT PRIMARY KEY)")
        for file in sorted(migrations.glob("*.sql"))[:5]:
            db.executescript(file.read_text())
            db.execute("INSERT INTO schema_migrations VALUES(?)", (file.name,))
        db.execute("INSERT INTO research_sessions(id,title) VALUES(1,'Old session')")
        db.execute(
            "INSERT INTO research_events(id,session_id,event_type,payload_json,created_at) VALUES(1,1,'session_created','{}','2026-01-01 00:00:00')"
        )
        db.execute(
            "INSERT INTO research_events(id,session_id,event_type,payload_json,created_at) VALUES(2,1,'evidence_note_updated','{\"id\":42}','2026-01-01 00:01:00')"
        )
        old = db.execute(
            "SELECT id,session_id,event_type,payload_json,created_at FROM research_events"
        ).fetchall()
    Database(path)
    Database(path)
    engine = Engine(path.parent, start_worker=False)
    try:
        page = listed(engine, 1)
        assert page["has_legacy_activity"]
        assert [r["event_type"] for r in page["items"]] == [
            "session_created",
            "evidence_note_updated",
            "trail_tracking_started",
        ]
        with engine.db.connect() as db:
            assert [
                tuple(r)
                for r in db.execute(
                    "SELECT id,session_id,event_type,payload_json,created_at FROM research_events WHERE id<=2"
                )
            ] == old
            assert (
                db.execute(
                    "SELECT count(*) FROM research_events WHERE event_type='trail_tracking_started'"
                ).fetchone()[0]
                == 1
            )
        assert "new_note_snapshot" not in detailed(engine, 1, page["items"][1])["metadata"]
        assert [r["actor_type"] for r in page["items"]] == ["user", "user", "system"]
    finally:
        engine.close()


@pytest.mark.parametrize(
    "payload",
    [
        {"reasoning": "PRIVATE"},
        {"x": {"reasoning_content": "PRIVATE"}},
        {"raw_candidate": "PRIVATE"},
        ["not an object"],
    ],
)
def test_forbidden_diagnostics_not_persisted(setup_trail, payload):
    engine, session, _ = setup_trail
    with engine.db.connect() as db, pytest.raises(ValueError, match="trail.invalidPayload"):
        append_event(db, session, "ask_rejected", payload)


def test_actor_filters_do_not_reorder_events(setup_trail):
    engine, session, _ = setup_trail
    ask(engine, session)
    all_items = listed(engine, session)["items"]
    for actor in ("user", "ai", "system"):
        assert listed(engine, session, actor_type=actor)["items"] == [
            item for item in all_items if item["actor_type"] == actor
        ]


def test_question_limit_is_explicit_before_generation(setup_trail):
    engine, session, model = setup_trail
    before = listed(engine, session)
    with pytest.raises(ValueError, match="ask_invalid_question"):
        ask(engine, session, "x" * 2001)
    assert listed(engine, session) == before and not model.calls
    text = "z" * 2000
    ask(engine, session, text)
    item = next(i for i in listed(engine, session)["items"] if i["event_type"] == "question_asked")
    assert detailed(engine, session, item)["metadata"]["question"] == text


def test_answer_limit_warns_without_truncation_or_regeneration(setup_trail):
    engine, session, model = setup_trail
    model.reply = {"answer": "x" * 2_000_000 + " [E1]", "insufficient_evidence": False, "limitations": []}
    response = ask(engine, session)
    assert response["execution_metadata"]["final_status"] == "accepted"
    assert response["trail"]["state"] == "failed" and len(model.calls) == 1
    assert len(response["answer"]) > 2_000_000
    assert [i["event_type"] for i in listed(engine, session)["items"]] == [
        "session_created",
        "question_asked",
    ]


def test_observation_failure_does_not_change_successful_retrieval(setup_trail, monkeypatch):
    engine, session, model = setup_trail

    def fail(*args):
        raise RuntimeError("fixture metadata unavailable")

    monkeypatch.setattr("petrus_engine.trail.fingerprint", fail)
    response = ask(engine, session)
    assert (
        response["execution_metadata"]["final_status"] == "accepted"
        and response["trail"]["state"] == "recorded"
    )
    retrieval = detailed(engine, session, listed(engine, session)["items"][2])["metadata"]
    assert retrieval["configuration"]["ranking_observed"] is False
    assert "semantic_unavailable_lexical_fallback" not in response["limitations"]
    assert len(model.calls) == 1


def test_lexical_fallback_reports_unknown_rankings_without_second_generation(setup_trail, monkeypatch):
    engine, session, model = setup_trail
    from test_embeddings import FakeEmbeddingProvider

    monkeypatch.setattr("petrus_engine.rag.providers.configured_provider", lambda _: FakeEmbeddingProvider())

    def fail(*args, **kwargs):
        raise RuntimeError("PRIVATE ERROR")

    monkeypatch.setattr("petrus_engine.rag.retrieval.HybridRetriever.semantic_search", fail)
    response = ask(engine, session)
    assert response["trail"]["state"] == "recorded" and len(model.calls) == 1
    retrieval = detailed(engine, session, listed(engine, session)["items"][2])["metadata"]
    assert retrieval["configuration"]["effective_strategy"] == "lexical_fallback"
    assert retrieval["configuration"]["ranking_observed"] is False
    assert all("lexical_rank" not in identity for identity in retrieval["selected"])
    assert "PRIVATE" not in json.dumps(retrieval)


def test_legacy_removal_captures_existing_snapshot_without_rewriting_history(setup_trail):
    engine, session, _ = setup_trail
    saved = engine.call("research_evidence_save", {"session_id": session, "unit_id": "span:2"})["item"]
    # Simulate a genuine pre-006 saved event, whose payload had no source text.
    with engine.db.connect() as db:
        db.execute("DROP TRIGGER research_events_no_update")
        db.execute(
            "UPDATE research_events SET legacy=1,payload_json=? WHERE event_type='evidence_saved'",
            (
                json.dumps(
                    {
                        "id": saved["id"],
                        "paper_id": saved["paper_id"],
                        "evidence_fingerprint": saved["evidence_fingerprint"],
                    }
                ),
            ),
        )
        db.execute(
            "CREATE TRIGGER research_events_no_update BEFORE UPDATE ON research_events BEGIN SELECT RAISE(ABORT,'research_trail_append_only'); END"
        )
        original = tuple(
            db.execute(
                "SELECT id,payload_json,created_at FROM research_events WHERE event_type='evidence_saved'"
            ).fetchone()
        )
    engine.call("research_evidence_remove", {"id": saved["id"]})
    removal = detailed(engine, session, listed(engine, session)["items"][-1])
    assert removal["metadata"]["source_snapshot"]["text_snapshot"] == saved["text_snapshot"]
    assert removal["metadata"]["evidence_saved_event_id"] == original[0]
    with engine.db.connect() as db:
        assert (
            tuple(
                db.execute(
                    "SELECT id,payload_json,created_at FROM research_events WHERE id=?", (original[0],)
                ).fetchone()
            )
            == original
        )


def test_manual_save_cannot_reference_a_different_answer_snapshot(setup_trail):
    engine, session, _ = setup_trail
    response = ask(engine, session)
    before = listed(engine, session)
    with pytest.raises(ValueError, match="ask_invalid_event"):
        engine.call(
            "save_ask_event",
            {"session_id": session, "response": {**response, "answer": "Different valid text [E1]."}},
        )
    assert listed(engine, session) == before


def test_manual_save_in_another_session_keeps_standalone_validated_snapshot(setup_trail):
    engine, session, _ = setup_trail
    response = ask(engine, session)
    other = engine.call("new_session", {"title": "Another target"})["id"]
    event = engine.call("save_ask_event", {"session_id": other, "response": response})
    detail = detailed(engine, other, {"id": event["event_id"]})
    assert detail["object_type"] == "ask_snapshot" and detail["object_id"] is None
    assert detail["metadata"]["answer"] == response["answer"]
