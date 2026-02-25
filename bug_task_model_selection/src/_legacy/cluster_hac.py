from __future__ import annotations

import argparse
import json
import pickle
from pathlib import Path

import numpy as np
from sklearn.cluster import AgglomerativeClustering

from .cluster_prep import VectorMeta  # noqa: F401 - needed for pickle


def _l2_normalize_rows(x: np.ndarray, *, eps: float = 1e-12) -> np.ndarray:
    norms = np.linalg.norm(x, axis=1, keepdims=True)
    norms = np.maximum(norms, eps)
    return x / norms


class _UnionFind:
    def __init__(self, n: int) -> None:
        self.parent = list(range(n))
        self.size = [1] * n

    def find(self, a: int) -> int:
        while self.parent[a] != a:
            self.parent[a] = self.parent[self.parent[a]]
            a = self.parent[a]
        return a

    def union(self, a: int, b: int) -> int:
        ra = self.find(a)
        rb = self.find(b)
        if ra == rb:
            return ra
        if self.size[ra] < self.size[rb]:
            ra, rb = rb, ra
        self.parent[rb] = ra
        self.size[ra] += self.size[rb]
        return ra


def _cut_k_from_children(*, children: np.ndarray, n_samples: int, k: int) -> np.ndarray:
    """Cut a full agglomerative merge tree into exactly k clusters.

    children is the sklearn-style array of shape (n_samples-1, 2).
    Node ids follow sklearn convention:
      - leaf i is 0..n_samples-1
      - merge node (n_samples + t) corresponds to children[t]

    Returns labels in [0, k-1] for each sample.
    """

    if k <= 0:
        raise ValueError(f"k must be >= 1, got {k}")
    if k > n_samples:
        raise ValueError(f"k must be <= n_samples, got k={k} n_samples={n_samples}")

    merges_needed = n_samples - k
    uf = _UnionFind(n_samples)

    # Map any node_id (leaf or internal) -> representative leaf root after unions.
    node_rep: dict[int, int] = {i: i for i in range(n_samples)}

    for t in range(min(merges_needed, children.shape[0])):
        a = int(children[t, 0])
        b = int(children[t, 1])

        ra = node_rep.get(a)
        if ra is None:
            raise RuntimeError(f"Missing representative for node {a}")
        rb = node_rep.get(b)
        if rb is None:
            raise RuntimeError(f"Missing representative for node {b}")

        root = uf.union(ra, rb)
        node_rep[n_samples + t] = root

    # Assign compact labels.
    roots: dict[int, int] = {}
    labels = np.empty(n_samples, dtype=np.int32)
    next_label = 0
    for i in range(n_samples):
        r = uf.find(i)
        if r not in roots:
            roots[r] = next_label
            next_label += 1
        labels[i] = roots[r]

    return labels


