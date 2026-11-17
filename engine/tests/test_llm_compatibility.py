"""Offline regressions for bounded local-provider diagnostics and output privacy."""

import json

import pytest
from petrus_engine.llm.local import (
    ERROR_BODY_LIMIT,
    LLMProviderError,
    OpenAICompatibleLLMProvider,
    http_error,
)


class Response:
    def __init__(self, body, status=400):
        self.body = body
        self.status = status
        self.read_limits = []

    def read(self, limit):
        self.read_limits.append(limit)
        return self.body[:limit]


def test_http_error_preserves_only_useful_json_fields():
    response = Response(
        json.dumps(
            {
                "error": {
                    "message": "Unsupported response_format",
                    "type": "invalid_request",
                    "code": "bad_format",
                    "reasoning_content": "PRIVATE",
                    "request": "DO NOT COPY",
                }
            }
        ).encode()
    )
    error = http_error(response)
    assert isinstance(error, ValueError)
    assert str(error) == "llm_http_400"
    assert error.diagnostic() == {
        "code": "llm_http_400",
        "status": 400,
        "provider_message": "Unsupported response_format",
        "provider_type": "invalid_request",
        "provider_code": "bad_format",
        "truncated": False,
    }
    assert "PRIVATE" not in repr(error.diagnostic())
    assert "DO NOT COPY" not in repr(error.diagnostic())
    assert response.read_limits == [ERROR_BODY_LIMIT + 1]


@pytest.mark.parametrize(
    "body", [b'{"message":"top level","type":"bad"}', b'{"error":"top level"}', b"top level"]
)
def test_json_and_text_error_shapes(body):
    assert http_error(Response(body)).provider_message == "top level"


def test_error_body_is_bounded_even_for_truncated_json():
    body = b'{"error":{"message":"' + b"SECRET" * ERROR_BODY_LIMIT
    response = Response(body)
    error = http_error(response)
    assert error.truncated
    assert len(error.provider_message) <= 2048
    assert "SECRET" not in error.provider_message
    assert response.read_limits == [ERROR_BODY_LIMIT + 1]
    assert len(http_error(Response(b"X" * 5000)).provider_message) == 2048


def test_error_redacts_echoed_system_evidence_and_partial_sources():
    system = "Secret system prompt that should never appear in any diagnostic output."
    evidence = "Private evidence paragraph with an unusual scientific phrase and many further words."
    messages = [
        {"role": "system", "content": system},
        {"role": "user", "content": json.dumps({"evidence": [{"text": evidence}]})},
    ]
    echoed = f"Invalid parameter. {system} Source excerpt: {evidence[:54]}"
    error = http_error(Response(json.dumps({"error": {"message": echoed}}).encode()), messages)
    assert error.provider_message.startswith("Invalid parameter.")
    assert system not in error.provider_message
    assert evidence[:54] not in error.provider_message
    assert "unusual scientific" not in error.provider_message
    assert "[redacted]" in error.provider_message


def test_text_error_sanitizes_controls_and_thinking():
    value = http_error(Response(b"Invalid\x00 parameter <think>PRIVATE</think> reasoning_content: HIDDEN"))
    assert value.provider_message == "Invalid parameter [redacted] [redacted]"
    quoted = http_error(Response(b'Invalid parameter "reasoning_content":"HIDDEN"'))
    assert "HIDDEN" not in quoted.provider_message


def mock_connection(monkeypatch, response):
    requests = []

    class Connection:
        def __init__(self, *args, **kwargs):
            pass

        def request(self, method, path, body=None, headers=None):
            requests.append(json.loads(body) if body else None)

        def getresponse(self):
            return response

        def close(self):
            pass

    monkeypatch.setattr("petrus_engine.llm.local.http.client.HTTPConnection", Connection)
    return requests


def test_complete_raises_structured_error_after_reading(monkeypatch):
    response = Response(b'{"error":{"message":"Bad parameter"}}')
    mock_connection(monkeypatch, response)
    with pytest.raises(LLMProviderError) as caught:
        OpenAICompatibleLLMProvider("exact-id").complete([{"role": "user", "content": "private question"}])
    assert response.read_limits
    assert caught.value.status == 400
    assert caught.value.provider_message == "Bad parameter"


