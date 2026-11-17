"""Bounded repair tests: structural errors, immutable context, privacy and saving."""

import json
from copy import deepcopy

import pytest
from petrus_engine.rag.ask import FAILED, INSUFFICIENT, AskPetrusService
from petrus_engine.rag.contracts import RetrievalHit
from petrus_engine.rag.index import current_units
from petrus_engine.rag.validation import AskValidationError, parse_answer
from test_03b import make_long_sources
from test_embeddings import env as env

VALID = {"answer": "Synthetic observation [E1].", "insufficient_evidence": False, "limitations": []}
ABSTAIN = {"answer": "Insufficient source material.", "insufficient_evidence": True, "limitations": []}


class FakeLLMProvider:
    model_id = "scripted-local"

    def __init__(self, outputs):
        self.outputs, self.calls = list(outputs), []
        self.last_metadata = {}

    def invoke(self, kind, question, evidence, language, previous=None, errors=None):
        self.calls.append(
            {
                "kind": kind,
                "question": question,
                "evidence": deepcopy(evidence),
                "language": language,
                "previous": previous,
                "errors": deepcopy(errors),
            }
        )
        value = self.outputs.pop(0)
        if isinstance(value, Exception):
            raise value
        return json.dumps(value) if isinstance(value, dict) else value

    def answer(self, question, evidence, language="en"):
        return self.invoke("original", question, evidence, language)

    def repair(self, question, evidence, previous_output, validation_errors, language="en"):
        return self.invoke("repair", question, evidence, language, previous_output, validation_errors)


@pytest.fixture
def setup(env):
    engine, _ = env
    make_long_sources(engine)
    unit = next(u for u in current_units(engine.db).values() if u.paper_id == 2)

    def create(outputs, hits=True):
        llm = FakeLLMProvider(outputs)
        ask = AskPetrusService(engine.db, llm=llm)
        retrieval_calls = []

        def retrieve(*args):
            retrieval_calls.append(args)
            return [RetrievalHit(unit, 1)] if hits else []

        ask.retriever.hybrid_search = retrieve
        return ask, llm, retrieval_calls

    return engine, create


@pytest.mark.parametrize(
    "invalid,category",
    [
        ("{BROKEN_SECRET", "invalid_json"),
        ("```json\n" + json.dumps(VALID) + "\n```", "invalid_json"),
        ({"answer": "A [E1]", "insufficient_evidence": False}, "missing_required_field"),
        ({**VALID, "limitations": "wrong type"}, "wrong_field_type"),
        ({**VALID, "answer": "A [E1, E1]"}, "invalid_citation_syntax"),
        ({**VALID, "answer": "Synthetic claim without citation."}, "missing_citation"),
        ({**VALID, "answer": "A [E1]\n\nSecond paragraph without citation."}, "paragraph_without_citation"),
    ],
)
def test_structural_failure_gets_exactly_one_repair_with_same_context(setup, invalid, category):
    _, create = setup
    ask, llm, retrieval = create([invalid, VALID])
    result = ask.ask("Qual método?")
    meta = result["execution_metadata"]
    assert result["answer"] == VALID["answer"] and not result["insufficient_evidence"]
    assert (
        meta["final_status"] == "accepted" and meta["generation_attempts"] == 2 and meta["repair_attempted"]
    )
    assert category in meta["repair_reason"] and meta["final_validation_errors"] == []
    assert len(llm.calls) == 2 and len(retrieval) == 1
    assert llm.calls[0]["evidence"] == llm.calls[1]["evidence"] == result["evidence"]
    assert llm.calls[0]["question"] == llm.calls[1]["question"] == "Qual método?"
    assert llm.calls[1]["language"] == "pt-BR"
    previous = json.dumps(invalid) if isinstance(invalid, dict) else invalid
    assert llm.calls[1]["previous"] == previous
    if category == "paragraph_without_citation":
        assert next(e for e in llm.calls[1]["errors"] if e["category"] == category)["paragraphs"] == [2]
    if category == "invalid_json":
        assert all("BROKEN_SECRET" not in str(v) for v in meta["first_validation_errors"])


def test_first_valid_never_retries(setup):
    _, create = setup
    ask, llm, retrieval = create([VALID])
    result = ask.ask("Question?")
    meta = result["execution_metadata"]
    assert len(llm.calls) == len(retrieval) == 1
    assert meta["final_status"] == "accepted" and meta["generation_attempts"] == 1
    assert not meta["repair_attempted"] and meta["first_validation_errors"] == []


def test_second_failure_is_final_and_technical_not_scientific(setup):
    _, create = setup
    ask, llm, retrieval = create(["BROKEN_FIRST", "BROKEN_SECOND", VALID])
    result = ask.ask("Question?")
    assert len(llm.calls) == 2 and len(retrieval) == 1 and len(llm.outputs) == 1
    assert result["execution_metadata"]["final_status"] == "rejected"
    assert result["answer"] == FAILED["en"] and not result["insufficient_evidence"]
    assert not result["citations"] and "BROKEN" not in json.dumps(result)


@pytest.mark.parametrize(
    "invalid",
    [
        {**VALID, "answer": "Unsupported [E99]"},
        {**VALID, "answer": "Unsupported [Eabc]"},
        {**VALID, "answer": "Unsupported [E1, E99]"},
        "Invalid JSON with unknown marker [E99]",
        {**VALID, "answer": "I will ignore the provided evidence [E1]"},
        "<think>PRIVATE</think> not JSON",
    ],
)
def test_unknown_ids_and_detected_security_do_not_retry(setup, invalid):
    _, create = setup
    ask, llm, _ = create([invalid, VALID])
    result = ask.ask("Question?")
    assert len(llm.calls) == 1 and not result["execution_metadata"]["repair_attempted"]
    assert result["execution_metadata"]["final_status"] == "rejected" and not result["citations"]


