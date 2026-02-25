"""Export per-cluster JSONs for each hierarchy level.

This script merges:
- Full cluster membership from `D4C/embedding/clustering_results.json`
- Representative points selected by DPP from `D4C/dpp/result/level_N/selected.json`
- Dense vectors from `D4C/embedding/vector_index/vectors.npy`

Output layout (default):
  D4C/dpp/result_cluster/
    level_0/
      root_c0.json
      ...
    level_1/
      root_c0_c0.json
      ...
    level_2/
      root_c0_c0_c0.json
      ...

Each cluster json includes:
- cluster_key / cluster_id / level
- points: all members, each with vector
- representatives: ids selected by DPP for that cluster

Note: vectors are duplicated across levels by design (as requested).
"""

from __future__ import annotations

import argparse
import json
import pickle
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Tuple

import numpy as np


@dataclass(frozen=True)
class Paths:
    clustering_results: Path
    vector_index_dir: Path
    dpp_result_dir: Path
    out_dir: Path


def _load_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def _dump_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, separators=(",", ":"))


def _load_vector_index(vector_index_dir: Path) -> Tuple[np.ndarray, Mapping[str, int]]:
    vectors_path = vector_index_dir / "vectors.npy"
    mapping_path = vector_index_dir / "id_mapping.pkl"

    vectors = np.load(vectors_path)

    with mapping_path.open("rb") as f:
        mapping_obj = pickle.load(f)

    if not isinstance(mapping_obj, dict) or "id_to_idx" not in mapping_obj:
        raise ValueError(f"Unexpected id_mapping.pkl format: {mapping_path}")

    id_to_idx = mapping_obj["id_to_idx"]
    if not isinstance(id_to_idx, dict):
        raise ValueError(f"Unexpected id_to_idx type in {mapping_path}: {type(id_to_idx)}")

    return vectors, id_to_idx


def _load_representatives(selected_json_path: Path) -> Dict[str, List[str]]:
    """Return mapping cluster_key -> representative ids (ordered by rank_in_cluster)."""
    obj = _load_json(selected_json_path)
    selected = obj.get("selected")
    if not isinstance(selected, list):
        raise ValueError(f"Bad selected.json (missing list 'selected'): {selected_json_path}")

    # Keep stable order; also handle the case where the same cluster has multiple picks.
    reps: Dict[str, List[Tuple[int, str]]] = defaultdict(list)
    for item in selected:
        if not isinstance(item, dict):
            continue
        cluster_key = item.get("cluster_key")
        point_id = item.get("id")
        rank = item.get("rank_in_cluster")
        if not isinstance(cluster_key, str) or not isinstance(point_id, str):
            continue
        if not isinstance(rank, int):
            rank = 10**9
        reps[cluster_key].append((rank, point_id))

    out: Dict[str, List[str]] = {}
    for ck, pairs in reps.items():
        pairs.sort(key=lambda x: x[0])
        out[ck] = [pid for _, pid in pairs]
    return out


def _iter_level_clusters(hierarchy_level: Mapping[str, Any]) -> Iterable[Tuple[str, Mapping[str, Any]]]:
    for cluster_key, payload in hierarchy_level.items():
        if not isinstance(cluster_key, str) or not isinstance(payload, dict):
            continue
        yield cluster_key, payload


def _vector_to_jsonable(vec: np.ndarray) -> List[float]:
    # Ensure plain Python floats for JSON.
    return [float(x) for x in vec.tolist()]


