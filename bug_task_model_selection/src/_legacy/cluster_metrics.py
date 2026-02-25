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
class ClusterMetrics:
    cluster_id: int
    n_items: int
    n_scored_items: dict[str, int]
    missing_items: dict[str, int]
    missing_rate: dict[str, float]
    stats: dict[str, dict]
    deltas: dict[str, dict]
    chosen: str | None = None
    chosen_votes: dict[str, int] | None = None
    chosen_mean_scores: dict[str, float] | None = None


def compute_cluster_metrics(
    *,
    representatives_path: Path,
    ppl_by_name: dict[str, dict[str, float]],
    out_dir: Path,
    only_rank1: bool,
    choices_path: Path | None,
) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)

    clusters: dict[int, list[dict]] = {}
    for obj in _iter_jsonl(representatives_path):
        if only_rank1 and obj.get("rank") != 1:
            continue
        cid = obj.get("cluster_id")
        slug = obj.get("slug")
        if cid is None or not isinstance(slug, str):
            continue
        clusters.setdefault(int(cid), []).append(obj)

    choices: dict[str, dict] = {}
    if choices_path is not None and choices_path.exists():
        choices = json.loads(choices_path.read_text(encoding="utf-8"))

    names = list(ppl_by_name.keys())

    per_item_path = out_dir / "cluster_items_scored.jsonl"
    per_cluster_path = out_dir / "cluster_metrics.json"

    cluster_metrics: dict[str, dict] = {}

    with per_item_path.open("w", encoding="utf-8") as outf:
        for cluster_id in sorted(clusters.keys()):
            items = clusters[cluster_id]
            n_items = len(items)

            values_by_name: dict[str, list[float]] = {n: [] for n in names}
            missing_by_name: dict[str, int] = {n: 0 for n in names}

            for it in items:
                slug = str(it.get("slug"))
                scores: dict[str, float | None] = {}
                for n in names:
                    v = ppl_by_name[n].get(slug)
                    scores[n] = float(v) if v is not None else None
                    if v is None:
                        missing_by_name[n] += 1
                    else:
                        values_by_name[n].append(float(v))

                outf.write(
                    json.dumps(
                        {
                            "cluster_id": int(cluster_id),
                            "item_id": it.get("item_id"),
                            "slug": slug,
                            "rank": it.get("rank"),
                            "scores": scores,
                        },
                        ensure_ascii=False,
                    )
                    + "\n"
                )

            stats: dict[str, dict] = {}
            for n in names:
                st = _basic_stats(values_by_name[n])
                if st is not None:
                    stats[n] = st

            deltas: dict[str, dict] = {}
            for i in range(len(names)):
                for j in range(i + 1, len(names)):
                    a = names[i]
                    b = names[j]
                    key = f"{a}-{b}"

                    # Compute delta per-item when both present (align by slug).
                    deltas_list: list[float] = []
                    for it in items:
                        slug = str(it.get("slug"))
                        va = ppl_by_name[a].get(slug)
                        vb = ppl_by_name[b].get(slug)
                        if va is None or vb is None:
                            continue
                        deltas_list.append(float(va) - float(vb))

                    st = _basic_stats(deltas_list)
                    if st is not None:
                        deltas[key] = st

            missing_rate = {
                n: (float(missing_by_name[n]) / float(n_items) if n_items > 0 else 1.0) for n in names
            }

            choice = choices.get(str(int(cluster_id))) if choices else None
            cm = ClusterMetrics(
                cluster_id=int(cluster_id),
                n_items=int(n_items),
                n_scored_items={n: int(len(values_by_name[n])) for n in names},
                missing_items={n: int(missing_by_name[n]) for n in names},
                missing_rate={n: float(missing_rate[n]) for n in names},
                stats=stats,
                deltas=deltas,
                chosen=str(choice.get("chosen")) if isinstance(choice, dict) and choice.get("chosen") is not None else None,
                chosen_votes=choice.get("votes") if isinstance(choice, dict) else None,
                chosen_mean_scores=choice.get("mean_scores") if isinstance(choice, dict) else None,
            )

            cluster_metrics[str(int(cluster_id))] = asdict(cm)

    with per_cluster_path.open("w", encoding="utf-8") as f:
        json.dump(
            {
                "only_rank1": bool(only_rank1),
                "ppl_names": names,
                "clusters": cluster_metrics,
            },
            f,
            ensure_ascii=False,
            indent=2,
        )


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Compute cluster-level metrics from representatives + aggregated PPL")
    p.add_argument("--representatives", type=str, required=True, help="representatives.jsonl")
    p.add_argument("--ppl", action="append", default=[], help="name=path to aggregated ppl jsonl")
    p.add_argument("--outdir", type=str, required=True, help="Output directory")
    p.add_argument("--use-all-reps", action="store_true", help="Use all representatives (not only rank==1)")
    p.add_argument("--choices", type=str, default=None, help="Optional cluster_choices.json from task_model_selector")

    args = p.parse_args(argv)

    named = _parse_named_paths(list(args.ppl))
    ppl_by_name: dict[str, dict[str, float]] = {}
    for name, path in named.items():
        ppl_by_name[name] = load_slug_scores(path)

    compute_cluster_metrics(
        representatives_path=Path(args.representatives),
        ppl_by_name=ppl_by_name,
        out_dir=Path(args.outdir),
        only_rank1=(not bool(args.use_all_reps)),
        choices_path=(Path(args.choices) if args.choices else None),
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
