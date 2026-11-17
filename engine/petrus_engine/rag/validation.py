"""Structural output errors, never an entailment or scientific-correctness judge."""

import json
import re

REPAIRABLE = frozenset(
    {
        "invalid_json",
        "missing_required_field",
        "wrong_field_type",
        "invalid_citation_syntax",
        "missing_citation",
        "paragraph_without_citation",
    }
)
CODES = {
    "invalid_json": "llm_response_rejected",
    "missing_required_field": "ask_malformed_response",
    "wrong_field_type": "ask_malformed_response",
    "invalid_citation_syntax": "ask_invalid_citation",
    "unknown_evidence_id": "ask_invalid_citation",
    "missing_citation": "ask_missing_citations",
    "paragraph_without_citation": "ask_uncited_paragraph",
    "security_violation": "ask_security_violation",
}


class AskValidationError(ValueError):
    def __init__(self, errors):
        self.errors = errors
        self.retryable = bool(errors) and all(e["category"] in REPAIRABLE for e in errors)
        super().__init__(errors[0]["code"])


def error(category, **details):
    return {"category": category, "code": CODES[category], **details}


def citation_errors(text, allowed):
    markers = re.findall(r"\[\s*E[^\]\n]*\]", text, re.IGNORECASE)
    unknown = sorted(
        {token.upper() for marker in markers for token in re.findall(r"\bE\w+\b", marker, re.IGNORECASE)}
        - allowed
    )
    errors = [error("unknown_evidence_id", evidence_ids=unknown)] if unknown else []
    if any(not re.fullmatch(r"\[E\d+\]", marker) for marker in markers):
        errors.append(error("invalid_citation_syntax"))
    return errors


def security_errors(text):
    # Explicit output indicators only; this does not claim general injection detection.
    if re.search(
        r"<(?:think|analysis)>|<\|im_start\|>|\bI (?:will|am going to) ignore (?:the )?(?:provided|supplied) evidence\b|\bI am using my own knowledge\b",
        text,
        re.IGNORECASE,
    ):
        return [error("security_violation")]
    return []


def validate_answer(value, allowed):
    errors = []
    if not isinstance(value, dict):
        raise AskValidationError([error("wrong_field_type", field="response")])
    # Look for out-of-context IDs even when another field has a repairable defect.
    for field in ("answer", "limitations"):
        content = value.get(field)
        text = (
            content
            if isinstance(content, str)
            else " ".join(x for x in content if isinstance(x, str))
            if isinstance(content, list)
            else ""
        )
        errors += citation_errors(text, allowed) + security_errors(text)
    for field, kind in (("answer", str), ("insufficient_evidence", bool), ("limitations", list)):
        if field not in value:
            errors.append(error("missing_required_field", field=field))
        elif type(value[field]) is not kind or (
            field == "limitations" and any(not isinstance(x, str) for x in value[field])
        ):
            errors.append(error("wrong_field_type", field=field))
    if any(e["category"] in {"missing_required_field", "wrong_field_type"} for e in errors):
        raise AskValidationError(errors)
    answer, limitations = value["answer"], value["limitations"]
    ids = re.findall(r"\[(E\d+)\]", answer)
    if not value["insufficient_evidence"]:
        if not ids or not answer.strip():
            errors.append(error("missing_citation"))
        paragraphs = [p for p in re.split(r"\n\s*\n", answer.strip()) if p.strip()]
        uncited = [
            i
            for i, p in enumerate(paragraphs, 1)
            if not any(c in allowed for c in re.findall(r"\[(E\d+)\]", p))
        ]
        if uncited:
            errors.append(error("paragraph_without_citation", paragraphs=uncited))
    if errors:
        raise AskValidationError(errors)
    return answer, limitations, sorted(set(ids))


def parse_answer(raw, allowed):
    if not isinstance(raw, str):
        raise AskValidationError([error("wrong_field_type", field="response")])
    # Scan markers, not partial JSON/facts; unknown IDs prohibit a retry even in malformed JSON.
    hard = [
        e for e in citation_errors(raw, allowed) if e["category"] == "unknown_evidence_id"
    ] + security_errors(raw)
    try:
        value = json.loads(raw)
    except (ValueError, RecursionError) as exc:
        raise AskValidationError(
            hard
            + [
                error(
                    "invalid_json",
                    parse_error=exc.msg
                    if isinstance(exc, json.JSONDecodeError)
                    else "JSON parser limit exceeded",
                    position=getattr(exc, "pos", None),
                    error_type=type(exc).__name__,
                )
            ]
        ) from None
    try:
        validated = validate_answer(value, allowed)
    except AskValidationError as exc:
        raise AskValidationError(hard + exc.errors) from None
    if hard:
        raise AskValidationError(hard)
    return value, validated


def snapshot_execution(metadata):
    """Whitelist validation summaries for research events; never retain raw outputs."""
    if not isinstance(metadata, dict) or metadata.get("final_status") != "accepted":
        raise ValueError("ask_unvalidated_event")
    attempts, repaired = metadata.get("generation_attempts"), metadata.get("repair_attempted")
    if (
        type(attempts) is not int
        or attempts not in (1, 2)
        or type(repaired) is not bool
        or repaired != (attempts == 2)
    ):
        raise ValueError("ask_invalid_event")
    first = metadata.get("first_validation_errors", [])
    if (
        not isinstance(first, list)
        or bool(first) != repaired
        or metadata.get("final_validation_errors") != []
    ):
        raise ValueError("ask_invalid_event")
    errors = []
    for item in first[:64]:
        if not isinstance(item, dict) or item.get("category") not in REPAIRABLE:
            raise ValueError("ask_invalid_event")
        safe = error(item["category"])
        if item.get("field") in ("answer", "insufficient_evidence", "limitations", "response"):
            safe["field"] = item["field"]
        if type(item.get("position")) is int and 0 <= item["position"] <= 2_000_000:
            safe["position"] = item["position"]
        if item.get("error_type") in ("JSONDecodeError", "ValueError", "RecursionError"):
            safe["error_type"] = item["error_type"]
        if isinstance(item.get("paragraphs"), list):
            safe["paragraphs"] = [n for n in item["paragraphs"][:1000] if type(n) is int and 1 <= n <= 10000]
        errors.append(safe)
    reasons = list(dict.fromkeys(e["category"] for e in errors))
    if metadata.get("repair_reason") != reasons:
        raise ValueError("ask_invalid_event")
    return {
        "generation_attempts": attempts,
        "repair_attempted": repaired,
        "repair_reason": reasons,
        "first_validation_errors": errors,
        "final_validation_errors": [],
        "final_status": "accepted",
    }
