"""k-DPP (greedy DPP / approximate MAP) diversity sampling for hierarchical clustering results.

Reads:
- D4C/embedding/clustering_results.json (from hierarchical_clustering.py)
- D4C/embedding/vector_index/ (optional, for selecting members by distance)

Outputs:
- selected.json (ids + metadata + config)
- selected.csv (optional)

Notes:
- This is a greedy DPP MAP-style selection (not an exact k-DPP sampler).
- Default kernel is cosine (L2-normalize then dot product).
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import pickle
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

import numpy as np


@dataclass(frozen=True)
class LoadedIndex:
    vectors: np.ndarray  # shape (n, d)
    id_to_idx: Dict[str, int]


def _load_json(path: Path) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _load_index(index_path: Path) -> LoadedIndex:
    vectors_file = index_path / "vectors.npy"
    mapping_file = index_path / "id_mapping.pkl"
    metadata_file = index_path / "metadata.json"

    if not vectors_file.exists():
        raise FileNotFoundError(f"vectors.npy not found: {vectors_file}")

    vectors = np.load(vectors_file)
    if vectors.ndim != 2:
        raise ValueError(f"Unexpected vectors shape: {vectors.shape} (expected 2D)")

    id_to_idx: Optional[Dict[str, int]] = None

    if mapping_file.exists():
        with open(mapping_file, "rb") as f:
            mappings = pickle.load(f)

        maybe = mappings.get("id_to_idx") if isinstance(mappings, dict) else None
        if isinstance(maybe, dict) and maybe:
            id_to_idx = maybe

    # Best-effort fallback: infer an ordering from metadata.json keys.
    # This may be incorrect if vectors.npy row order does not match sorted keys.
    if id_to_idx is None and metadata_file.exists():
        with open(metadata_file, "r", encoding="utf-8") as f:
            meta_obj = json.load(f)

        meta_map = meta_obj.get("metadata")
        if isinstance(meta_map, dict) and meta_map:
            ids = sorted([k for k in meta_map.keys() if isinstance(k, str) and k])
            if len(ids) != int(vectors.shape[0]):
                raise ValueError(
                    "vector_index is missing id_mapping.pkl, and metadata.json size does not match vectors.npy rows; "
                    "cannot infer id order safely. Provide id_mapping.pkl or run with --no-index."
                )
            id_to_idx = {vid: i for i, vid in enumerate(ids)}

    if id_to_idx is None:
        raise FileNotFoundError(
            f"id_mapping.pkl not found (and no usable metadata.json fallback): {mapping_file}. "
            "Provide id_mapping.pkl or run with --no-index."
        )

    return LoadedIndex(vectors=vectors, id_to_idx=id_to_idx)


def _available_levels(hierarchy: dict) -> List[int]:
    levels: List[int] = []
    for key in hierarchy.keys():
        if not key.startswith("level_"):
            continue
        try:
            levels.append(int(key.split("_", 1)[1]))
        except ValueError:
            continue
    return sorted(set(levels))


def _l2_normalize_rows(x: np.ndarray, eps: float = 1e-12) -> np.ndarray:
    norms = np.linalg.norm(x, axis=1, keepdims=True)
    norms = np.maximum(norms, eps)
    return x / norms


def greedy_dpp_order(
    X: np.ndarray,
    max_items: int,
    *,
    seed: int,
) -> List[int]:
    """Return a greedy DPP / pivoted-QR style selection order.

    Interprets L-ensemble L = (X_norm)(X_norm)^T (cosine kernel).

    This yields a deterministic order given the same X and seed.
    """

    if X.ndim != 2:
        raise ValueError(f"X must be 2D, got shape={X.shape}")

    n, d = X.shape
    if n == 0:
        return []
    max_items = int(max_items)
    if max_items <= 0:
        return []
    max_items = min(max_items, n)

    Xn = _l2_normalize_rows(X.astype(np.float32, copy=False))

    # Residual squared norms in feature space after orthogonalization.
    residual = np.einsum("ij,ij->i", Xn, Xn).astype(np.float64)

    selected: List[int] = []
    chosen = np.zeros(n, dtype=bool)

    # We keep orthonormal basis vectors q_t (each in R^d).
    Q: List[np.ndarray] = []

    rng = np.random.default_rng(seed)

    for _ in range(max_items):
        # Choose index with max residual; tie-break deterministically with a seeded tiny jitter.
        # The jitter only affects exact/near ties and remains reproducible.
        jitter = rng.uniform(low=0.0, high=1e-9, size=n)
        scores = residual + jitter
        scores[chosen] = -np.inf

        i = int(np.argmax(scores))
        if not np.isfinite(scores[i]) or residual[i] <= 1e-14:
            break

        selected.append(i)
        chosen[i] = True

        # Compute new basis vector q = (x_i - sum_t <q_t, x_i> q_t) / ||.||
        xi = Xn[i].astype(np.float64, copy=False)
        vi = xi.copy()
        for q in Q:
            vi -= float(np.dot(q, xi)) * q

        vi_norm2 = float(np.dot(vi, vi))
        if vi_norm2 <= 1e-14:
            # Degenerate / duplicate; continue without updating.
            continue

        q_new = (vi / math.sqrt(vi_norm2)).astype(np.float64)
        Q.append(q_new)

        # Update residuals: r_j <- r_j - <q_new, x_j>^2
        proj = Xn.astype(np.float64) @ q_new  # shape (n,)
        residual = residual - proj * proj
        residual = np.maximum(residual, 0.0)

    return selected


def select_diverse_vectors(
    *,
    clusters: Dict[str, dict],
    centers: np.ndarray,
    level: int,
    k: int,
    seed: int,
    mode: str,
    index: Optional[LoadedIndex],
    per_cluster: Optional[int],
) -> Tuple[List[dict], Dict[str, Any]]:
    """Select a diverse set of vector ids + metadata.

    Returns:
      - selected_items: list of {id, folder, file, tokens, cluster_key, level}
      - stats: dict with counters
    """

    if mode != "centers_then_members":
        raise ValueError(f"Unsupported mode: {mode}")

    cluster_keys = sorted(clusters.keys())
    num_clusters = len(cluster_keys)
    if num_clusters != centers.shape[0]:
        raise ValueError("centers rows mismatch cluster count")

    # k semantics (per the user's requirement):
    # - k <= 0: auto budget computed from per-cluster rule (sum of b(n))
    # - k  > 0: total output cap; MUST be >= number of clusters to keep 1-per-cluster coverage
    k = int(k)
    if k > 0 and k < num_clusters:
        raise ValueError(
            f"k must be >= number of clusters for full coverage: k={k} < clusters={num_clusters}. "
            "Use k=0 for auto budget or set a larger k."
        )

    def default_budget(cluster_size: int) -> int:
        if per_cluster is not None:
            return max(1, int(per_cluster))

        # Default heuristic from proposal/design.
        if level <= 0:
            return min(4, 1 + (cluster_size // 25))
        if level == 1:
            return 1 if cluster_size <= 25 else 2
        return 1

    def rank_members(cluster_key: str, info: dict) -> Tuple[List[dict], int]:
        """Return members ordered by representativeness + missing vector count."""
        vectors_meta = info.get("vectors") or []
        metas = [m for m in vectors_meta if isinstance(m, dict) and m.get("id")]
        if not metas:
            return [], 0

        if index is None:
            metas.sort(key=lambda m: str(m.get("id")))
            return metas, 0

        center = np.asarray(info.get("center"), dtype=np.float32)
        if center.ndim != 1 or center.shape[0] != index.vectors.shape[1]:
            raise ValueError(
                f"Center dim mismatch for {cluster_key}: {center.shape} vs d={index.vectors.shape[1]}"
            )

        missing = 0
        dists: List[Tuple[float, str]] = []
        meta_by_id: Dict[str, dict] = {}
        for m in metas:
            vid = m.get("id")
            if not isinstance(vid, str) or not vid:
                continue
            meta_by_id[vid] = m

            vec_idx = index.id_to_idx.get(vid)
            if vec_idx is None:
                missing += 1
                continue
            v = index.vectors[vec_idx].astype(np.float32, copy=False)
            dist = float(np.sum((v - center) ** 2))
            dists.append((dist, vid))

        dists.sort(key=lambda x: (x[0], x[1]))
        ordered = [meta_by_id[vid] for _, vid in dists]
        if not ordered:
            # If all vectors are missing in index, fall back to stable id order.
            metas.sort(key=lambda m: str(m.get("id")))
            return metas, missing
        return ordered, missing

    # Precompute per-cluster budgets and ordered members.
    per_cluster_budget: Dict[str, int] = {}
    per_cluster_members: Dict[str, List[dict]] = {}
    missing_vectors = 0

    for ck in cluster_keys:
        info = clusters[ck]
        members, miss = rank_members(ck, info)
        missing_vectors += miss

        b = default_budget(len(info.get("vectors") or []))
        b = max(1, int(b))
        if members:
            b = min(b, len(members))
        else:
            b = 0

        per_cluster_budget[ck] = b
        per_cluster_members[ck] = members

    clusters_with_members = [ck for ck in cluster_keys if per_cluster_budget.get(ck, 0) > 0]
    num_clusters_with_members = len(clusters_with_members)
    if num_clusters_with_members == 0:
        return [], {
            "selected": 0,
            "requested_k": k,
            "clusters": num_clusters,
            "clusters_with_members": 0,
            "missing_vectors_in_index": int(missing_vectors),
        }

    auto_total_budget = int(sum(per_cluster_budget.get(ck, 0) for ck in cluster_keys))
    base_coverage = num_clusters_with_members  # 1 per non-empty cluster

    total_target = auto_total_budget if k <= 0 else min(int(k), auto_total_budget)
    if total_target < base_coverage:
        # This can only happen if user provided k < base_coverage, but we guard above using total clusters.
        raise ValueError(
            f"Total target {total_target} is smaller than required coverage {base_coverage}; increase k or use auto." 
        )

    # Selection result, deduped by id.
    selected_by_id: Dict[str, dict] = {}

    # Step 1: guarantee 1 representative per cluster (for clusters that have members).
    for ck in clusters_with_members:
        m0 = per_cluster_members[ck][0]
        vid = m0.get("id")
        if not isinstance(vid, str) or not vid:
            continue
        if vid in selected_by_id:
            continue
        selected_by_id[vid] = {
            "id": vid,
            "folder": m0.get("folder"),
            "file": m0.get("file"),
            "tokens": m0.get("tokens"),
            "cluster_key": ck,
            "level": int(level),
            "rank_in_cluster": 1,
            "cluster_budget": int(per_cluster_budget.get(ck, 0)),
        }

    # Step 2: allocate remaining slots (extras) following greedy DPP order over centers.
    remaining = total_target - len(selected_by_id)
    if remaining > 0:
        # Rank clusters by DPP order (full order length = number of clusters).
        cluster_order = greedy_dpp_order(centers, max_items=num_clusters, seed=seed)
        ordered_cluster_keys = [cluster_keys[i] for i in cluster_order]

        # Round-robin: give each diverse cluster one extra at a time, until budgets exhausted.
        next_pos: Dict[str, int] = {ck: 1 for ck in cluster_keys}  # next member index to try (0 already used)

        made_progress = True
        while remaining > 0 and made_progress:
            made_progress = False
            for ck in ordered_cluster_keys:
                if remaining <= 0:
                    break
                b = int(per_cluster_budget.get(ck, 0))
                if b <= 1:
                    continue
                pos = int(next_pos.get(ck, 1))
                if pos >= b:
                    continue
                members = per_cluster_members.get(ck) or []
                if pos >= len(members):
                    continue
                m = members[pos]
                vid = m.get("id")
                next_pos[ck] = pos + 1
                if not isinstance(vid, str) or not vid:
                    continue
                if vid in selected_by_id:
                    continue
                selected_by_id[vid] = {
                    "id": vid,
                    "folder": m.get("folder"),
                    "file": m.get("file"),
                    "tokens": m.get("tokens"),
                    "cluster_key": ck,
                    "level": int(level),
                    "rank_in_cluster": int(pos + 1),
                    "cluster_budget": int(b),
                }
                remaining -= 1
                made_progress = True

    selected_items = list(selected_by_id.values())
    selected_items.sort(key=lambda x: (str(x.get("cluster_key")), int(x.get("rank_in_cluster") or 0), str(x.get("id"))))
    selected_ids = [x["id"] for x in selected_items]

    stats = {
        "selected": len(selected_items),
        "requested_k": int(k),
        "clusters": int(num_clusters),
        "clusters_with_members": int(num_clusters_with_members),
        "auto_total_budget": int(auto_total_budget),
        "coverage_min": int(base_coverage),
        "effective_target": int(total_target),
        "missing_vectors_in_index": int(missing_vectors),
        "deduped": len(selected_ids) - len(set(selected_ids)),
    }
    return selected_items, stats


def write_outputs(
    *,
    outdir: Path,
    selected_items: List[dict],
    config: Dict[str, Any],
    stats: Dict[str, Any],
    write_csv: bool,
):
    outdir.mkdir(parents=True, exist_ok=True)

    payload = {
        "created_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "config": config,
        "stats": stats,
        "selected_ids": [x.get("id") for x in selected_items],
        "selected": selected_items,
    }

    json_path = outdir / "selected.json"
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)

    if write_csv:
        csv_path = outdir / "selected.csv"
        with open(csv_path, "w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(
                f,
                fieldnames=[
                    "id",
                    "folder",
                    "file",
                    "tokens",
                    "cluster_key",
                    "level",
                    "cluster_budget",
                    "rank_in_cluster",
                ],
            )
            writer.writeheader()
            for row in selected_items:
                writer.writerow(
                    {
                        "id": row.get("id"),
                        "folder": row.get("folder"),
                        "file": row.get("file"),
                        "tokens": row.get("tokens"),
                        "cluster_key": row.get("cluster_key"),
                        "level": row.get("level"),
                        "cluster_budget": row.get("cluster_budget"),
                        "rank_in_cluster": row.get("rank_in_cluster"),
                    }
                )


def _md_escape(text: Any) -> str:
    s = "" if text is None else str(text)
    return s.replace("|", "\\|").replace("\n", " ")


def write_markdown(
    *,
    outdir: Path,
    selected_items: List[dict],
    config: Dict[str, Any],
    stats: Dict[str, Any],
):
    outdir.mkdir(parents=True, exist_ok=True)
    md_path = outdir / "selected.md"

    lines: List[str] = []
    lines.append(f"# Greedy k-DPP Selection (level_{config.get('level')})")
    lines.append("")
    lines.append("## Config")
    for k in ["input", "index_path", "level", "k", "mode", "seed", "per_cluster", "kernel", "member_selection"]:
        if k in config:
            lines.append(f"- **{k}**: `{_md_escape(config.get(k))}`")
    lines.append("")
    lines.append("## Stats")
    for k, v in stats.items():
        lines.append(f"- **{k}**: `{_md_escape(v)}`")
    lines.append("")
    lines.append("## Selected")
    lines.append("")
    lines.append("| # | id | folder | file | tokens | cluster_key | budget | rank |")
    lines.append("|---:|---|---|---|---:|---|---:|---:|")
    for i, item in enumerate(selected_items, start=1):
        lines.append(
            "| "
            + " | ".join(
                [
                    str(i),
                    _md_escape(item.get("id")),
                    _md_escape(item.get("folder")),
                    _md_escape(item.get("file")),
                    _md_escape(item.get("tokens")),
                    _md_escape(item.get("cluster_key")),
                    _md_escape(item.get("cluster_budget")),
                    _md_escape(item.get("rank_in_cluster")),
                ]
            )
            + " |"
        )

    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_summary(
    *,
    out_root: Path,
    run_config: Dict[str, Any],
    per_level_results: List[Tuple[int, Dict[str, Any], Dict[str, Any]]],
):
    """Write a human-readable summary for multi-level runs.

    per_level_results: list of (level, stats, config)
    """
    out_root.mkdir(parents=True, exist_ok=True)
    md_path = out_root / "summary.md"

    lines: List[str] = []
    lines.append("# Greedy k-DPP Sampling Summary")
    lines.append("")
    lines.append(f"- **created_at**: `{datetime.now(timezone.utc).isoformat(timespec='seconds')}`")
    for k in ["input", "index_path", "k", "mode", "seed", "per_cluster", "kernel"]:
        if k in run_config:
            lines.append(f"- **{k}**: `{_md_escape(run_config.get(k))}`")
    lines.append("")
    lines.append("## Results")
    lines.append("")
    lines.append("| level | clusters | selected | missing_vectors | outputs |")
    lines.append("|---:|---:|---:|---:|---|")
    for lvl, stats, cfg in per_level_results:
        subdir = f"level_{lvl}"
        outputs = f"[{subdir}/selected.md]({subdir}/selected.md) · [{subdir}/selected.json]({subdir}/selected.json)"
        if (out_root / subdir / "selected.csv").exists():
            outputs += f" · [{subdir}/selected.csv]({subdir}/selected.csv)"
        lines.append(
            "| "
            + " | ".join(
                [
                    str(lvl),
                    str(stats.get("clusters", "")),
                    str(stats.get("selected", "")),
                    str(stats.get("missing_vectors_in_index", "")),
                    outputs,
                ]
            )
            + " |"
        )

    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _resolve_level(results: dict, requested_level: Optional[int]) -> int:
    hierarchy = results.get("hierarchy") or {}
    levels = _available_levels(hierarchy)
    if not levels:
        raise RuntimeError("No level_* found in clustering results")
    if requested_level is None:
        return levels[-1]
    if requested_level not in levels:
        raise ValueError(f"Level {requested_level} not available. Available: {levels}")
    return requested_level


def _collect_level_clusters(results: dict, level: int) -> Tuple[Dict[str, dict], np.ndarray]:
    hierarchy = results.get("hierarchy") or {}
    level_key = f"level_{level}"
    level_data = hierarchy.get(level_key)
    if not isinstance(level_data, dict) or not level_data:
        raise RuntimeError(f"{level_key} not found or empty")

    cluster_keys = sorted(level_data.keys())
    centers: List[np.ndarray] = []
    clusters: Dict[str, dict] = {}

    for k in cluster_keys:
        info = level_data.get(k) or {}
        center = np.asarray(info.get("center"), dtype=np.float32)
        if center.ndim != 1:
            raise ValueError(f"Invalid center for cluster {k}: shape={center.shape}")
        centers.append(center)
        clusters[k] = info

    C = np.stack(centers, axis=0)
    return clusters, C


def _self_check(
    *,
    clusters_path: Path,
    index_path: Optional[Path],
    level: Optional[int],
    k: int,
    seed: int,
    per_cluster: Optional[int],
):
    results = _load_json(clusters_path)
    resolved_level = _resolve_level(results, level)
    clusters, centers = _collect_level_clusters(results, resolved_level)

    index = _load_index(index_path) if index_path is not None else None

    selected1, stats1 = select_diverse_vectors(
        clusters=clusters,
        centers=centers,
        level=resolved_level,
        k=k,
        seed=seed,
        mode="centers_then_members",
        index=index,
        per_cluster=per_cluster,
    )
    selected2, stats2 = select_diverse_vectors(
        clusters=clusters,
        centers=centers,
        level=resolved_level,
        k=k,
        seed=seed,
        mode="centers_then_members",
        index=index,
        per_cluster=per_cluster,
    )

    ids1 = [x["id"] for x in selected1]
    ids2 = [x["id"] for x in selected2]

    if len(ids1) != len(set(ids1)):
        raise AssertionError("Self-check failed: output has duplicates")
    if ids1 != ids2:
        raise AssertionError("Self-check failed: outputs not reproducible with same seed")
    if stats1.get("selected") != stats2.get("selected"):
        raise AssertionError("Self-check failed: selected counts mismatch")


def main():
    parser = argparse.ArgumentParser(
        description="Greedy k-DPP (approx MAP) sampling over hierarchical clustering results"
    )
    parser.add_argument(
        "--input",
        type=str,
        default=str(Path(__file__).resolve().parents[1] / "embedding" / "clustering_results.json"),
        help="Path to clustering_results.json",
    )
    parser.add_argument(
        "--index-path",
        type=str,
        default=str(Path(__file__).resolve().parents[1] / "embedding" / "vector_index"),
        help="Path to vector_index (vectors.npy + id_mapping.pkl) for member selection",
    )
    parser.add_argument(
        "--no-index",
        action="store_true",
        help="Do not load vector_index; member selection falls back to stable metadata ordering",
    )
    parser.add_argument(
        "--level",
        type=int,
        default=None,
        help="Which level_N to sample (default: deepest)",
    )
    parser.add_argument(
        "--levels",
        type=str,
        default=None,
        help="Comma-separated levels to sample, e.g. '0,1,2' (overrides --level)",
    )
    parser.add_argument(
        "--all-levels",
        action="store_true",
        help="Sample all available levels in clustering_results.json",
    )
    parser.add_argument(
        "--k",
        type=int,
        default=0,
        help=(
            "Total output cap per level. k=0 means auto (sum of per-cluster budgets). "
            "For full coverage, k must be >= number of clusters."
        ),
    )
    parser.add_argument(
        "--mode",
        type=str,
        default="centers_then_members",
        choices=["centers_then_members"],
        help="Sampling mode",
    )
    parser.add_argument("--seed", type=int, default=42, help="Random seed")
    parser.add_argument(
        "--out",
        type=str,
        default=str(Path(__file__).resolve().parent / "result"),
        help="Output directory. For --all-levels/--levels, this is the root dir (writes summary.md + per-level subdirs)",
    )
    parser.add_argument(
        "--csv",
        action="store_true",
        help="Also write selected.csv",
    )
    parser.add_argument(
        "--per-cluster",
        type=int,
        default=None,
        help="Override representatives per selected cluster (fixed integer)",
    )
    parser.add_argument(
        "--self-check",
        action="store_true",
        help="Run minimal reproducibility/dedup checks (no output)",
    )

    args = parser.parse_args()

    clusters_path = Path(args.input)
    if not clusters_path.exists():
        raise FileNotFoundError(f"Input not found: {clusters_path}")

    if args.self_check:
        index_path = None if args.no_index else Path(args.index_path)
        if index_path is not None and not index_path.exists():
            index_path = None
        _self_check(
            clusters_path=clusters_path,
            index_path=index_path,
            level=args.level,
            k=args.k,
            seed=args.seed,
            per_cluster=args.per_cluster,
        )
        print("OK: self-check passed")
        return

    results = _load_json(clusters_path)
    hierarchy = results.get("hierarchy") or {}
    available_levels = _available_levels(hierarchy)
    if not available_levels:
        raise RuntimeError("No level_* found in clustering results")

    # Determine which levels to run.
    chosen_levels: List[int]
    if args.all_levels:
        chosen_levels = available_levels
    elif args.levels:
        raw = [x.strip() for x in str(args.levels).split(",") if x.strip()]
        chosen_levels = []
        for x in raw:
            try:
                chosen_levels.append(int(x))
            except ValueError:
                raise ValueError(f"Invalid --levels entry: {x}")
        missing = [lvl for lvl in chosen_levels if lvl not in available_levels]
        if missing:
            raise ValueError(f"Levels not available: {missing}. Available: {available_levels}")
        chosen_levels = sorted(dict.fromkeys(chosen_levels))
    else:
        resolved_level = _resolve_level(results, args.level)
        chosen_levels = [resolved_level]

    index: Optional[LoadedIndex] = None
    if not args.no_index:
        index_path = Path(args.index_path)
        if index_path.exists():
            index = _load_index(index_path)
        else:
            print(f"WARN: index-path not found, falling back to no-index: {index_path}")

    out_root = Path(args.out)

    run_config = {
        "input": str(clusters_path),
        "index_path": None if args.no_index else str(Path(args.index_path)),
        "k": int(args.k),
        "mode": args.mode,
        "seed": int(args.seed),
        "per_cluster": args.per_cluster,
        "kernel": "cosine",
    }

    per_level_summary: List[Tuple[int, Dict[str, Any], Dict[str, Any]]] = []

    for lvl in chosen_levels:
        clusters, centers = _collect_level_clusters(results, lvl)

        selected_items, stats = select_diverse_vectors(
            clusters=clusters,
            centers=centers,
            level=lvl,
            k=args.k,
            seed=args.seed,
            mode=args.mode,
            index=index,
            per_cluster=args.per_cluster,
        )

        config = {
            "input": str(clusters_path),
            "index_path": None if args.no_index else str(Path(args.index_path)),
            "level": int(lvl),
            "k": int(args.k),
            "mode": args.mode,
            "seed": int(args.seed),
            "per_cluster": args.per_cluster,
            "kernel": "cosine",
            "member_selection": "l2_to_center" if index is not None else "stable_metadata_order",
        }

        outdir = out_root / f"level_{lvl}" if len(chosen_levels) > 1 else out_root
        write_outputs(
            outdir=outdir,
            selected_items=selected_items,
            config=config,
            stats=stats,
            write_csv=bool(args.csv),
        )
        write_markdown(outdir=outdir, selected_items=selected_items, config=config, stats=stats)

        per_level_summary.append((lvl, stats, config))

        print(f"OK: level_{lvl} selected {len(selected_items)} items (requested k={args.k})")
        print(f"OK: wrote {outdir / 'selected.json'}")
        print(f"OK: wrote {outdir / 'selected.md'}")
        if args.csv:
            print(f"OK: wrote {outdir / 'selected.csv'}")

    if len(chosen_levels) > 1:
        write_summary(out_root=out_root, run_config=run_config, per_level_results=per_level_summary)
        print(f"OK: wrote {out_root / 'summary.md'}")


if __name__ == "__main__":
    main()
