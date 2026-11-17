"""Read-only discovery contract; fake transport, no model loading or generation."""

import json

import pytest
from petrus_engine.llm.catalog import model_catalog, reasoning_capability
from petrus_engine.llm.local import LLMProviderError
from petrus_engine.llm.native import LMStudioNativeLLMProvider
from petrus_engine.service import Engine


@pytest.fixture
def catalog_http(monkeypatch):
    state = {"payload": {"models": []}, "status": 200, "requests": [], "closed": 0}

    class Response:
        @property
        def status(self):
            return state["status"]

        def read(self, limit):
            payload = state["payload"]
            return (payload if isinstance(payload, bytes) else json.dumps(payload).encode())[:limit]

    class Connection:
        def __init__(self, host, port, timeout):
            state["address"] = (host, port, timeout)

        def request(self, method, path, body=None, headers=None):
            state["requests"].append((method, path, body))
            if state.get("offline"):
                raise OSError("synthetic offline")

        def getresponse(self):
            return Response()

        def close(self):
            state["closed"] += 1

    monkeypatch.setattr("petrus_engine.llm.catalog.http.client.HTTPConnection", Connection)
    return state


def test_normal_catalog_metadata_classification_and_unicode(catalog_http):
    catalog_http["payload"] = {"models": [
        {"key": "模型/ação:9b", "type": "llm", "display_name": "Modelo ç", "architecture": "qwen",
         "format": "mlx", "params_string": "9B", "quantization": {"name": "4-bit", "secret": "PRIVATE"},
         "size_bytes": 123, "loaded_instances": [{"id": "PRIVATE"}], "path": "PRIVATE",
         "capabilities": {"reasoning": {"allowed_options": ["on", "off"]}}},
        {"key": "nomic", "type": "embedding", "loaded_instances": []},
        {"key": "qwen-embedding-in-name-only"},
        {"key": "future", "type": "future-runtime-type"},
    ]}
    models = model_catalog("http://127.0.0.1:1234/v1")["models"]
    assert [m["category"] for m in models] == ["llm", "embedding", "unknown", "unknown"]
    assert models[0] == {
        "id": "模型/ação:9b", "display_name": "Modelo ç", "type": "llm", "category": "llm",
        "architecture": "qwen", "format": "mlx", "parameters": "9B", "quantization": "4-bit",
        "size_bytes": 123, "loaded": True, "reasoning": {"configurable": True, "can_disable": True},
    }
    assert models[1]["loaded"] is False
    assert models[2]["loaded"] is None
    assert models[2]["reasoning"] == {"configurable": None, "can_disable": None}
    assert "PRIVATE" not in json.dumps(models)
    assert catalog_http["requests"] == [("GET", "/api/v1/models", None)]
    assert catalog_http["address"] == ("127.0.0.1", 1234, 3)
    assert catalog_http["closed"] == 1


def test_empty_catalog(catalog_http):
    assert model_catalog("http://localhost:1234") == {"models": []}


def test_invalid_optional_fields_duplicate_and_invalid_ids(catalog_http):
    catalog_http["payload"] = {"models": [None, 2, {}, {"key": ""}, {"key": " "}, {"key": 5},
        {"key": " custom exact ", "display_name": 1, "size_bytes": True, "loaded_instances": "bad",
         "quantization": {}, "capabilities": []}, {"key": " custom exact "}]}
    models = model_catalog("http://[::1]:1234")["models"]
    assert len(models) == 1 and models[0]["id"] == " custom exact "
    for key in ("display_name", "size_bytes", "loaded", "quantization", "architecture", "parameters", "format"):
        assert models[0][key] is None
    assert models[0]["reasoning"] == {"configurable": None, "can_disable": None}


@pytest.mark.parametrize("endpoint", ["http://example.com:1234", "https://127.0.0.1:1234",
    "http://127.0.0.1:1234/other", "http://user@localhost:1234", "http://localhost:1234?q=x",
    "http://localhost:1234#fragment", "http://192.168.1.1:1234", None])
def test_loopback_only_before_transport(catalog_http, endpoint):
    with pytest.raises(ValueError, match="llm_local_endpoint_required"):
        model_catalog(endpoint)
    assert not catalog_http["requests"]


def test_offline_closes_without_writes(catalog_http):
    catalog_http["offline"] = True
    with pytest.raises(OSError):
        model_catalog("http://127.0.0.1:1234")
    assert catalog_http["closed"] == 1
    assert catalog_http["requests"] == [("GET", "/api/v1/models", None)]


@pytest.mark.parametrize("status", [302, 401, 500])
def test_http_errors_sanitized_and_redirect_not_followed(catalog_http, status):
    catalog_http.update(status=status, payload={"error": {
        "message": "Failure <think>PRIVATE</think>\u0001", "type": "runtime", "code": "unavailable",
        "request": "PRIVATE-EXTRA"}, "models": [{"key": "PRIVATE"}]})
    with pytest.raises(LLMProviderError) as caught:
        model_catalog("http://127.0.0.1:1234")
    assert str(caught.value) == f"llm_http_{status}"
    assert "PRIVATE" not in repr(caught.value.diagnostic())
    assert len(catalog_http["requests"]) == 1 and catalog_http["closed"] == 1


@pytest.mark.parametrize("payload", [b"bad json", {}, {"models": {}}, [], b'\xff'])
def test_invalid_payload(catalog_http, payload):
    catalog_http["payload"] = payload
    with pytest.raises((ValueError, UnicodeDecodeError)):
        model_catalog("http://127.0.0.1:1234")
    assert catalog_http["closed"] == 1


def test_response_bound(catalog_http):
    catalog_http["payload"] = b" " * 1_000_001
    with pytest.raises(ValueError, match="llm_response_too_large"):
        model_catalog("http://127.0.0.1:1234")


@pytest.mark.parametrize("capabilities,expected", [({}, None),
    ({"reasoning": {"allowed_options": ["off", "on"]}}, True),
    ({"reasoning": {"allowed_options": ["on"]}}, False),
    ({"reasoning": True}, False)])
def test_shared_reasoning_policy(catalog_http, capabilities, expected):
    model = {"key": "chosen", "type": "llm", "capabilities": capabilities}
    catalog_http["payload"] = {"models": [model]}
    normalized = model_catalog("http://127.0.0.1:1234")["models"][0]
    provider = LMStudioNativeLLMProvider("chosen")
    assert reasoning_capability(provider._get_model()) == reasoning_capability(model)
    assert normalized["reasoning"]["can_disable"] is expected
    assert all(r == ("GET", "/api/v1/models", None) for r in catalog_http["requests"])


def test_engine_discovery_refresh_no_settings_or_database_mutation(tmp_path, catalog_http):
    engine = Engine(tmp_path / "data", start_worker=False)
    try:
        engine.call("save_settings", {"llm_model": "saved/missing", "embedding_model": "saved/nomic"})
        with engine.db.connect() as db:
            before = list(db.iterdump())
        for identifier in ["first", "second"]:
            catalog_http["payload"] = {"models": [{"key": identifier, "type": "llm"}]}
            assert engine.call("llm_models", {"endpoint": "http://127.0.0.1:1234"})["models"][0]["id"] == identifier
        with engine.db.connect() as db:
            assert list(db.iterdump()) == before
        assert engine.get_settings()["llm_model"] == "saved/missing"
        assert engine.get_settings()["embedding_model"] == "saved/nomic"
        assert catalog_http["requests"] == [("GET", "/api/v1/models", None)] * 2
    finally:
        engine.close()