def export_level(
    *,
    level: int,
    hierarchy_obj: Mapping[str, Any],
    vectors: np.ndarray,
    id_to_idx: Mapping[str, int],
    representatives: Mapping[str, List[str]],
    out_dir: Path,
) -> Tuple[int, int, int]:
    """Export all clusters for one level.

    Returns: (clusters_written, points_written, missing_vectors)
    """

    level_key = f"level_{level}"
    level_obj = hierarchy_obj.get(level_key)
    if not isinstance(level_obj, dict):
        raise ValueError(f"clustering_results missing hierarchy.{level_key}")

    clusters_written = 0
    points_written = 0
    missing_vectors = 0

    for cluster_key, payload in _iter_level_clusters(level_obj):
        cluster_id = payload.get("cluster_id")
        cluster_size = payload.get("size")
        members = payload.get("vectors")

        if not isinstance(members, list):
            # Some clusters might be empty or malformed; skip.
            continue

        points: List[Dict[str, Any]] = []
        for m in members:
            if not isinstance(m, dict):
                continue
            point_id = m.get("id")
            if not isinstance(point_id, str):
                continue
            idx = id_to_idx.get(point_id)
            if idx is None:
                missing_vectors += 1
                vec_json = None
            else:
                vec_json = _vector_to_jsonable(vectors[idx])

            points.append(
                {
                    "id": point_id,
                    "folder": m.get("folder"),
                    "file": m.get("file"),
                    "tokens": m.get("tokens"),
                    "vector": vec_json,
                }
            )

        reps = representatives.get(cluster_key, [])

        out_obj = {
            "level": level,
            "cluster_key": cluster_key,
            "cluster_id": cluster_id,
            "size": cluster_size if isinstance(cluster_size, int) else len(points),
            "points": points,
            "representatives": reps,
        }

        out_path = out_dir / f"level_{level}" / f"{cluster_key}.json"
        _dump_json(out_path, out_obj)

        clusters_written += 1
        points_written += len(points)

    return clusters_written, points_written, missing_vectors


def main() -> None:
    parser = argparse.ArgumentParser(description="Export per-cluster JSONs for each level")
    parser.add_argument(
        "--clustering-results",
        default="D4C/embedding/clustering_results.json",
        help="Path to clustering_results.json",
    )
    parser.add_argument(
        "--vector-index-dir",
        default="D4C/embedding/vector_index",
        help="Directory containing vectors.npy and id_mapping.pkl",
    )
    parser.add_argument(
        "--dpp-result-dir",
        default="D4C/dpp/result",
        help="Directory containing level_N/selected.json",
    )
    parser.add_argument(
        "--out-dir",
        default="D4C/dpp/result_cluster",
        help="Output directory",
    )
    parser.add_argument(
        "--levels",
        default="0,1,2",
        help="Comma-separated levels to export (default: 0,1,2)",
    )

    args = parser.parse_args()

    paths = Paths(
        clustering_results=Path(args.clustering_results),
        vector_index_dir=Path(args.vector_index_dir),
        dpp_result_dir=Path(args.dpp_result_dir),
        out_dir=Path(args.out_dir),
    )

    levels = [int(x.strip()) for x in str(args.levels).split(",") if x.strip()]

    clustering = _load_json(paths.clustering_results)
    hierarchy = clustering.get("hierarchy")
    if not isinstance(hierarchy, dict):
        raise ValueError("clustering_results.json missing 'hierarchy'")

    vectors, id_to_idx = _load_vector_index(paths.vector_index_dir)

    overall = {
        "created_from": {
            "clustering_results": str(paths.clustering_results),
            "vector_index_dir": str(paths.vector_index_dir),
            "dpp_result_dir": str(paths.dpp_result_dir),
        },
        "levels": {},
    }

    for level in levels:
        selected_json_path = paths.dpp_result_dir / f"level_{level}" / "selected.json"
        reps = _load_representatives(selected_json_path)

        c_written, p_written, missing = export_level(
            level=level,
            hierarchy_obj=hierarchy,
            vectors=vectors,
            id_to_idx=id_to_idx,
            representatives=reps,
            out_dir=paths.out_dir,
        )

        overall["levels"][str(level)] = {
            "clusters_written": c_written,
            "points_written": p_written,
            "missing_vectors": missing,
            "out_dir": str(paths.out_dir / f"level_{level}"),
        }

    _dump_json(paths.out_dir / "export_summary.json", overall)


if __name__ == "__main__":
    main()
