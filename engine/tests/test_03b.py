import json
from dataclasses import replace

import pytest
from petrus_engine.graph.semantic import paper_centroids, semantic_relations
from petrus_engine.rag.ask import AskPetrusService, validate_answer
from petrus_engine.rag.contracts import RetrievalHit
from petrus_engine.rag.evidence import EvidenceRepository, subdivide_span
from petrus_engine.rag.index import EmbeddingIndexService, current_units
from petrus_engine.rag.query import plan_query
from petrus_engine.rag.retrieval import HybridRetriever, diversify, finalize
from test_embeddings import env as env


class FakeLLMProvider:
    model_id = "fake-local-chat"

    def __init__(self, reply=None, error=None):
        self.reply = reply or {
            "answer": "The synthetic observations describe the method [E1].",
            "insufficient_evidence": False,
            "limitations": [],
        }
        self.error = error
        self.calls = []

    def answer(self, question, evidence, language="en"):
        self.calls.append((question, evidence, language))
        if self.error:
            raise self.error
        return json.dumps(self.reply) if isinstance(self.reply, dict) else self.reply

    def repair(self, question, evidence, previous_output, validation_errors, language="en"):
        return self.answer(question, evidence, language)

    def expand_query(self, query):
        return ["synthetic reconstruction method"]


def make_long_sources(engine):
    with engine.db.connect() as db:
        db.execute(
            "UPDATE source_spans SET text=? WHERE id=2",
            ("Synthetic reconstruction used documented measurements and controlled observations. " * 4,),
        )
        db.execute(
            "UPDATE sections SET text=? WHERE id=3",
            ("Synthetic results describe observations and their uncertainty in the original source. " * 4,),
        )


def test_roles_inherit_methods_and_exclude_bibliography(env):
    engine, provider = env
    with engine.db.connect() as db:
        ref = db.execute(
            'INSERT INTO "references"(source_paper_id,title) VALUES(2,?)', ("Cited synthetic source",)
        ).lastrowid
        db.execute(
            "INSERT INTO source_spans(paper_id,reference_id,page,text,source_type) VALUES(2,?,2,'mosquito reference entry','grobid_coordinates')",
            (ref,),
        )
        db.execute(
            "INSERT INTO sections(id,paper_id,parent_section_id,section_type,heading,text) VALUES(20,2,2,'other','Child','Synthetic child')"
        )
    raw = list(EvidenceRepository(engine.db).iter_units(2))
    assert next(u for u in raw if u.unit_id == "section:20").evidence_role == "methods"
    assert any(u.evidence_role == "bibliography" for u in raw)
    EmbeddingIndexService(engine.db, provider).index_paper(2)
    assert all(
        h.unit.evidence_role != "bibliography"
        for h in HybridRetriever(engine.db, provider).semantic_search("mosquito")
    )
    assert any(
        h.unit.evidence_role == "bibliography"
        for h in HybridRetriever(engine.db, provider, include_bibliography=True).semantic_search("mosquito")
    )


def test_subdivision_is_lossless_and_preserves_provenance(env):
    engine, _ = env
    unit = next(EvidenceRepository(engine.db).iter_units(2))
    unit = replace(
        unit, text="First paragraph has controlled observations.\n\nSecond sentence has uncertainty. " * 10
    )
    parts = subdivide_span(unit, 120)
    assert len(parts) > 1 and "".join(p.text for p in parts) == unit.text
    assert all(len(p.text) <= 120 and p.unit_id.startswith(unit.unit_id + ":part:") for p in parts)
    assert all(
        p.paper_id == unit.paper_id
        and p.section_id == unit.section_id
        and p.source_span_id == unit.source_span_id
        and p.evidence_role == unit.evidence_role
        and p.page_start == unit.page_start
        and p.provenance_level == unit.provenance_level
        for p in parts
    )
    assert all(p.text == unit.text[p.part_start : p.part_end] for p in parts)


def test_subdivision_invalidates_parent_and_is_idempotent(env):
    engine, provider = env
    make_long_sources(engine)
    EmbeddingIndexService(engine.db, provider).index_paper(2)
    engine.call("save_settings", {"embedding_max_chars": 100})
    service = EmbeddingIndexService(engine.db, provider)
    assert service.remove_stale() == 1
    first = service.index_paper(2)
    second = service.index_paper(2)
    assert first["indexed"] > 1 and second["indexed"] == 0 and second["cached"] == first["indexed"]
    assert all(len(u.text) <= 100 for u in current_units(engine.db).values())


