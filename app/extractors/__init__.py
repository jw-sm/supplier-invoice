from __future__ import annotations
import os
from .base import LLMExtractor
from .gemini import GeminiExtractor
from .claude import ClaudeExtractor

_REGISTRY: dict[str, type[LLMExtractor]] = {
    "gemini": GeminiExtractor,
    "claude": ClaudeExtractor,
}

_REQUIRED_ENV = {
    "gemini": "GEMINI_API_KEY",
    "claude": "ANTHROPIC_API_KEY",
}


def get_extractors() -> list[LLMExtractor]:
    """Return configured extractors in fallback order.

    Providers with no API key are skipped silently. If the resulting chain is
    empty, the pipeline warns and falls back to the deterministic result.
    """
    order = [
        p.strip().lower()
        for p in os.getenv("LLM_FALLBACK_ORDER", "gemini").split(",")
        if p.strip()
    ]
    chain: list[LLMExtractor] = []
    for name in order:
        if name not in _REGISTRY:
            raise ValueError(
                f"Unknown provider '{name}' in LLM_FALLBACK_ORDER. "
                f"Choose from {list(_REGISTRY)}"
            )
        if not os.getenv(_REQUIRED_ENV[name]):
            continue
        chain.append(_REGISTRY[name]())
    return chain