"""Generate images to visualize clustering results.

Reads:
- clustering_results.json (from hierarchical_clustering.py)
- vector_index/ (vectors.npy + id_mapping.pkl)

Outputs PNGs (headless-friendly).
"""

from __future__ import annotations

import argparse
import json
import pickle
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np

# Headless backend for servers/CI
import matplotlib

matplotlib.use("Agg")  # must be set before pyplot import
import matplotlib.pyplot as plt

from sklearn.decomposition import PCA


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

    if not vectors_file.exists():
        raise FileNotFoundError(f"vectors.npy not found: {vectors_file}")
    if not mapping_file.exists():
        raise FileNotFoundError(f"id_mapping.pkl not found: {mapping_file}")

    vectors = np.load(vectors_file)
    if vectors.ndim != 2:
        raise ValueError(f"Unexpected vectors shape: {vectors.shape} (expected 2D)")

    with open(mapping_file, "rb") as f:
        mappings = pickle.load(f)

    id_to_idx = mappings.get("id_to_idx")
    if not isinstance(id_to_idx, dict) or not id_to_idx:
        raise ValueError("id_mapping.pkl missing 'id_to_idx' mapping")

    return LoadedIndex(vectors=vectors, id_to_idx=id_to_idx)


def _available_levels(hierarchy: dict) -> List[int]:
    levels: List[int] = []
    for key in hierarchy.keys():
        if key.startswith("level_"):
            try:
                levels.append(int(key.split("_", 1)[1]))
            except ValueError:
                continue
    return sorted(set(levels))


def _build_vector_to_cluster(hierarchy: dict, level: int) -> Dict[str, str]:
    level_key = f"level_{level}"
    if level_key not in hierarchy:
        raise KeyError(f"{level_key} not found in clustering results")

    v2c: Dict[str, str] = {}
    for cluster_key, cluster_info in hierarchy[level_key].items():
        vectors_meta = cluster_info.get("vectors") or []
        for meta in vectors_meta:
            vid = meta.get("id")
            if isinstance(vid, str) and vid:
                v2c[vid] = cluster_key
    return v2c


def _sample_indices(n: int, max_points: Optional[int], seed: int) -> np.ndarray:
    if max_points is None or max_points <= 0 or n <= max_points:
        return np.arange(n)
    rng = np.random.default_rng(seed)
    return rng.choice(n, size=max_points, replace=False)


def _cluster_palette(num_clusters: int):
    if num_clusters <= 20:
        return plt.get_cmap("tab20", num_clusters)
    return plt.get_cmap("hsv", num_clusters)


def plot_scatter(
    xy: np.ndarray,
    labels: np.ndarray,
    cluster_names: List[str],
    out_file: Path,
    title: str,
    legend: bool,
):
    out_file.parent.mkdir(parents=True, exist_ok=True)

    fig, ax = plt.subplots(figsize=(12, 9), dpi=180)
    cmap = _cluster_palette(len(cluster_names))

    for cluster_id, cluster_name in enumerate(cluster_names):
        mask = labels == cluster_id
        if not np.any(mask):
            continue
        ax.scatter(
            xy[mask, 0],
            xy[mask, 1],
            s=10,
            alpha=0.75,
            c=[cmap(cluster_id)],
            label=f"{cluster_name} ({int(mask.sum())})",
            linewidths=0,
        )

    ax.set_title(title)
    ax.set_xlabel("PC1")
    ax.set_ylabel("PC2")

    if legend and len(cluster_names) <= 30:
        ax.legend(loc="best", fontsize=8, frameon=False)

    fig.tight_layout()
    fig.savefig(out_file)
    plt.close(fig)


def plot_cluster_sizes(
    cluster_sizes: List[Tuple[str, int]],
    out_file: Path,
    title: str,
):
    out_file.parent.mkdir(parents=True, exist_ok=True)

    names = [x[0] for x in cluster_sizes]
    sizes = [x[1] for x in cluster_sizes]

    fig, ax = plt.subplots(figsize=(max(12, min(28, 0.35 * len(names))), 7), dpi=180)
    ax.bar(range(len(names)), sizes)
    ax.set_title(title)
    ax.set_ylabel("Count")
    ax.set_xticks(range(len(names)))
    ax.set_xticklabels(names, rotation=70, ha="right", fontsize=8)

    fig.tight_layout()
    fig.savefig(out_file)
    plt.close(fig)


