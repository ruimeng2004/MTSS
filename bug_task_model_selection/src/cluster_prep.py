from __future__ import annotations

import argparse
import json
import pickle
from dataclasses import dataclass
from pathlib import Path

import numpy as np


@dataclass(frozen=True)
class VectorMeta:
    item_id: str
    slug: str
    view: str
    source_file: str | None
    tokens: int | str | None
    embedding_model: str | None
    embedding_proxy: str | None


def _iter_jsonl(path: Path):
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            s = line.strip()
            if not s:
                continue
            yield json.loads(s)


def load_embeddings_jsonl(
    *,
    embeddings_path: Path,
    strict_dim: bool = True,
    view_filter: str | None = None,
) -> tuple[np.ndarray, list[str], dict[str, VectorMeta]]:
    """Load embeddings.jsonl into a matrix.

    Returns:
        vectors: (N, D) float32
        ids: list[str] in the same order
        meta: mapping id -> VectorMeta

    Notes:
        - Skips records with embedding==None
        - If strict_dim=True, enforces constant D across all rows
    """

    ids: list[str] = []
    meta: dict[str, VectorMeta] = {}
    vecs: list[np.ndarray] = []
    dim: int | None = None

    for obj in _iter_jsonl(embeddings_path):
        emb = obj.get("embedding")
        if emb is None:
            continue
        if not isinstance(emb, list):
            continue

        # Filter by view if specified
        if view_filter is not None and obj.get("view") != view_filter:
            continue

        if dim is None:
            dim = len(emb)
        elif strict_dim and len(emb) != dim:
            raise ValueError(f"Inconsistent embedding_dim: expected {dim}, got {len(emb)} for {obj.get('item_id')}")

        v = np.asarray(emb, dtype=np.float32)
        if dim is not None and v.shape[0] != dim:
            continue

        item_id = str(obj.get("item_id"))
        ids.append(item_id)
        vecs.append(v)
        meta[item_id] = VectorMeta(
            item_id=item_id,
            slug=str(obj.get("slug")),
            view=str(obj.get("view")),
            source_file=obj.get("source_file"),
            tokens=obj.get("tokens"),
            embedding_model=obj.get("embedding_model"),
            embedding_proxy=obj.get("embedding_proxy"),
        )

    if not vecs:
        raise ValueError(f"No valid embeddings found in {embeddings_path}")

    vectors = np.stack(vecs, axis=0).astype(np.float32, copy=False)
    return vectors, ids, meta


def export_vector_index(
    *,
    embeddings_path: Path,
    out_dir: Path,
    strict_dim: bool = True,
    view_filter: str | None = None,
) -> None:
    """Export a vector index compatible with embedding/ scripts.

    Outputs:
        out_dir/
          vectors.npy
          id_mapping.pkl      (list[str])
          metadata.pkl        (dict[str, VectorMeta])
    """

    out_dir.mkdir(parents=True, exist_ok=True)

    vectors, ids, meta = load_embeddings_jsonl(
        embeddings_path=embeddings_path, 
        strict_dim=strict_dim,
        view_filter=view_filter,
    )

    np.save(out_dir / "vectors.npy", vectors)
    with (out_dir / "id_mapping.pkl").open("wb") as f:
        pickle.dump(ids, f)
    with (out_dir / "metadata.pkl").open("wb") as f:
        pickle.dump(meta, f)


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Prepare vector index from bug_task_model_selection embeddings.jsonl")
    p.add_argument("--embeddings", type=str, required=True, help="Path to embeddings.jsonl")
    p.add_argument("--outdir", type=str, required=True, help="Output dir for vectors.npy + id_mapping.pkl")
    p.add_argument("--no-strict-dim", action="store_true", help="Allow inconsistent embedding dims (will skip bad rows)")
    p.add_argument("--view", type=str, default=None, help="Filter by view (e.g. report, test, error)")

    args = p.parse_args(argv)

    export_vector_index(
        embeddings_path=Path(args.embeddings),
        out_dir=Path(args.outdir),
        strict_dim=(not args.no_strict_dim),
        view_filter=args.view,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
