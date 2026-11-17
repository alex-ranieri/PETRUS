from typing import Protocol


class LLMProvider(Protocol):
    """Opt-in provider contract. Only explicitly configured local providers are supported."""

    def answer(self, question: str, evidence: list[dict], language: str = "en") -> str: ...