def test_diversity_and_moderate_method_boost(env):
    engine, _ = env
    unit = next(EvidenceRepository(engine.db).iter_units(2))
    hits = [RetrievalHit(replace(unit, unit_id=str(i), paper_id=1), 1 - i * 0.01) for i in range(4)]
    hits.append(RetrievalHit(replace(unit, unit_id="other", paper_id=2), 0.8))
    assert [h.unit.paper_id for h in diversify(hits, 3)] == [1, 2, 1]
    ordinary = replace(unit, unit_id="general", paper_id=1, evidence_role="body")
    final = finalize([RetrievalHit(ordinary, 1), RetrievalHit(unit, 0.95)], "software method", 2)
    assert final[0].unit.evidence_role == "methods" and final[0].section_boost == 1.15
    assert final[0].score == 0.95


def test_query_plan_language_intent_and_expansion():
    plan = plan_query("Qual método de reconstrução filogenética?")
    assert plan.detected_language == "pt-BR" and plan.intent == "methods"
    assert plan.original_query == "Qual método de reconstrução filogenética?"
    assert plan_query("What results were observed?").intent == "results"
    assert plan_query("limitações do estudo").intent == "limitations"
    assert plan_query("vigilância genômica").detected_language == "pt-BR"
    assert plan_query("genomic surveillance").detected_language == "en"


def test_ask_evidence_only_citations_and_language(env):
    engine, _ = env
    make_long_sources(engine)
    fake = FakeLLMProvider()
    ask = AskPetrusService(engine.db, llm=fake, expand=True)
    # Reuse the actual controlled source; isolate only retrieval ordering for this test.
    units = list(current_units(engine.db).values())
    chosen = next(u for u in units if u.paper_id == 2)
    ask.retriever.hybrid_search = lambda *args: [RetrievalHit(chosen, 0.8)]
    response = ask.ask("Qual método foi utilizado?")
    assert not response["insufficient_evidence"] and response["citations"] == ["E1"]
    assert fake.calls[0][2] == "pt-BR" and fake.calls[0][1] == response["evidence"]
    assert response["evidence"][0]["page_start"] == 2
    assert response["retrieval_metadata"]["query_plan"]["expanded_terms"]


@pytest.mark.parametrize(
    "reply,code",
    [
        (
            {"answer": "Invented [E99]", "insufficient_evidence": False, "limitations": []},
            "ask_invalid_citation",
        ),
        (
            {"answer": "No citation", "insufficient_evidence": False, "limitations": []},
            "ask_missing_citations",
        ),
        ("not-json", "llm_response_rejected"),
        (
            {"answer": "A [E1]\n\nUncited claim", "insufficient_evidence": False, "limitations": []},
            "ask_uncited_paragraph",
        ),
    ],
)
def test_ask_rejects_invalid_or_malformed_answers(env, reply, code):
    engine, _ = env
    make_long_sources(engine)
    ask = AskPetrusService(engine.db, llm=FakeLLMProvider(reply))
    unit = next(u for u in current_units(engine.db).values() if u.paper_id == 2)
    ask.retriever.hybrid_search = lambda *args: [RetrievalHit(unit, 0.8)]
    result = ask.ask("method?")
    assert not result["insufficient_evidence"] and code in result["limitations"] and not result["citations"]


def test_insufficient_evidence_and_timeout(env):
    engine, _ = env
    fake = FakeLLMProvider()
    ask = AskPetrusService(engine.db, llm=fake)
    ask.retriever.hybrid_search = lambda *args: []
    result = ask.ask("Qual método?")
    assert result["insufficient_evidence"] and not fake.calls
    assert result["answer"].startswith("Não encontrei")
    make_long_sources(engine)
    unit = next(u for u in current_units(engine.db).values() if u.paper_id == 2)
    ask.llm = FakeLLMProvider(error=TimeoutError())
    ask.retriever.hybrid_search = lambda *args: [RetrievalHit(unit, 1)]
    assert "llm_timeout" in ask.ask("method?")["limitations"]


def test_centroid_and_semantic_relations_exclude_bibliography(env):
    engine, provider = env
    make_long_sources(engine)
    with engine.db.connect() as db:
        db.execute(
            "UPDATE chunks SET text=? WHERE paper_id=1",
            ("Synthetic reconstruction used documented measurements and controlled observations. " * 4,),
        )
    service = EmbeddingIndexService(engine.db, provider)
    service.index_paper(1)
    service.index_paper(2)
    units = current_units(engine.db)
    with engine.db.connect() as db:
        centers = paper_centroids(db, units, provider, {1, 2})
        assert set(centers) == {1, 2}
        edges = semantic_relations(db, units, provider, {1, 2})
        assert len(edges) == 1 and edges[0]["score"] == pytest.approx(1)
        assert edges[0]["relation_type"] == "SEMANTIC_SIMILARITY"
        excluded = {key: replace(u, evidence_role="bibliography") for key, u in units.items()}
        assert not paper_centroids(db, excluded, provider, {1, 2})


