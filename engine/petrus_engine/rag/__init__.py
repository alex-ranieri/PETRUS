from typing import Protocol

from petrus_engine.rag.evidence import EvidenceUnit


class VectorIndex(Protocol):
    def upsert(self, unit: EvidenceUnit, vector: list[float], fingerprint: str) -> None: ...
    def search(self, vector: list[float], limit: int = 10) -> list[tuple[str, float]]: ...
