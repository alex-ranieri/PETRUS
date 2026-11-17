"""Embedding and retrieval interfaces; provenance stays with EvidenceUnit."""

from dataclasses import dataclass
from typing import Protocol, Sequence

from petrus_engine.rag.evidence import EvidenceUnit


class EmbeddingProvider(Protocol):
    provider_id: str
    model_id: str
    dimension: int | None

    def embed_documents(self, texts: Sequence[str]) -> list[list[float]]: ...
    def embed_query(self, text: str) -> list[float]: ...


@dataclass(frozen=True)
class RetrievalQuery:
    text: str
    limit: int = 10

    def __post_init__(self):
        if not self.text.strip() or self.limit < 1:
            raise ValueError("A nonempty query and positive limit are required")


@dataclass(frozen=True)
class RetrievalHit:
    unit: EvidenceUnit
    score: float

    lexical_rank: int | None = None
    semantic_rank: int | None = None
    hybrid_score: float | None = None
    section_boost: float = 1.0