def test_local_llm_http_and_health_contract(monkeypatch):
    from petrus_engine.llm.local import OpenAICompatibleLLMProvider

    requests = []

    class Response:
        status = 200

        def read(self, limit):
            return json.dumps(
                {
                    "choices": [
                        {
                            "message": {
                                "content": '{"answer":"A [E1]","insufficient_evidence":false,"limitations":[]}'
                            }
                        }
                    ]
                }
            ).encode()

    class Connection:
        def __init__(self, *args, **kwargs):
            pass

        def request(self, method, path, body, headers):
            requests.append((path, json.loads(body)))

        def getresponse(self):
            return Response()

        def close(self):
            pass

    monkeypatch.setattr("petrus_engine.llm.local.http.client.HTTPConnection", Connection)
    provider = OpenAICompatibleLLMProvider("exact-local-id")
    answer = provider.answer("question", [{"evidence_id": "E1", "text": "controlled"}])
    assert validate_answer(json.loads(answer), {"E1"})[2] == ["E1"]
    assert requests[0][0] == "/v1/chat/completions" and "ONLY" in requests[0][1]["messages"][0]["content"]
    assert "tools" not in requests[0][1]
    with pytest.raises(ValueError):
        OpenAICompatibleLLMProvider("x", "http://example.com/v1")


def test_save_ask_event_keeps_snapshot_and_rejects_stale(env):
    engine, _ = env
    make_long_sources(engine)
    unit = next(u for u in current_units(engine.db).values() if u.paper_id == 2)
    ask = AskPetrusService(engine.db, llm=FakeLLMProvider())
    ask.retriever.hybrid_search = lambda *args: [RetrievalHit(unit, 0.8)]
    result = ask.ask("method?")
    session = engine.call("new_session", {"title": "Synthetic session"})
    event = engine.call("save_ask_event", {"session_id": session["id"], "response": result})
    with engine.db.connect() as db:
        saved = db.execute("SELECT * FROM research_events WHERE id=?", (event["event_id"],)).fetchone()
        assert saved["event_type"] == "ask" and saved["created_at"]
        assert json.loads(saved["payload_json"])["evidence_ids"] == ["E1"]
    result["evidence"][0]["page_start"] = 999
    with pytest.raises(ValueError):
        engine.call("save_ask_event", {"session_id": session["id"], "response": result})


def test_invalid_citations_in_limitations_and_context_budget(env):
    with pytest.raises(ValueError, match="ask_invalid_citation"):
        validate_answer(
            {"answer": "A [E1]", "insufficient_evidence": False, "limitations": ["Unknown [E99]"]}, {"E1"}
        )
    with pytest.raises(ValueError, match="ask_invalid_citation"):
        validate_answer(
            {"answer": "A [E1] [Eabc]", "insufficient_evidence": False, "limitations": []}, {"E1"}
        )
    engine, _ = env
    make_long_sources(engine)
    ask = AskPetrusService(engine.db, llm=FakeLLMProvider())
    unit = next(u for u in current_units(engine.db).values() if u.paper_id == 2)
    ask.retriever.hybrid_search = lambda *args: [
        RetrievalHit(
            replace(unit, unit_id=str(i), text=("Synthetic content " + str(i) + " ") * 170), 1 - i * 0.01
        )
        for i in range(8)
    ]
    result = ask.ask("method?")
    assert result["retrieval_metadata"]["context_characters"] <= 12000


def test_llm_health_and_redirect_error(monkeypatch):
    from petrus_engine.llm.local import OpenAICompatibleLLMProvider

    class Connection:
        status = 200

        def __init__(self, *args, **kwargs):
            self.path = ""

        def request(self, method, path, body=None, headers=None):
            self.path = path

        def getresponse(self):
            return self

        def read(self, limit):
            if self.path == "/v1/models":
                return b'{"data":[{"id":"local-test"}]}'
            return b'{"choices":[{"message":{"content":"OK"}}]}'

        def close(self):
            pass

    monkeypatch.setattr("petrus_engine.llm.local.http.client.HTTPConnection", Connection)
    provider = OpenAICompatibleLLMProvider("local-test")
    assert provider.status()["state"] == "available"
    Connection.status = 302
    assert provider.status()["state"] == "error"
    with pytest.raises(ValueError, match="llm_http_302"):
        provider.complete([{"role": "user", "content": "no paper"}])


def test_expanded_lexical_query_fuses_without_replacing_original(env):
    engine, _ = env
    plan = plan_query("vigilância genômica")
    plan.expanded_terms = ["arbovirus"]
    retriever = HybridRetriever(engine.db)
    assert retriever.lexical_search(plan.original_query) == []
    hits = retriever.hybrid_search(plan.original_query, 5, plan)
    assert hits and {h.unit.paper_id for h in hits} == {1, 3}
    assert plan.original_query == "vigilância genômica"
