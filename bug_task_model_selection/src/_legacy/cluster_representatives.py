from __future__ import annotations

import argparse
import json
import pickle
from pathlib import Path

import numpy as np

from .cluster_prep import VectorMeta  # noqa: F401 - needed for pickle


def _l2_normalize_rows(x: np.ndarray, *, eps: float = 1e-12) -> np.ndarray:
    norms = np.linalg.norm(x, axis=1, keepdims=True)
    norms = np.maximum(norms, eps)
    return x / norms


def _l2_normalize_vec(x: np.ndarray, *, eps: float = 1e-12) -> np.ndarray:
    n = float(np.linalg.norm(x))
    if n <= eps:
        return x
    return x / n


def _greedy_dpp_order(*, X: np.ndarray, max_items: int, seed: int) -> list[int]:
    if X.ndim != 2:
        raise ValueError(f"X must be 2D, got shape={X.shape}")
    n, _ = X.shape
    if n == 0:
        return []
    max_items = int(max_items)
    if max_items <= 0:
        return []
    max_items = min(max_items, n)

    Xn = _l2_normalize_rows(X.astype(np.float32, copy=False))
    residual = np.einsum("ij,ij->i", Xn, Xn).astype(np.float64)

    selected: list[int] = []
    chosen = np.zeros(n, dtype=bool)
    Q: list[np.ndarray] = []
    rng = np.random.default_rng(int(seed))

    for _ in range(max_items):
        jitter = rng.uniform(low=0.0, high=1e-9, size=n)
        scores = residual + jitter
        scores[chosen] = -np.inf
        i = int(np.argmax(scores))
        if not np.isfinite(scores[i]) or residual[i] <= 1e-14:
            break
        selected.append(i)
        chosen[i] = True

        xi = Xn[i].astype(np.float64, copy=False)
        vi = xi.copy()
        for q in Q:
            vi -= float(np.dot(q, xi)) * q
        vi_norm2 = float(np.dot(vi, vi))
        if vi_norm2 <= 1e-14:
            continue
        q_new = (vi / float(np.sqrt(vi_norm2))).astype(np.float64)
        Q.append(q_new)
        proj = Xn.astype(np.float64) @ q_new
        residual = residual - proj * proj
        residual = np.maximum(residual, 0.0)

    return selected


def _meta_to_dict(m) -> dict:
    if m is None:
        return {}
    if isinstance(m, dict):
        return dict(m)

    out: dict[str, object] = {}
    for k in [
        "item_id",
        "slug",
        "view",
        "source_file",
        "tokens",
        "embedding_model",
        "embedding_proxy",
    ]:
        if hasattr(m, k):
            out[k] = getattr(m, k)
    return out


def _read_assignments_jsonl(path: Path) -> dict[str, int]:
    out: dict[str, int] = {}
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            s = line.strip()
            if not s:
                continue
            obj = json.loads(s)
            item_id = obj.get("item_id")
            cid = obj.get("cluster_id")
            if not isinstance(item_id, str):
                continue
            if cid is None:
                continue
            out[item_id] = int(cid)
    return out


def _select_medoid_cosine(*, vectors: np.ndarray, indices: np.ndarray, ids: list[str]) -> int:
    sub = vectors[indices]
    centroid = sub.mean(axis=0)
    centroid = _l2_normalize_vec(centroid)
    sims = sub @ centroid

    best_local = int(np.argmax(sims))
    best_score = float(sims[best_local])
    best_global = int(indices[best_local])

    # Stable tie-break by item_id.
    ties = np.where(np.isclose(sims, best_score))[0]
    if ties.size > 1:
        best_global = min(
            ((int(indices[int(t)]), ids[int(indices[int(t)])]) for t in ties),
            key=lambda x: x[1],
        )[0]

    return best_global


def _select_medoid_euclidean(*, vectors: np.ndarray, indices: np.ndarray, ids: list[str]) -> int:
    sub = vectors[indices]
    centroid = sub.mean(axis=0)
    d2 = np.sum((sub - centroid) ** 2, axis=1)

    best_local = int(np.argmin(d2))
    best_score = float(d2[best_local])
    best_global = int(indices[best_local])

    ties = np.where(np.isclose(d2, best_score))[0]
    if ties.size > 1:
        best_global = min(
            ((int(indices[int(t)]), ids[int(indices[int(t)])]) for t in ties),
            key=lambda x: x[1],
        )[0]

    return best_global


