"""Offline embeddings, provenance and RRF fixtures. No model download or server."""

import json

import numpy as np
import pytest
from petrus_engine.rag.evidence import EvidenceRepository, ProvenanceLevel
from petrus_engine.rag.index import EmbeddingIndexService, SQLiteVectorIndex, content_hash
from petrus_engine.rag.providers import OpenAICompatibleEmbeddingProvider, local_endpoint
from petrus_engine.rag.retrieval import HybridRetriever
from petrus_engine.service import Engine


class FakeEmbeddingProvider:
    provider_id = "fake"
    model_id = "synthetic-3d"
    dimension = 3
    max_chars = 6000

    def __init__(self):
        self.calls = []

    def vector(self, text):
        if text == "arbovirus" or ("mosquito" in text and "arbovirus" not in text):
            return [1.0, 0.0, 0.0]
        if "mosquito" in text:
            return [0.7, 0.7, 0.0]
        if "arbovirus" in text:
            return [0.0, 1.0, 0.0]
        return [0.0, 0.0, 1.0]

    def embed_documents(self, texts):
        self.calls.extend(texts)
        return [self.vector(t) for t in texts]

    def embed_query(self, text):
        return self.vector(text)


@pytest.fixture
def env(tmp_path):
    engine = Engine(tmp_path / "data", start_worker=False)
    with engine.db.connect() as db:
        db.execute("INSERT INTO libraries(id,name,root_path) VALUES(1,'synthetic','/synthetic')")
        for i, text in enumerate(
            ["arbovirus antigen", "mosquito ecology", "arbovirus mosquito", "stellar astronomy"], 1
        ):
            db.execute(
                "INSERT INTO papers(id,file_hash,file_name,title,index_status) VALUES(?,?,?,?,?)",
                (i, str(i), str(i), f"Synthetic {i}", "indexed"),
            )
            db.execute(
                "INSERT INTO paper_files(paper_id,library_id,file_path,file_name) VALUES(?,1,?,?)",
                (i, str(i), str(i)),
            )
            db.execute("INSERT INTO chunks(id,paper_id,page,text) VALUES(?,?,?,?)", (i, i, i, text))
            db.execute(
                "INSERT INTO paper_search(rowid,title,body) VALUES(?,?,?)", (i, f"Synthetic {i}", text)
            )
        db.execute(
            "INSERT INTO sections(id,paper_id,section_type,heading,text,page_start,page_end) VALUES(2,2,'methods','Original','mosquito ecology',2,2)"
        )
        db.execute(
            "INSERT INTO source_spans(id,paper_id,section_id,page,text,source_type) VALUES(2,2,2,2,'mosquito ecology','grobid_coordinates')"
        )
        db.execute(
            "INSERT INTO sections(id,paper_id,section_type,heading,text) VALUES(3,3,'results','Original','arbovirus mosquito')"
        )
        db.execute(
            "INSERT INTO sections(id,paper_id,text,page_start,page_end) VALUES(4,4,'stellar astronomy',4,4)"
        )
        db.execute(
            "INSERT INTO source_spans(id,paper_id,section_id,page,text,source_type) VALUES(4,4,4,4,'stellar astronomy','page_text_alignment')"
        )
    yield engine, FakeEmbeddingProvider()
    engine.close()


def test_float32_roundtrip_cosine_and_semantic_top(env):
    engine, provider = env
    service = EmbeddingIndexService(engine.db, provider)
    service.index_paper(2)
    service.index_paper(3)
    with engine.db.connect() as db:
        row = db.execute("SELECT * FROM embedding_index WHERE paper_id=3").fetchone()
        assert len(row["vector_blob"]) == row["dimension"] * 4
        np.testing.assert_allclose(np.frombuffer(row["vector_blob"], dtype="<f4"), [0.7, 0.7, 0], rtol=1e-6)
    hits = HybridRetriever(engine.db, provider).semantic_search("arbovirus")
    assert hits[0].unit.paper_id == 2 and hits[0].score == pytest.approx(1)
    assert hits[1].score == pytest.approx(2**-0.5)
    assert hits[0].unit.supports_paginated_evidence
    assert hits[1].unit.page_start is None and not hits[1].unit.supports_paginated_evidence


def test_dimension_zero_nan_and_model_isolation(env):
    engine, provider = env
    unit = next(EvidenceRepository(engine.db).iter_units(1))
    index = SQLiteVectorIndex(engine.db, provider)
    for bad in ([1, 2], [0, 0, 0], [float("nan"), 0, 1]):
        with pytest.raises(ValueError):
            index.upsert(unit, bad, content_hash(unit))
    first = EmbeddingIndexService(engine.db, provider)
    first.index_paper(1)
    other = FakeEmbeddingProvider()
    other.model_id = "different-model"
    EmbeddingIndexService(engine.db, other).index_paper(1)
    third = FakeEmbeddingProvider()
    third.provider_id = "different-provider"
    EmbeddingIndexService(engine.db, third).index_paper(1)
    with engine.db.connect() as db:
        assert db.execute("SELECT count(*) FROM embedding_index").fetchone()[0] == 3


def test_cache_change_and_stale_deletion(env):
    engine, provider = env
    service = EmbeddingIndexService(engine.db, provider)
    assert service.index_paper(1)["indexed"] == 1
    assert service.index_paper(1)["cached"] == 1 and len(provider.calls) == 1
    with engine.db.connect() as db:
        db.execute("UPDATE chunks SET text='changed arbovirus source' WHERE paper_id=1")
    assert service.status()["current"] == 0
    assert service.index.search([1, 0, 0]) == []
    assert service.index_paper(1)["indexed"] == 1 and len(provider.calls) == 2
    with engine.db.connect() as db:
        db.execute("DELETE FROM chunks WHERE paper_id=1")
    assert service.remove_stale() == 1


