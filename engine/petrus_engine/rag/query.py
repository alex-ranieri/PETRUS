"""Transparent query planning; optional local expansion never replaces the original."""

import re
import unicodedata
from dataclasses import dataclass, field


@dataclass
class QueryPlan:
    original_query: str
    normalized_query: str
    detected_language: str
    intent: str
    expanded_terms: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


def plan_query(query):
    normalized = " ".join(
        re.findall(
            r"\w+",
            "".join(
                c for c in unicodedata.normalize("NFKD", query.casefold()) if not unicodedata.combining(c)
            ),
        )
    )
    words = set(normalized.split())
    pt = bool(
        words
        & {
            "qual",
            "quais",
            "metodo",
            "metodos",
            "metodologia",
            "protocolo",
            "filogenetica",
            "evolucao",
            "vigilancia",
            "genomica",
            "recombinacao",
            "dinamica",
            "utilizado",
            "artigos",
            "resultado",
            "limitacao",
            "limitacoes",
            "adaptacao",
        }
    )
    intent = "general"
    for kind, pattern in [
        (
            "methods",
            r"\b(methods?|methodology|software|pipeline|protocol|metodos?|metodologia|protocolo)\b|phylogenetic reconstruction",
        ),
        ("results", r"\b(results?|findings?|association|observed|resultados?|achados?)\b"),
        ("limitations", r"\b(limitations?|caveats?|limitacoes|limitacao)\b"),
    ]:
        if re.search(pattern, normalized):
            intent = kind
            break
    return QueryPlan(query, normalized, "pt-BR" if pt else "en", intent)
