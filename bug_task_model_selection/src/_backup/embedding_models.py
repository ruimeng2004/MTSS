from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class EmbeddedItem:
    item_id: str
    slug: str
    view: str
    embedding: Any
    embedding_dim: int | None
    embedding_model: str
    embedding_proxy: str
    tokens: int | str | None
    source_file: str | None
    transform_config: dict[str, Any] | None