def _collect_level_vectors(
    v2c: Dict[str, str],
    index: LoadedIndex,
) -> Tuple[np.ndarray, np.ndarray, List[str], int]:
    """Return (X, y, cluster_keys, missing_count) for a level."""
    cluster_keys = sorted(set(v2c.values()))
    cluster_key_to_id = {k: i for i, k in enumerate(cluster_keys)}

    vectors: List[np.ndarray] = []
    labels: List[int] = []
    missing = 0

    for vid, cluster_key in v2c.items():
        idx = index.id_to_idx.get(vid)
        if idx is None:
            missing += 1
            continue
        vectors.append(index.vectors[idx])
        labels.append(cluster_key_to_id[cluster_key])

    if not vectors:
        raise RuntimeError("No vectors matched between clustering results and index")

    X = np.asarray(vectors, dtype=np.float32)
    y = np.asarray(labels, dtype=np.int32)
    return X, y, cluster_keys, missing


def _render_level_plots(
    *,
    hierarchy: dict,
    index: LoadedIndex,
    level: int,
    outdir: Path,
    max_points: Optional[int],
    seed: int,
    legend: bool,
):
    v2c = _build_vector_to_cluster(hierarchy, level)
    if not v2c:
        raise RuntimeError(f"No vectors found in level_{level}")

    X, y, cluster_keys, missing = _collect_level_vectors(v2c, index)

    keep = _sample_indices(len(X), max_points, seed=seed)
    Xs = X[keep]
    ys = y[keep]

    pca = PCA(n_components=2, random_state=seed)
    xy = pca.fit_transform(Xs)

    title = f"Clustering scatter (level_{level}) | points={len(Xs)} | clusters={len(cluster_keys)}"
    if missing:
        title += f" | missing_vectors={missing}"

    plot_scatter(
        xy=xy,
        labels=ys,
        cluster_names=cluster_keys,
        out_file=outdir / f"scatter_level_{level}.png",
        title=title,
        legend=legend,
    )

    counts = np.bincount(y, minlength=len(cluster_keys))
    cluster_sizes = sorted(
        [(cluster_keys[i], int(counts[i])) for i in range(len(cluster_keys))],
        key=lambda x: x[1],
        reverse=True,
    )
    plot_cluster_sizes(
        cluster_sizes=cluster_sizes,
        out_file=outdir / f"cluster_sizes_level_{level}.png",
        title=f"Cluster sizes (level_{level}) | vectors={len(X)} | clusters={len(cluster_keys)}",
    )

    print(f"OK: wrote {outdir / f'scatter_level_{level}.png'}")
    print(f"OK: wrote {outdir / f'cluster_sizes_level_{level}.png'}")


def _plot_hierarchy_tree(hierarchy: dict, total_vectors: int, out_file: Path):
    """Plot parent-child structure across all levels.

    Notes:
    - Nodes are clusters (e.g., root_c0, root_c0_c1, ...)
    - Parent pointers come from clustering_results.json
    """

    # Build nodes
    levels = _available_levels(hierarchy)
    if not levels:
        raise RuntimeError("No level_* found in clustering results")

    parent_of: Dict[str, str] = {}
    size_of: Dict[str, int] = {"root": int(total_vectors)}
    depth_of: Dict[str, int] = {"root": -1}
    children_of: Dict[str, List[str]] = {"root": []}

    for lvl in levels:
        level_key = f"level_{lvl}"
        for node, info in (hierarchy.get(level_key) or {}).items():
            parent = info.get("parent")
            if not isinstance(parent, str) or not parent:
                parent = "root"

            parent_of[node] = parent
            size_of[node] = int(info.get("size") or 0)
            depth_of[node] = int(lvl)

            children_of.setdefault(node, [])
            children_of.setdefault(parent, []).append(node)

    for p, cs in children_of.items():
        cs.sort()

    # Leaves (no children) among cluster nodes
    all_nodes = sorted(set(["root", *parent_of.keys()]))
    leaves = [n for n in all_nodes if n != "root" and not children_of.get(n)]
    if not leaves:
        raise RuntimeError("Hierarchy tree has no leaves to layout")

    leaf_x: Dict[str, float] = {leaf: float(i) for i, leaf in enumerate(leaves)}
    x_of: Dict[str, float] = {}

    def compute_x(node: str) -> float:
        if node in x_of:
            return x_of[node]
        if node in leaf_x:
            x_of[node] = leaf_x[node]
            return x_of[node]
        kids = children_of.get(node) or []
        if not kids:
            # isolated node (should not happen often)
            x_of[node] = float(len(x_of))
            return x_of[node]
        xs = [compute_x(k) for k in kids]
        x_of[node] = float(sum(xs) / len(xs))
        return x_of[node]

    compute_x("root")

    # Positions
    max_depth = max([depth_of.get(n, -1) for n in all_nodes])
    pos: Dict[str, Tuple[float, float]] = {}
    for n in all_nodes:
        d = depth_of.get(n, -1)
        y = d + 1  # root at 0, level_0 at 1, ...
        pos[n] = (compute_x(n), float(y))

    out_file.parent.mkdir(parents=True, exist_ok=True)
    fig, ax = plt.subplots(figsize=(max(14, min(30, 0.25 * len(leaves))), 10), dpi=180)

    # Draw edges
    for child, parent in parent_of.items():
        if parent not in pos or child not in pos:
            continue
        x0, y0 = pos[parent]
        x1, y1 = pos[child]
        ax.plot([x0, x1], [y0, y1], color="black", alpha=0.25, linewidth=1)

    # Draw nodes
    nodes = all_nodes
    depths = np.array([depth_of.get(n, -1) + 1 for n in nodes], dtype=np.int32)
    sizes = np.array([size_of.get(n, 0) for n in nodes], dtype=np.float32)
    # scale bubble sizes
    bubble = 40.0 + 18.0 * np.sqrt(np.maximum(sizes, 1.0))

    cmap = plt.get_cmap("viridis", max_depth + 2)
    colors = ["#666666" if n == "root" else cmap(depths[i]) for i, n in enumerate(nodes)]
    xs = [pos[n][0] for n in nodes]
    ys = [pos[n][1] for n in nodes]

    ax.scatter(xs, ys, s=bubble, c=colors, alpha=0.9, linewidths=0.5, edgecolors="white")

    # Labels only when small enough
    if len(nodes) <= 60:
        for n in nodes:
            x, y = pos[n]
            ax.text(x, y, n, fontsize=7, ha="center", va="center")

    ax.set_title(f"Hierarchy tree | levels={len(levels)} | nodes={len(nodes)}")
    ax.set_xlabel("layout")
    ax.set_ylabel("depth (root -> deeper)")
    ax.set_yticks(list(range(0, max_depth + 2)))
    ax.set_yticklabels(["root"] + [f"level_{i}" for i in range(0, max_depth + 1)])
    ax.invert_yaxis()
    ax.grid(axis="y", alpha=0.15)
    ax.set_xticks([])

    fig.tight_layout()
    fig.savefig(out_file)
    plt.close(fig)

    print(f"OK: wrote {out_file}")