def test_source_identity_reuse_invalidates_and_rebuild_is_scoped(env):
    engine, provider = env
    service = EmbeddingIndexService(engine.db, provider)
    service.index_paper(2)
    with engine.db.connect() as db:
        db.execute("UPDATE source_spans SET page=9 WHERE id=2")
    assert service.status()["current"] == 0
    assert service.index.search([1, 0, 0]) == []
    assert service.remove_stale() == 1
    service.index_paper(2)
    assert service.clear() == 1
    assert service.status()["stored"] == 0
    assert next(EvidenceRepository(engine.db).iter_units(2)).page_start == 9


def test_all_provenance_levels_and_explicit_oversize_subdivision(env):
    engine, provider = env
    service = EmbeddingIndexService(engine.db, provider)
    assert len(service.index_all_available()) == 4
    hits = HybridRetriever(engine.db, provider).semantic_search("arbovirus")
    assert {h.unit.provenance_level for h in hits} == set(ProvenanceLevel)
    limited = EmbeddingIndexService(engine.db, provider, max_chars=3)
    result = limited.index_paper(1)
    assert result["warnings"] == []
    assert result["indexed"] == 6
    with engine.db.connect() as db:
        assert db.execute("SELECT count(*) FROM embedding_index WHERE paper_id=1").fetchone()[0] == 6


def test_rrf_includes_lexical_only_semantic_only_and_both(env):
    engine, provider = env
    service = EmbeddingIndexService(engine.db, provider)
    service.index_paper(2)
    service.index_paper(3)
    retriever = HybridRetriever(engine.db, provider)
    lexical = retriever.lexical_search("arbovirus")
    assert [h.unit.paper_id for h in lexical] == [1, 3]
    semantic = retriever.semantic_search("arbovirus")
    assert [h.unit.paper_id for h in semantic] == [2, 3]
    hybrid = retriever.hybrid_search("arbovirus")
    assert [h.unit.paper_id for h in hybrid] == [3, 1, 2]
    assert hybrid[0].lexical_rank == hybrid[0].semantic_rank == 2
    assert hybrid[0].score == pytest.approx(2 / 62)
    assert hybrid[1].semantic_rank is None and hybrid[2].lexical_rank is None
    print(
        "Synthetic example:",
        {
            "query": "arbovirus",
            "lexical": [h.unit.paper_id for h in lexical],
            "semantic": [h.unit.paper_id for h in semantic],
            "hybrid": [h.unit.paper_id for h in hybrid],
        },
    )


def test_engine_api_settings_and_lexical_fallback(env, monkeypatch):
    engine, provider = env
    assert engine.call("embedding_status", {})["enabled"] is False
    assert engine.call("hybrid_search", {"query": "arbovirus"})["hits"]
    monkeypatch.setattr("petrus_engine.rag.providers.configured_provider", lambda _: provider)
    assert engine.call("embedding_index", {"paper_id": 2})["indexed"] == 1
    hit = engine.call("semantic_search", {"query": "arbovirus", "top_k": 2})["hits"][0]
    assert hit["paper_id"] == 2 and hit["supports_paginated_evidence"]
    assert hit["unit"]["page_start"] == 2 and hit["text_excerpt"] == "mosquito ecology"
    with pytest.raises(ValueError):
        engine.call("semantic_search", {"query": "arbovirus", "top_k": -1})
    with pytest.raises(ValueError):
        engine.call("save_settings", {"embedding_endpoint": "http://example.com/v1"})
    engine.call(
        "save_settings",
        {
            "embedding_provider": "lmstudio",
            "embedding_endpoint": "http://127.0.0.1:1234/v1",
            "embedding_model": "test",
        },
    )
    assert engine.get_settings()["embedding_model"] == "test"


@pytest.mark.parametrize(
    "endpoint",
    [
        "https://127.0.0.1/v1",
        "http://example.com/v1",
        "http://127.0.0.1.evil/v1",
        "http://user@127.0.0.1/v1",
        "http://127.0.0.1/v1?x=1",
        "http://127.0.0.1/other",
    ],
)
def test_remote_or_ambiguous_endpoints_rejected(endpoint):
    with pytest.raises(ValueError):
        local_endpoint(endpoint)


def test_http_adapter_order_validation_and_no_redirect(monkeypatch):
    requests = []

    class Response:
        status = 200

        def read(self, limit):
            return json.dumps(
                {
                    "model": "test",
                    "data": [{"index": 1, "embedding": [0, 1]}, {"index": 0, "embedding": [1, 0]}],
                }
            ).encode()

    response = Response()

    class Connection:
        def __init__(self, host, port, timeout):
            assert host == "127.0.0.1"

        def request(self, method, path, body, headers):
            requests.append((method, path, json.loads(body)))

        def getresponse(self):
            return response

        def close(self):
            pass

    monkeypatch.setattr("petrus_engine.rag.providers.http.client.HTTPConnection", Connection)
    provider = OpenAICompatibleEmbeddingProvider("test", endpoint="http://localhost:1234/v1")
    assert provider.embed_documents(["one", "two"]) == [[1, 0], [0, 1]]
    assert provider.dimension == 2 and requests[0][1] == "/v1/embeddings"
    response.status = 302
    with pytest.raises(ValueError, match="embedding_provider_response"):
        provider.embed_query("one")
