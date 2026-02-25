from __future__ import annotations


def approximate_tokens(text: str) -> int:
    s = text.strip()
    if not s:
        return 0
    return len(s.split())