def test_complete_ignores_separate_reasoning_content(monkeypatch):
    response = Response(
        json.dumps(
            {
                "choices": [
                    {
                        "message": {
                            "content": '{"answer":"Final [E1]","insufficient_evidence":false,"limitations":[]}',
                            "reasoning_content": "PRIVATE INTERNAL REASONING",
                        }
                    }
                ]
            }
        ).encode(),
        200,
    )
    mock_connection(monkeypatch, response)
    final = OpenAICompatibleLLMProvider("exact-id").answer("question", [])
    assert "PRIVATE" not in final
    assert json.loads(final)["answer"] == "Final [E1]"


def test_ask_serializes_exact_response_schema_and_keeps_citation_validation(monkeypatch):
    from petrus_engine.llm.local import ASK_RESPONSE_SCHEMA
    from petrus_engine.rag.ask import validate_answer

    payload = {"answer": "Supported [E1]", "insufficient_evidence": False, "limitations": []}
    response = Response(
        json.dumps({"choices": [{"message": {"content": json.dumps(payload)}}]}).encode(), 200
    )
    requests = mock_connection(monkeypatch, response)
    final = OpenAICompatibleLLMProvider("exact-id").answer(
        "question", [{"evidence_id": "E1", "text": "source"}]
    )
    request = requests[0]
    assert request["response_format"] == {
        "type": "json_schema",
        "json_schema": {"name": "petrus_ask_response", "strict": True, "schema": ASK_RESPONSE_SCHEMA},
    }
    assert set(ASK_RESPONSE_SCHEMA["properties"]) == {"answer", "insufficient_evidence", "limitations"}
    assert set(ASK_RESPONSE_SCHEMA["required"]) == set(ASK_RESPONSE_SCHEMA["properties"])
    assert ASK_RESPONSE_SCHEMA["additionalProperties"] is False
    assert request["max_tokens"] == 1600
    assert request["temperature"] == 0.1
    assert validate_answer(json.loads(final), {"E1"})[2] == ["E1"]
    with pytest.raises(ValueError, match="ask_invalid_citation"):
        validate_answer(json.loads(final), {"E2"})
    with pytest.raises(ValueError, match="ask_uncited_paragraph"):
        validate_answer({**payload, "answer": "Supported [E1]\n\nUnsupported paragraph"}, {"E1"})


def test_expansion_has_its_own_existing_contract(monkeypatch):
    response = Response(b'{"choices":[{"message":{"content":"{\\"queries\\":[\\"english query\\"]}"}}]}', 200)
    requests = mock_connection(monkeypatch, response)
    assert OpenAICompatibleLLMProvider("exact-id").expand_query("consulta") == ["english query"]
    schema = requests[0]["response_format"]["json_schema"]
    assert schema["name"] == "petrus_query_expansion"
    assert schema["schema"]["required"] == ["queries"]
    assert "answer" not in schema["schema"]["properties"]


def test_reasoning_only_success_is_not_used_as_an_answer(monkeypatch):
    response = Response(
        json.dumps(
            {
                "choices": [
                    {
                        "message": {
                            "content": "",
                            "reasoning_content": json.dumps(
                                {
                                    "answer": "PRIVATE [E1]",
                                    "insufficient_evidence": False,
                                    "limitations": [],
                                }
                            ),
                        }
                    }
                ]
            }
        ).encode(),
        200,
    )
    mock_connection(monkeypatch, response)
    with pytest.raises(ValueError, match="llm_empty_response"):
        OpenAICompatibleLLMProvider("exact-id").answer("question", [])


def test_valid_reasoning_json_cannot_replace_invalid_final_content(monkeypatch):
    response = Response(
        json.dumps(
            {
                "choices": [
                    {
                        "message": {
                            "content": "not JSON",
                            "reasoning_content": '{"answer":"PRIVATE [E1]","insufficient_evidence":false,"limitations":[]}',
                        }
                    }
                ]
            }
        ).encode(),
        200,
    )
    mock_connection(monkeypatch, response)
    final = OpenAICompatibleLLMProvider("exact-id").answer("question", [])
    assert final == "not JSON"
    with pytest.raises(json.JSONDecodeError):
        json.loads(final)