def _farthest_first(
    *,
    vectors: np.ndarray,
    indices: np.ndarray,
    ids: list[str],
    metric: str,
    k: int,
    start_index: int,
) -> list[int]:
    chosen: list[int] = [start_index]
    if k <= 1:
        return chosen

    cand = [int(i) for i in indices.tolist() if int(i) != int(start_index)]
    if not cand:
        return chosen

    # Maintain per-candidate min distance to chosen set.
    if metric == "cosine":
        # distance = 1 - dot(u,v); assumes vectors are normalized.
        chosen_vec = vectors[start_index]
        min_dist = np.ones(len(cand), dtype=np.float64) - (vectors[cand] @ chosen_vec).astype(np.float64)
    else:
        chosen_vec = vectors[start_index]
        min_dist = np.linalg.norm(vectors[cand] - chosen_vec, axis=1).astype(np.float64)

    while len(chosen) < k and cand:
        best_pos = int(np.argmax(min_dist))
        best_d = float(min_dist[best_pos])

        # Stable tie-break by item_id.
        ties = np.where(np.isclose(min_dist, best_d))[0]
        if ties.size > 1:
            best_pos = min(
                ((int(t), ids[int(cand[int(t)])]) for t in ties),
                key=lambda x: x[1],
            )[0]

        nxt = int(cand[best_pos])
        chosen.append(nxt)

        # Remove chosen candidate.
        cand.pop(best_pos)
        min_dist = np.delete(min_dist, best_pos)
        if not cand:
            break

        # Update min distances with new chosen.
        if metric == "cosine":
            d = np.ones(len(cand), dtype=np.float64) - (vectors[cand] @ vectors[nxt]).astype(np.float64)
        else:
            d = np.linalg.norm(vectors[cand] - vectors[nxt], axis=1).astype(np.float64)
        min_dist = np.minimum(min_dist, d)

    return chosen