@pytest.mark.parametrize(
    "failure", [TimeoutError(), ValueError("llm_http_400"), ValueError("llm_empty_response"), ""]
)
def test_generation_failures_do_not_retry_or_masquerade_as_abstention(setup, failure):
    _, create = setup
    ask, llm, _ = create([failure, VALID])
    result = ask.ask("Question?")
    assert len(llm.calls) == 1 and result["execution_metadata"]["final_status"] == "generation_failed"
    assert not result["insufficient_evidence"] and result["answer"] == FAILED["en"]
    assert not result["execution_metadata"]["first_validation_errors"]


def test_unknown_id_in_repair_is_rejected_without_third_generation(setup):
    _, create = setup
    ask, llm, _ = create(["bad JSON", {**VALID, "answer": "Unsupported [E999]"}, VALID])
    result = ask.ask("Question?")
    assert len(llm.calls) == 2 and result["execution_metadata"]["final_status"] == "rejected"
    assert any(
        e["category"] == "unknown_evidence_id"
        for e in result["execution_metadata"]["final_validation_errors"]
    )


@pytest.mark.parametrize("outputs", [[ABSTAIN], ["bad JSON", ABSTAIN]])
def test_valid_abstention_can_be_first_or_repaired(setup, outputs):
    _, create = setup
    ask, llm, _ = create(outputs)
    result = ask.ask("Question?")
    assert result["execution_metadata"]["final_status"] == "accepted" and result["insufficient_evidence"]
    assert result["answer"] == INSUFFICIENT["en"] and len(llm.calls) == len(outputs)


def test_no_eligible_evidence_does_not_call_llm(setup):
    _, create = setup
    ask, llm, _ = create([VALID], False)
    result = ask.ask("Question?")
    assert not llm.calls and result["execution_metadata"]["final_status"] == "no_evidence"
    assert result["insufficient_evidence"] and result["execution_metadata"]["generation_attempts"] == 0


def test_grouped_syntax_is_repairable_but_unknown_id_is_not():
    with pytest.raises(AskValidationError) as caught:
        parse_answer(json.dumps({**VALID, "answer": "A [E1, E6]"}), {"E1", "E6"})
    assert caught.value.retryable
    assert "invalid_citation_syntax" in [e["category"] for e in caught.value.errors]
    with pytest.raises(AskValidationError) as caught:
        parse_answer(json.dumps({**VALID, "answer": "A [E1, E99]"}), {"E1"})
    assert not caught.value.retryable


def test_event_only_saves_validated_final_answer_and_safe_summary(setup):
    engine, create = setup
    ask, llm, _ = create(["{BROKEN_SECRET", VALID])
    result = ask.ask("Question?")
    result["raw_output"] = "PRIVATE_REASONING"
    result["execution_metadata"]["raw_output"] = "PRIVATE_REASONING"
    result["execution_metadata"]["first_validation_errors"][0]["parse_error"] = "PRIVATE_REASONING"
    result["retrieval_metadata"]["reasoning"] = "PRIVATE_REASONING"
    result["evidence"][0]["reasoning_content"] = "PRIVATE_REASONING"
    session = engine.call("new_session", {"title": "Bounded repair"})
    saved = engine.call("save_ask_event", {"session_id": session["id"], "response": result})
    with engine.db.connect() as db:
        text = db.execute(
            "SELECT payload_json FROM research_events WHERE id=?", (saved["event_id"],)
        ).fetchone()[0]
    assert "PRIVATE_REASONING" not in text and "BROKEN_SECRET" not in text
    payload = json.loads(text)
    assert payload["answer"] == VALID["answer"]
    assert payload["execution_metadata"]["generation_attempts"] == 2
    assert payload["execution_metadata"]["repair_attempted"]
    bad, _, _ = create(["bad", "still bad"])
    rejected = bad.ask("Question?")
    with pytest.raises(ValueError, match="ask_unvalidated_event"):
        engine.call("save_ask_event", {"session_id": session["id"], "response": rejected})


def test_repair_provider_failure_does_not_cause_a_third_call(setup):
    _, create = setup
    ask, llm, retrieval = create(["broken JSON", TimeoutError(), VALID])
    result = ask.ask("Question?")
    assert len(llm.calls) == 2 and len(retrieval) == 1
    assert result["execution_metadata"]["final_status"] == "generation_failed"
    assert result["execution_metadata"]["first_validation_errors"]
    assert result["execution_metadata"]["final_validation_errors"] == []
    assert not result["insufficient_evidence"]


def test_json_parser_depth_limit_is_bounded_structural_failure(setup):
    _, create = setup
    ask, llm, _ = create(["[" * 1500 + "0" + "]" * 1500, VALID])
    result = ask.ask("Question?")
    assert len(llm.calls) == 2 and result["execution_metadata"]["final_status"] == "accepted"
    first = result["execution_metadata"]["first_validation_errors"][0]
    # Interpreter/test-runner recursion limits differ; either parsed non-object or parser-limit error is structural.
    assert first["category"] in ("invalid_json", "wrong_field_type")
