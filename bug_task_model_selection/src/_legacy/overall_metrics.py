from __future__ import annotations

import argparse
import json
from dataclasses import dataclass, asdict
from pathlib import Path

import numpy as np


def _iter_jsonl(path: Path):
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            s = line.strip()
            if not s:
                continue
            yield json.loads(s)


def _parse_named_paths(raw_list: list[str]) -> dict[str, Path]:
    out: dict[str, Path] = {}
    for raw in raw_list:
        s = str(raw).strip()
        if not s:
            continue
        if "=" not in s:
            raise ValueError(f"Expected name=path, got {s}")
        name, path = s.split("=", 1)
        name = name.strip()
        path = path.strip()
        if not name or not path:
            raise ValueError(f"Bad name=path: {s}")
        out[name] = Path(path)
    if not out:
        raise ValueError("No --ppl provided")
    return out


def load_slug_scores(path: Path) -> dict[str, float]:
    out: dict[str, float] = {}
    for obj in _iter_jsonl(path):
        slug = obj.get("slug")
        val = obj.get("value")
        if not isinstance(slug, str):
            continue
        if val is None:
            continue
        try:
            out[slug] = float(val)
        except Exception:
            continue
    return out


def load_assignments(path: Path) -> dict[str, int]:
    out: dict[str, int] = {}
    for obj in _iter_jsonl(path):
        item_id = obj.get("item_id")
        cid = obj.get("cluster_id")
        if not isinstance(item_id, str) or cid is None:
            continue
        try:
            out[item_id] = int(cid)
        except Exception:
            continue
    return out


def _slug_and_view_from_item_id(item_id: str) -> tuple[str, str | None]:
    if "__" not in item_id:
        return item_id, None
    slug, view = item_id.split("__", 1)
    return slug, view


def _basic_stats(values: list[float]) -> dict[str, float] | None:
    if not values:
        return None
    arr = np.asarray(values, dtype=np.float64)
    return {
        "n": float(arr.size),
        "mean": float(np.mean(arr)),
        "median": float(np.median(arr)),
        "std": float(np.std(arr)),
        "min": float(np.min(arr)),
        "max": float(np.max(arr)),
    }


@dataclass(frozen=True)
class OverallMetrics:
    n_slugs: int
    n_scored_slugs: dict[str, int]
    strategies: dict[str, dict]


def compute_overall_metrics(
    *,
    assignments_path: Path,
    cluster_choices_path: Path,
    ppl_by_name: dict[str, dict[str, float]],
    out_dir: Path,
    view: str | None,
) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)

    assignments = load_assignments(assignments_path)
    cluster_choices = json.loads(cluster_choices_path.read_text(encoding="utf-8"))

    names = list(ppl_by_name.keys())

    slug_to_cluster: dict[str, int] = {}
    for item_id, cid in assignments.items():
        slug, v = _slug_and_view_from_item_id(item_id)
        if view is not None and v is not None and v != view:
            continue
        if slug not in slug_to_cluster:
            slug_to_cluster[slug] = int(cid)

    strategies: dict[str, dict] = {}

    per_slug_out = out_dir / "per_slug_scores.jsonl"

    routed_scores: list[float] = []
    baseline_scores: dict[str, list[float]] = {n: [] for n in names}
    oracle_scores: list[float] = []

    n_scored: dict[str, int] = {"routed": 0, "oracle": 0, **{f"always_{n}": 0 for n in names}}

    with per_slug_out.open("w", encoding="utf-8") as f:
        for slug, cid in sorted(slug_to_cluster.items(), key=lambda x: x[0]):
            cid_key = str(int(cid))
            choice = cluster_choices.get(cid_key)
            chosen = choice.get("chosen") if isinstance(choice, dict) else None

            row: dict[str, object] = {
                "slug": slug,
                "cluster_id": int(cid),
                "chosen": chosen,
                "scores": {n: ppl_by_name[n].get(slug) for n in names},
            }

            oracle_val: float | None = None
            for n in names:
                v = ppl_by_name[n].get(slug)
                if v is None:
                    continue
                baseline_scores[n].append(float(v))
                n_scored[f"always_{n}"] += 1
                if oracle_val is None or float(v) < oracle_val:
                    oracle_val = float(v)

            if oracle_val is not None:
                oracle_scores.append(float(oracle_val))
                n_scored["oracle"] += 1

            routed_val: float | None = None
            if isinstance(chosen, str) and chosen in ppl_by_name:
                v = ppl_by_name[chosen].get(slug)
                if v is not None:
                    routed_val = float(v)

            if routed_val is not None:
                routed_scores.append(float(routed_val))
                n_scored["routed"] += 1

            row["oracle"] = oracle_val
            row["routed"] = routed_val
            f.write(json.dumps(row, ensure_ascii=False) + "\n")

    strategies["routed"] = {
        "stats": _basic_stats(routed_scores),
        "n": int(len(routed_scores)),
    }

    for n in names:
        strategies[f"always_{n}"] = {
            "stats": _basic_stats(baseline_scores[n]),
            "n": int(len(baseline_scores[n])),
        }

    strategies["oracle"] = {
        "stats": _basic_stats(oracle_scores),
        "n": int(len(oracle_scores)),
    }

    metrics = OverallMetrics(
        n_slugs=int(len(slug_to_cluster)),
        n_scored_slugs={k: int(v) for k, v in n_scored.items()},
        strategies=strategies,
    )

    out_path = out_dir / "overall_metrics.json"
    out_path.write_text(json.dumps(asdict(metrics), ensure_ascii=False, indent=2), encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Compute overall routed metrics vs baselines")
    p.add_argument("--assignments", type=str, required=True, help="assignments.jsonl (item_id -> cluster_id)")
    p.add_argument("--choices", type=str, required=True, help="cluster_choices.json from task_model_selector")
    p.add_argument("--ppl", action="append", default=[], help="name=path to aggregated ppl jsonl")
    p.add_argument("--outdir", type=str, required=True, help="Output directory")
    p.add_argument("--view", type=str, default=None, help="Optional view filter (e.g. report)")

    args = p.parse_args(argv)

    named = _parse_named_paths(list(args.ppl))
    ppl_by_name: dict[str, dict[str, float]] = {}
    for name, path in named.items():
        ppl_by_name[name] = load_slug_scores(path)

    compute_overall_metrics(
        assignments_path=Path(args.assignments),
        cluster_choices_path=Path(args.choices),
        ppl_by_name=ppl_by_name,
        out_dir=Path(args.outdir),
        view=(str(args.view) if args.view else None),
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