def export_hac(
    *,
    vectors_path: Path,
    id_mapping_path: Path,
    metadata_path: Path,
    out_dir: Path,
    metric: str = "cosine",
    linkage: str = "average",
    ks: list[int] | None = None,
    normalize: bool = True,
) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)

    vectors = np.load(vectors_path)
    with id_mapping_path.open("rb") as f:
        ids: list[str] = pickle.load(f)
    with metadata_path.open("rb") as f:
        meta = pickle.load(f)

    if vectors.ndim != 2:
        raise ValueError(f"Expected vectors to be 2D (N,D), got shape={vectors.shape}")
    n_samples = int(vectors.shape[0])
    if len(ids) != n_samples:
        raise ValueError(f"id_mapping length {len(ids)} != vectors rows {n_samples}")

    if metric == "cosine" and normalize:
        vectors = _l2_normalize_rows(vectors)

    # Full merge tree.
    model = AgglomerativeClustering(
        n_clusters=None,
        distance_threshold=0,
        metric=metric,
        linkage=linkage,
        compute_distances=True,
    )
    model.fit(vectors)

    children = np.asarray(model.children_, dtype=np.int32)
    distances = getattr(model, "distances_", None)
    if distances is not None:
        distances = np.asarray(distances, dtype=np.float64)

    # 2.2 Export merge tree / dendrogram data.
    np.savez_compressed(
        out_dir / "merge_tree.npz",
        children=children,
        distances=distances if distances is not None else np.array([], dtype=np.float64),
    )
    with (out_dir / "merge_tree_meta.json").open("w", encoding="utf-8") as f:
        json.dump(
            {
                "n_samples": n_samples,
                "dim": int(vectors.shape[1]),
                "metric": metric,
                "linkage": linkage,
                "vectors": str(vectors_path),
                "id_mapping": str(id_mapping_path),
                "metadata": str(metadata_path),
            },
            f,
            ensure_ascii=False,
            indent=2,
        )

    # 2.3 Export multiple cut levels.
    if ks:
        cuts_dir = out_dir / "cuts"
        cuts_dir.mkdir(parents=True, exist_ok=True)

        for k in ks:
            labels = _cut_k_from_children(children=children, n_samples=n_samples, k=int(k))
            k_dir = cuts_dir / f"k={int(k)}"
            k_dir.mkdir(parents=True, exist_ok=True)

            # Write assignments.jsonl for easy downstream processing.
            with (k_dir / "assignments.jsonl").open("w", encoding="utf-8") as af:
                for item_id, lab in zip(ids, labels):
                    af.write(json.dumps({"item_id": item_id, "cluster_id": int(lab)}, ensure_ascii=False) + "\n")

            # Write clusters.json (cluster_id -> [item_id])
            clusters: dict[str, list[str]] = {}
            for item_id, lab in zip(ids, labels):
                key = str(int(lab))
                clusters.setdefault(key, []).append(item_id)
            with (k_dir / "clusters.json").open("w", encoding="utf-8") as cf:
                json.dump(clusters, cf, ensure_ascii=False, indent=2)

            # Lightweight per-run metadata.
            with (k_dir / "meta.json").open("w", encoding="utf-8") as mf:
                json.dump(
                    {
                        "k": int(k),
                        "n_samples": n_samples,
                        "metric": metric,
                        "linkage": linkage,
                        "normalize": bool(normalize),
                    },
                    mf,
                    ensure_ascii=False,
                    indent=2,
                )

    # Also persist a copy of the metadata mapping (useful for downstream without re-pointing).
    try:
        with (out_dir / "metadata.pkl").open("wb") as f:
            pickle.dump(meta, f)
    except Exception:
        # Best-effort; export_hac doesn't require this.
        pass


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Agglomerative hierarchical clustering for bug_task_model_selection")
    p.add_argument("--vectors", type=str, required=True, help="Path to vectors.npy")
    p.add_argument("--id-mapping", type=str, required=True, help="Path to id_mapping.pkl")
    p.add_argument("--metadata", type=str, required=True, help="Path to metadata.pkl")
    p.add_argument("--outdir", type=str, required=True, help="Output directory")
    p.add_argument("--metric", type=str, default="cosine", help="Distance metric (default: cosine)")
    p.add_argument("--linkage", type=str, default="average", help="Linkage (default: average)")
    p.add_argument("--ks", type=str, default="10,20,50", help="Comma-separated cut levels (e.g. 10,20,50); empty to skip")
    p.add_argument("--no-normalize", action="store_true", help="Disable L2 normalization before cosine")

    args = p.parse_args(argv)

    ks: list[int] | None
    if args.ks is None:
        ks = None
    else:
        raw = str(args.ks).strip()
        if raw == "":
            ks = None
        else:
            ks = [int(x.strip()) for x in raw.split(",") if x.strip()]

    export_hac(
        vectors_path=Path(args.vectors),
        id_mapping_path=Path(args.id_mapping),
        metadata_path=Path(args.metadata),
        out_dir=Path(args.outdir),
        metric=str(args.metric),
        linkage=str(args.linkage),
        ks=ks,
        normalize=(not bool(args.no_normalize)),
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