def main():
    parser = argparse.ArgumentParser(description="Generate PNGs to visualize clustering results")
    parser.add_argument(
        "--clusters",
        type=str,
        default=str(Path(__file__).parent / "clustering_results.json"),
        help="Path to clustering_results.json",
    )
    parser.add_argument(
        "--index-path",
        type=str,
        default=str(Path(__file__).parent / "vector_index"),
        help="Path to vector_index directory",
    )
    parser.add_argument(
        "--level",
        type=int,
        default=None,
        help="Which level_N to visualize (default: deepest level)",
    )
    parser.add_argument(
        "--all-levels",
        action="store_true",
        help="Render scatter/size plots for every available level",
    )
    parser.add_argument(
        "--tree",
        action="store_true",
        help="Render a hierarchy tree image using parent links",
    )
    parser.add_argument(
        "--outdir",
        type=str,
        default=str(Path(__file__).parent / "cluster_plots"),
        help="Output directory for PNGs",
    )
    parser.add_argument(
        "--max-points",
        type=int,
        default=0,
        help="Randomly subsample points for scatter (0 = no limit)",
    )
    parser.add_argument("--seed", type=int, default=42, help="Random seed")
    parser.add_argument("--legend", action="store_true", help="Show legend (only if clusters <= 30)")

    args = parser.parse_args()

    clusters_path = Path(args.clusters)
    index_path = Path(args.index_path)
    outdir = Path(args.outdir)

    results = _load_json(clusters_path)
    hierarchy = results.get("hierarchy") or {}
    total_vectors = int(results.get("total_vectors") or 0)

    levels = _available_levels(hierarchy)
    if not levels:
        raise RuntimeError("No level_* found in clustering results")

    index = _load_index(index_path)

    max_points = args.max_points if args.max_points and args.max_points > 0 else None

    if args.all_levels:
        for lvl in levels:
            _render_level_plots(
                hierarchy=hierarchy,
                index=index,
                level=lvl,
                outdir=outdir,
                max_points=max_points,
                seed=args.seed,
                legend=bool(args.legend),
            )
    else:
        level = args.level if args.level is not None else levels[-1]
        if level not in levels:
            raise ValueError(f"Level {level} not available. Available: {levels}")

        _render_level_plots(
            hierarchy=hierarchy,
            index=index,
            level=level,
            outdir=outdir,
            max_points=max_points,
            seed=args.seed,
            legend=bool(args.legend),
        )

    if args.tree:
        _plot_hierarchy_tree(
            hierarchy=hierarchy,
            total_vectors=total_vectors,
            out_file=outdir / "hierarchy_tree.png",
        )


if __name__ == "__main__":
    main()
