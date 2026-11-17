"""Bounded evidence selection and strict citation membership, not a claim-entailment oracle."""

import json
import re
import time
from dataclasses import asdict

from petrus_engine.rag.query import plan_query
from petrus_engine.rag.retrieval import HybridRetriever, diversify
from petrus_engine.rag.validation import AskValidationError, parse_answer
from petrus_engine.rag.validation import validate_answer as validate_answer

FAILED = {
    "en": "PETRUS could not produce a valid grounded response.",
    "pt-BR": "O PETRUS não conseguiu produzir uma resposta fundamentada válida.",
}

INSUFFICIENT = {
    "en": "I could not find sufficient evidence in the indexed library to answer this confidently.",
    "pt-BR": "Não encontrei evidência suficiente na biblioteca indexada para responder com confiança.",
}


def select_evidence(hits, max_units=8, max_chars=12000):
    priority = {"coordinate": 0, "exact_page_alignment": 0, "section_only": 1, "basic_page_text": 2}
    candidates = sorted(enumerate(hits), key=lambda item: (priority[item[1].unit.provenance_level], item[0]))
    selected = []
    shingles = []
    total = 0
    candidates = diversify([hit for _, hit in candidates], len(candidates))
    for hit in candidates:
        unit = hit.unit
        if unit.evidence_role in ("bibliography", "metadata") or len(unit.text.strip()) < 80:
            continue
        if total + len(unit.text) > max_chars:
            continue
        words = re.findall(r"\w+", unit.text.casefold())
        signature = {tuple(words[i : i + 4]) for i in range(max(1, len(words) - 3))}
        if any(len(signature & prior) / max(1, len(signature | prior)) >= 0.92 for prior in shingles):
            continue
        shingles.append(signature)
        selected.append(hit)
        total += len(unit.text)
        if len(selected) == max_units:
            break
    return selected