def export_representatives_for_k(
    *,
    vectors: np.ndarray,
    ids: list[str],
    meta: dict,
    assignments_path: Path,
    out_dir: Path,
    reps_per_cluster: int,
    metric: str,
    method: str,
    seed: int,
) -> None:
    assignments = _read_assignments_jsonl(assignments_path)

    cluster_to_indices: dict[int, list[int]] = {}
    for idx, item_id in enumerate(ids):
        if item_id not in assignments:
            continue
        cid = int(assignments[item_id])
        cluster_to_indices.setdefault(cid, []).append(idx)

    out_dir.mkdir(parents=True, exist_ok=True)

    rng = np.random.default_rng(seed)

    reps_path = out_dir / "representatives.jsonl"
    summary_path = out_dir / "clusters_summary.json"

    summary: dict[str, dict] = {}

    with reps_path.open("w", encoding="utf-8") as rf:
        for cid in sorted(cluster_to_indices.keys()):
            idxs = np.asarray(cluster_to_indices[cid], dtype=np.int64)
            if idxs.size == 0:
                continue

            # Deterministic shuffle inside cluster so farthest-first has stable ordering
            # when distances are equal.
            perm = rng.permutation(idxs.size)
            idxs = idxs[perm]
            idxs = np.asarray(sorted(idxs.tolist(), key=lambda i: ids[int(i)]), dtype=np.int64)

            if method == "kdpp":
                if metric != "cosine":
                    raise ValueError("kdpp method currently supports only cosine metric")
                X = vectors[idxs]
                cluster_seed = int(seed) * 1000003 + int(cid)
                local = _greedy_dpp_order(X=X, max_items=int(reps_per_cluster), seed=cluster_seed)
                chosen = [int(idxs[int(i)]) for i in local]
            elif method == "farthest_first":
                if metric == "cosine":
                    med = _select_medoid_cosine(vectors=vectors, indices=idxs, ids=ids)
                else:
                    med = _select_medoid_euclidean(vectors=vectors, indices=idxs, ids=ids)

                chosen = _farthest_first(
                    vectors=vectors,
                    indices=idxs,
                    ids=ids,
                    metric=metric,
                    k=int(reps_per_cluster),
                    start_index=int(med),
                )
            else:
                raise ValueError(f"Unsupported method: {method}")

            rep_ids = [ids[int(i)] for i in chosen]
            summary[str(cid)] = {
                "cluster_id": int(cid),
                "size": int(idxs.size),
                "representatives": rep_ids,
            }

            for rank, gi in enumerate(chosen, start=1):
                item_id = ids[int(gi)]
                md = _meta_to_dict(meta.get(item_id))
                rf.write(
                    json.dumps(
                        {
                            "cluster_id": int(cid),
                            "rank": int(rank),
                            "item_id": item_id,
                            **md,
                        },
                        ensure_ascii=False,
                    )
                    + "\n"
                )

    with summary_path.open("w", encoding="utf-8") as sf:
        json.dump(summary, sf, ensure_ascii=False, indent=2)


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Select per-cluster representatives from clustering assignments")
    p.add_argument("--vectors", type=str, required=True, help="Path to vectors.npy")
    p.add_argument("--id-mapping", type=str, required=True, help="Path to id_mapping.pkl")
    p.add_argument("--metadata", type=str, required=True, help="Path to metadata.pkl")

    g = p.add_mutually_exclusive_group(required=True)
    g.add_argument("--assignments", type=str, help="Path to assignments.jsonl")
    g.add_argument("--cuts-dir", type=str, help="Path to cluster_hac output cuts/ directory")

    p.add_argument("--k", type=int, default=None, help="Cut level k (required when using --cuts-dir)")
    p.add_argument("--ks", type=str, default=None, help="Comma-separated ks to process (only with --cuts-dir)")

    p.add_argument("--outdir", type=str, required=True, help="Output directory")
    p.add_argument("--reps-per-cluster", type=int, default=1, help="Representatives per cluster (default: 1)")
    p.add_argument("--method", type=str, default="farthest_first", help="farthest_first or kdpp (default: farthest_first)")
    p.add_argument("--metric", type=str, default="cosine", help="cosine or euclidean (default: cosine)")
    p.add_argument("--seed", type=int, default=0, help="Seed for reproducibility")
    p.add_argument("--no-normalize", action="store_true", help="Disable L2 normalization for cosine")

    args = p.parse_args(argv)

    vectors = np.load(Path(args.vectors))
    with Path(args.id_mapping).open("rb") as f:
        ids: list[str] = pickle.load(f)
    with Path(args.metadata).open("rb") as f:
        meta = pickle.load(f)

    if vectors.ndim != 2:
        raise ValueError(f"Expected vectors to be 2D (N,D), got shape={vectors.shape}")
    if len(ids) != int(vectors.shape[0]):
        raise ValueError(f"id_mapping length {len(ids)} != vectors rows {int(vectors.shape[0])}")

    metric = str(args.metric)
    if metric not in {"cosine", "euclidean"}:
        raise ValueError(f"Unsupported metric: {metric}")

    if metric == "cosine" and not bool(args.no_normalize):
        vectors = _l2_normalize_rows(vectors)

    out_root = Path(args.outdir)

    if args.assignments:
        export_representatives_for_k(
            vectors=vectors,
            ids=ids,
            meta=meta,
            assignments_path=Path(args.assignments),
            out_dir=out_root,
            reps_per_cluster=int(args.reps_per_cluster),
            metric=metric,
            method=str(args.method),
            seed=int(args.seed),
        )
        return 0

    cuts_dir = Path(args.cuts_dir)
    if args.ks is not None:
        ks = [int(x.strip()) for x in str(args.ks).split(",") if x.strip()]
    elif args.k is not None:
        ks = [int(args.k)]
    else:
        raise ValueError("When using --cuts-dir, you must provide --k or --ks")

    for k in ks:
        assignments_path = cuts_dir / f"k={int(k)}" / "assignments.jsonl"
        export_representatives_for_k(
            vectors=vectors,
            ids=ids,
            meta=meta,
            assignments_path=assignments_path,
            out_dir=out_root / f"k={int(k)}",
            reps_per_cluster=int(args.reps_per_cluster),
            metric=metric,
            method=str(args.method),
            seed=int(args.seed),
        )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
