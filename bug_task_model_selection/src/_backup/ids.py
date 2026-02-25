from __future__ import annotations

from .views import BugView


def stable_item_id(slug: str, view: BugView) -> str:
    return f"{slug}__{view.value}"
