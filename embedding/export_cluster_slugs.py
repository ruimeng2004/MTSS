"""Export hierarchical clustering results into per-level JSON files.

Input:
- clustering_results.json produced by `hierarchical_clustering.py`

Output (by default):
- cluster_exports/level_0.json
- cluster_exports/level_1.json
- ...

Each level file contains clusters with their parent, size, and the list/counts of slugs
(derived from the vector metadata field `folder`, e.g. `Chart_1` -> `chart_1`).
"""

from __future__ import annotations

import argparse
import json
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional


@dataclass(frozen=True)
class ExportOptions:
    slug_field: str = "folder"
    slug_lower: bool = True


def _load_json(path: Path) -> Dict[str, Any]:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _dump_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def _available_levels(hierarchy: Dict[str, Any]) -> List[int]:
    levels: List[int] = []
    for key in hierarchy.keys():
        if key.startswith("level_"):
            suffix = key.split("_", 1)[1]
            try:
                levels.append(int(suffix))
            except ValueError:
                continue
    return sorted(set(levels))


def _to_slug(value: Optional[str], *, lower: bool) -> str:
    if not value:
        return "unknown"
    return value.lower() if lower else value


def export_levels(
    *,
    results: Dict[str, Any],
    outdir: Path,
    options: ExportOptions,
) -> List[Path]:
    hierarchy = results.get("hierarchy") or {}
    total_vectors = int(results.get("total_vectors") or 0)

    levels = _available_levels(hierarchy)
    if not levels:
        raise RuntimeError("No level_* found in clustering results")

    written: List[Path] = []

    for lvl in levels:
        level_key = f"level_{lvl}"
        level_data: Dict[str, Any] = hierarchy.get(level_key) or {}

        clusters_out: List[Dict[str, Any]] = []
        vectors_seen = 0

        for cluster_key, cluster_info in level_data.items():
            vectors_meta = cluster_info.get("vectors") or []
            vectors_seen += len(vectors_meta)

            slug_counts: Counter[str] = Counter()
            for meta in vectors_meta:
                raw = meta.get(options.slug_field)
                slug_counts[_to_slug(raw, lower=options.slug_lower)] += 1

            clusters_out.append(
                {
                    "cluster": cluster_key,
                    "parent": cluster_info.get("parent"),
                    "size": int(cluster_info.get("size") or len(vectors_meta)),
                    "slugs": sorted(slug_counts.keys()),
                    "slug_counts": dict(sorted(slug_counts.items(), key=lambda x: (-x[1], x[0]))),
                }
            )

        clusters_out.sort(key=lambda c: (-int(c.get("size") or 0), str(c.get("cluster"))))

        level_out = {
            "level": lvl,
            "level_key": level_key,
            "total_vectors": total_vectors,
            "clusters": clusters_out,
            "num_clusters": len(clusters_out),
            "vectors_in_level": vectors_seen,
            "slug_field": options.slug_field,
            "slug_lower": options.slug_lower,
        }

        out_path = outdir / f"{level_key}.json"
        _dump_json(out_path, level_out)
        written.append(out_path)

    return written


def main() -> None:
    parser = argparse.ArgumentParser(description="Export per-level cluster -> slug mapping JSONs")
    parser.add_argument(
        "--input",
        type=str,
        default=str(Path(__file__).parent / "clustering_results.json"),
        help="Path to clustering_results.json",
    )
    parser.add_argument(
        "--outdir",
        type=str,
        default=str(Path(__file__).parent / "cluster_exports"),
        help="Output directory (one JSON per level)",
    )
    parser.add_argument(
        "--slug-field",
        type=str,
        default="folder",
        help="Vector metadata field to treat as slug source (default: folder)",
    )
    parser.add_argument(
        "--no-lower",
        action="store_true",
        help="Do not lowercase slugs",
    )

    args = parser.parse_args()

    results = _load_json(Path(args.input))
    written = export_levels(
        results=results,
        outdir=Path(args.outdir),
        options=ExportOptions(slug_field=args.slug_field, slug_lower=not args.no_lower),
    )

    for p in written:
        print(f"OK: wrote {p}")


if __name__ == "__main__":
    main()
