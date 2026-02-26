from __future__ import annotations

from math import ceil


def estimate_tokens_from_text(text: str) -> int:
    """Rough text-token estimate for planning/monitoring, not billing-accurate."""
    if not text:
        return 0
    return ceil(len(text) / 4)


def excerpt_text(text: str, max_chars: int = 6000) -> str:
    if len(text) <= max_chars:
        return text
    head = max_chars // 2
    tail = max_chars - head
    return text[:head] + "\n\n[...TRUNCATED FOR COST CONTROL...]\n\n" + text[-tail:]
