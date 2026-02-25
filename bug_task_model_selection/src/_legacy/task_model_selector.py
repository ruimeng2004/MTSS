from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from pathlib import Path

import numpy as np


@dataclass(frozen=True)
class ClusterChoice:
    cluster_id: int
    chosen: str
    votes: dict[str, int]
    mean_scores: dict[str, float]
    n_reps_used: int


def _iter_jsonl(path: Path):
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            s = line.strip()
            if not s:
                continue
            yield json.loads(s)


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


def select_clusters(
    *,
    representatives_path: Path,
    ppl_by_name: dict[str, dict[str, float]],
    out_dir: Path,
    default_choice: str | None,
) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)

    clusters: dict[int, list[dict]] = {}
    for obj in _iter_jsonl(representatives_path):
        if obj.get("rank") != 1:
            continue
        cid = obj.get("cluster_id")
        slug = obj.get("slug")
        if cid is None or not isinstance(slug, str):
            continue
        clusters.setdefault(int(cid), []).append(obj)

    names = list(ppl_by_name.keys())

    item_out = out_dir / "rep_item_choices.jsonl"
    cluster_out = out_dir / "cluster_choices.json"

    cluster_choices: dict[str, dict] = {}

    with item_out.open("w", encoding="utf-8") as f:
        for cluster_id in sorted(clusters.keys()):
            reps = clusters[cluster_id]

            votes: dict[str, int] = {n: 0 for n in names}
            score_lists: dict[str, list[float]] = {n: [] for n in names}

            for rep in reps:
                slug = str(rep.get("slug"))

                best_name: str | None = None
                best_score: float | None = None

                for n in names:
                    v = ppl_by_name[n].get(slug)
                    if v is None:
                        continue
                    score_lists[n].append(float(v))
                    if best_score is None or float(v) < best_score:
                        best_score = float(v)
                        best_name = n

                if best_name is not None:
                    votes[best_name] += 1

                f.write(
                    json.dumps(
                        {
                            "cluster_id": int(cluster_id),
                            "item_id": rep.get("item_id"),
                            "slug": slug,
                            "chosen": best_name,
                            "scores": {n: ppl_by_name[n].get(slug) for n in names},
                        },
                        ensure_ascii=False,
                    )
                    + "\n"
                )

            max_votes = max(votes.values()) if votes else 0
            candidates = [n for n, c in votes.items() if c == max_votes]

            mean_scores: dict[str, float] = {}
            for n in names:
                if score_lists[n]:
                    mean_scores[n] = float(np.mean(np.asarray(score_lists[n], dtype=np.float64)))

            chosen: str
            if len(candidates) == 1:
                chosen = candidates[0]
            else:
                scored = [(n, mean_scores.get(n)) for n in candidates]
                scored_present = [(n, v) for (n, v) in scored if v is not None]
                if scored_present:
                    chosen = min(scored_present, key=lambda x: x[1])[0]
                else:
                    chosen = default_choice if default_choice is not None else sorted(names)[0]

            cluster_choices[str(int(cluster_id))] = {
                "cluster_id": int(cluster_id),
                "chosen": chosen,
                "votes": votes,
                "mean_scores": mean_scores,
                "n_reps_used": int(len(reps)),
            }

    with cluster_out.open("w", encoding="utf-8") as f:
        json.dump(cluster_choices, f, ensure_ascii=False, indent=2)


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Cluster-level task-modeling selection from representatives + PPL aggregates")
    p.add_argument("--representatives", type=str, required=True, help="representatives.jsonl from cluster_representatives")
    p.add_argument("--ppl", action="append", default=[], help="name=path to aggregated ppl jsonl")
    p.add_argument("--outdir", type=str, required=True, help="Output directory")
    p.add_argument("--default", type=str, default=None, help="Default choice if all scores missing")

    args = p.parse_args(argv)

    named = _parse_named_paths(list(args.ppl))
    ppl_by_name: dict[str, dict[str, float]] = {}
    for name, path in named.items():
        ppl_by_name[name] = load_slug_scores(path)

    default_choice = str(args.default) if args.default is not None else None
    if default_choice is not None and default_choice not in ppl_by_name:
        raise ValueError(f"--default must be one of {list(ppl_by_name.keys())}, got {default_choice}")

    select_clusters(
        representatives_path=Path(args.representatives),
        ppl_by_name=ppl_by_name,
        out_dir=Path(args.outdir),
        default_choice=default_choice,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
