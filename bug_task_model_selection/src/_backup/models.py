from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class BugItem:
    item_id: str
    slug: str
    view: str
    source_file: str | None
    text: str
    tokens: int
    transform_config: dict[str, Any] | None = None