class AskPetrusService:
    def __init__(self, database, embedding_provider=None, llm=None, expand=False):
        self.database = database
        self.llm = llm
        self.expand = expand
        self.retriever = HybridRetriever(database, embedding_provider)

    def ask(self, question):
        if not isinstance(question, str) or not question.strip() or len(question) > 2000:
            raise ValueError("ask_invalid_question")
        started = time.perf_counter()
        plan = plan_query(question)
        if self.expand and self.llm and plan.detected_language == "pt-BR":
            try:
                plan.expanded_terms = self.llm.expand_query(question)
            except Exception:
                plan.warnings.append("query_expansion_unavailable")
        warnings = list(plan.warnings)
        retrieval_started = time.perf_counter()
        try:
            hits = self.retriever.hybrid_search(question, 30, plan)
        except Exception:
            warnings.append("semantic_unavailable_lexical_fallback")
            hits = HybridRetriever(self.database).hybrid_search(question, 30, plan)
        retrieval_seconds = time.perf_counter() - retrieval_started
        selected = select_evidence(hits)
        evidence = []
        for i, hit in enumerate(selected, 1):
            unit = hit.unit
            evidence.append(
                {
                    "evidence_id": f"E{i}",
                    "unit_id": unit.unit_id,
                    "paper_id": unit.paper_id,
                    "paper_title": unit.title,
                    "section": unit.heading or unit.section_type,
                    "page_start": unit.page_start,
                    "page_end": unit.page_end,
                    "text": unit.text,
                    "provenance": unit.provenance_level,
                    "evidence_role": unit.evidence_role,
                    "supports_paginated_evidence": unit.supports_paginated_evidence,
                }
            )
        while evidence and len(json.dumps(evidence, ensure_ascii=False)) > 12000:
            evidence.pop()
        result = {
            "question": question,
            "answer": FAILED[plan.detected_language],
            "evidence": evidence,
            "papers": [
                {"paper_id": pid, "title": next(e["paper_title"] for e in evidence if e["paper_id"] == pid)}
                for pid in sorted({e["paper_id"] for e in evidence})
            ],
            "limitations": warnings,
            "insufficient_evidence": False,
            "citations": [],
            "execution_metadata": {
                "generation_attempts": 0,
                "repair_attempted": False,
                "repair_reason": [],
                "first_validation_errors": [],
                "final_validation_errors": [],
                "final_status": "not_configured",
                "retrieval_seconds": retrieval_seconds,
                "first_generation_seconds": 0.0,
                "repair_generation_seconds": 0.0,
                "attempts": [],
            },
            "retrieval_metadata": {
                "query_plan": asdict(plan),
                "retrieved": len(hits),
                "selected": len(evidence),
                "context_characters": len(json.dumps(evidence, ensure_ascii=False)),
                "include_bibliography": False,
                "max_hits_per_paper": 2,
                "model_id": getattr(self.llm, "model_id", None),
            },
        }
        execution = result["execution_metadata"]

        def finish(status):
            execution["final_status"] = status
            execution["total_seconds"] = time.perf_counter() - started
            return result

        if not evidence:
            result.update(answer=INSUFFICIENT[plan.detected_language], insufficient_evidence=True)
            result["limitations"].append("no_eligible_evidence")
            return finish("no_evidence")
        if self.llm is None:
            result["limitations"].append("llm_not_configured")
            result["answer"] = (
                "Selecione um modelo LLM local em Configurações → IA para gerar uma resposta com as evidências recuperadas."
                if plan.detected_language == "pt-BR"
                else "Select a local LLM in Settings → AI to generate an answer from the retrieved evidence."
            )
            return finish("not_configured")
        context = json.dumps(evidence, ensure_ascii=False)
        allowed = {e["evidence_id"] for e in evidence}
        previous, errors = None, []
        for attempt in range(2):
            generation_started = time.perf_counter()
            execution["final_validation_errors"] = []
            execution["generation_attempts"] += 1
            attempt_info = {"kind": "repair" if attempt else "original"}
            execution["attempts"].append(attempt_info)
            try:
                if attempt:
                    raw = self.llm.repair(
                        question, json.loads(context), previous, errors, language=plan.detected_language
                    )
                else:
                    raw = self.llm.answer(question, json.loads(context), language=plan.detected_language)
                if not isinstance(raw, str) or not raw.strip():
                    raise ValueError("llm_empty_response")
            except Exception as exc:
                code = "llm_timeout" if isinstance(exc, TimeoutError) else str(exc)
                if not re.fullmatch(r"llm_[a-z_]+(?:_\d{3})?", code):
                    code = "llm_generation_failed"
                execution["generation_error"] = code
                result["limitations"].append(code)
                return finish("generation_failed")
            finally:
                elapsed = time.perf_counter() - generation_started
                attempt_info["generation_seconds"] = elapsed
                execution["repair_generation_seconds" if attempt else "first_generation_seconds"] = elapsed
                metadata = getattr(self.llm, "last_metadata", {})
                # Provider already excludes content/reasoning; keep only documented diagnostics.
                attempt_info["provider_metadata"] = {
                    k: metadata[k]
                    for k in (
                        "http_status",
                        "model_instance_id",
                        "output_types",
                        "stats",
                        "content_characters",
                    )
                    if k in metadata
                }
            try:
                value, (answer, limitations, citations) = parse_answer(raw, allowed)
            except AskValidationError as exc:
                errors = exc.errors
                attempt_info["validation_errors"] = errors
                execution["final_validation_errors"] = errors
                if attempt == 0:
                    execution["first_validation_errors"] = errors
                if attempt == 0 and exc.retryable:
                    previous = raw
                    execution["repair_attempted"] = True
                    execution["repair_reason"] = list(dict.fromkeys(e["category"] for e in errors))
                    continue
                result["limitations"].append(str(exc))
                return finish("rejected")
            execution["final_validation_errors"] = []
            attempt_info["validation_errors"] = []
            if value["insufficient_evidence"]:
                result.update(answer=INSUFFICIENT[plan.detected_language], insufficient_evidence=True)
            else:
                result.update(answer=answer, insufficient_evidence=False, citations=citations)
            result["limitations"] += limitations
            return finish("accepted")
        return finish("rejected")
