#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""Select per-cluster modeling strategy (SR vs GEN) based on representative points,
then apply the chosen strategy to all points in each cluster.

Inputs:
- Cluster JSON files produced by D4C/dpp/result_cluster/level_{0,1,2}
- Eval CSV for GEN and SR: columns [ID, slug, reward, submission_result]
- Pred CSV for GEN: columns [ID, lang, slug, bug, diff, fix]

Outputs (per level):
- CSV of per-point selected model and whether it is fixed under that model
- CSV summary per cluster

Notes:
- "Fixed" is defined as any attempt with reward == True for that slug.
- Success count is number of attempts with reward == True for that slug.
- Representative ids are like "Chart_1_query"; slug is derived as "Chart_1".
"""

from __future__ import annotations

import argparse
import csv
import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Sequence, Tuple


@dataclass(frozen=True)
class EvalStats:
    attempts: int
    successes: int

    @property
    def is_fixed(self) -> bool:
        return self.successes > 0


def _slug_from_point_id(point_id: str) -> str:
    # Most cluster points use "<slug>_query".
    suffix = "_query"
    if point_id.endswith(suffix):
        return point_id[: -len(suffix)]
    return point_id


def load_eval_stats(eval_csv: Path) -> Dict[str, EvalStats]:
    """Return per-slug (attempts, successes) from eval CSV."""
    attempts: Dict[str, int] = {}
    successes: Dict[str, int] = {}

    with eval_csv.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        required = {"slug", "reward"}
        missing = required - set(reader.fieldnames or [])
        if missing:
            raise ValueError(f"{eval_csv} missing columns: {sorted(missing)}")

        for row in reader:
            slug = (row.get("slug") or "").strip()
            if not slug:
                continue
            attempts[slug] = attempts.get(slug, 0) + 1
            reward = (row.get("reward") or "").strip().lower()
            if reward == "true":
                successes[slug] = successes.get(slug, 0) + 1

    out: Dict[str, EvalStats] = {}
    for slug, n in attempts.items():
        out[slug] = EvalStats(attempts=n, successes=successes.get(slug, 0))
    return out


def load_gen_pred_first_rows(pred_csv: Path, wanted_slugs: Sequence[str]) -> Dict[str, Dict[str, str]]:
    """Stream GEN pred CSV and capture the first row per wanted slug.

    The pred CSV in this workspace does not appear to carry a stable "try index" that
    can be joined with eval rows. Therefore we attach an arbitrary (first-seen) patch
    for each slug when we need to show the model output.
    """
    wanted = set(wanted_slugs)
    found: Dict[str, Dict[str, str]] = {}
    if not wanted:
        return found

    with pred_csv.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        required = {"slug"}
        missing = required - set(reader.fieldnames or [])
        if missing:
            raise ValueError(f"{pred_csv} missing columns: {sorted(missing)}")
        for row in reader:
            slug = (row.get("slug") or "").strip()
            if not slug or slug not in wanted or slug in found:
                continue
            found[slug] = row
            if len(found) >= len(wanted):
                break
    return found


def iter_cluster_files(cluster_root: Path, levels: Sequence[int]) -> Iterable[Tuple[int, Path]]:
    for level in levels:
        level_dir = cluster_root / f"level_{level}"
        if not level_dir.exists():
            continue
        for p in sorted(level_dir.glob("*.json")):
            yield level, p


def read_cluster(cluster_json: Path) -> Tuple[str, List[str], List[str]]:
    """Return (cluster_key, representative_point_ids, all_point_ids)."""
    with cluster_json.open("r", encoding="utf-8") as f:
        obj = json.load(f)
    cluster_key = obj.get("cluster_key") or cluster_json.stem
    reps = list(obj.get("representatives") or [])
    points = obj.get("points") or []
    point_ids = [p.get("id") for p in points if isinstance(p, dict) and p.get("id")]
    return cluster_key, reps, point_ids


def choose_model_for_cluster(
    rep_ids: Sequence[str],
    gen_eval: Dict[str, EvalStats],
    sr_eval: Dict[str, EvalStats],
) -> Tuple[str, str]:
    """Return (chosen_model, reason).

    Logic:
    - Determine whether representative is fixable by SR/GEN (any success).
    - If only one can fix -> choose it.
    - If both can fix -> choose the one with more successes (on representative slug).
    - If tie -> prefer SR (stable default).
    - If none can fix -> choose GEN (default) but mark reason.

    If multiple representatives exist, we aggregate over them:
    - A model is "can fix" if it fixes ANY representative.
    - Success count is sum of successes across representatives.
    """
    rep_slugs = [_slug_from_point_id(r) for r in rep_ids] if rep_ids else []

    gen_can = False
    sr_can = False
    gen_succ = 0
    sr_succ = 0

    for slug in rep_slugs:
        g = gen_eval.get(slug, EvalStats(0, 0))
        s = sr_eval.get(slug, EvalStats(0, 0))
        gen_can = gen_can or g.is_fixed
        sr_can = sr_can or s.is_fixed
        gen_succ += g.successes
        sr_succ += s.successes

    if sr_can and not gen_can:
        return "sr", "rep_fixed_by_sr_only"
    if gen_can and not sr_can:
        return "gen", "rep_fixed_by_gen_only"
    if gen_can and sr_can:
        if sr_succ > gen_succ:
            return "sr", f"both_fix_rep_sr_more_success({sr_succ}>{gen_succ})"
        if gen_succ > sr_succ:
            return "gen", f"both_fix_rep_gen_more_success({gen_succ}>{sr_succ})"
        return "sr", f"both_fix_rep_tie_success({sr_succ}=={gen_succ})"

    # none fixed
    return "gen", "rep_not_fixed_by_either_default_gen"


def point_fixed_under(model: str, slug: str, gen_eval: Dict[str, EvalStats], sr_eval: Dict[str, EvalStats]) -> Tuple[bool, int, int]:
    if model == "sr":
        st = sr_eval.get(slug, EvalStats(0, 0))
        return st.is_fixed, st.successes, st.attempts
    st = gen_eval.get(slug, EvalStats(0, 0))
    return st.is_fixed, st.successes, st.attempts


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--cluster-root", type=Path, default=Path("D4C/dpp/result_cluster"))
    ap.add_argument("--levels", type=str, default="0,1,2", help="comma-separated levels")
    ap.add_argument("--gen-eval", type=Path, required=True)
    ap.add_argument("--sr-eval", type=Path, required=True)
    ap.add_argument("--gen-pred", type=Path, required=False, help="optional; used to attach diff/fix for fixed points")
    ap.add_argument("--out-dir", type=Path, default=Path("D4C/fix/cluster_model_selector_out"))
    args = ap.parse_args()

    levels = [int(x.strip()) for x in args.levels.split(",") if x.strip()]

    gen_eval = load_eval_stats(args.gen_eval)
    sr_eval = load_eval_stats(args.sr_eval)

    gen_pred = None
    if args.gen_pred:
        gen_pred = args.gen_pred

    args.out_dir.mkdir(parents=True, exist_ok=True)

    # Pass 1: read clusters, decide model, and collect point rows in-memory.
    # Enforce per-level uniqueness: a point_id (bug) should belong to at most one cluster.
    cluster_rows_by_level: Dict[int, List[Dict[str, str]]] = {lvl: [] for lvl in levels}
    point_rows_by_level: Dict[int, List[Dict[str, str]]] = {lvl: [] for lvl in levels}
    needed_gen_slugs: set[str] = set()
    assigned_cluster_by_level: Dict[int, Dict[str, str]] = {lvl: {} for lvl in levels}
    duplicates_by_level: Dict[int, List[Dict[str, str]]] = {lvl: [] for lvl in levels}

    for level, cluster_file in iter_cluster_files(args.cluster_root, levels):
        cluster_key, reps, point_ids = read_cluster(cluster_file)
        chosen_model, reason = choose_model_for_cluster(reps, gen_eval, sr_eval)

        rep_slugs = [_slug_from_point_id(r) for r in reps]
        rep_gen_succ = sum(gen_eval.get(s, EvalStats(0, 0)).successes for s in rep_slugs)
        rep_sr_succ = sum(sr_eval.get(s, EvalStats(0, 0)).successes for s in rep_slugs)

        # Deduplicate points within the same level: keep the first cluster that claims the point.
        unique_point_ids: List[str] = []
        assigned = assigned_cluster_by_level[level]
        for pid in point_ids:
            prev_cluster = assigned.get(pid)
            if prev_cluster is not None and prev_cluster != cluster_key:
                duplicates_by_level[level].append(
                    {
                        "level": str(level),
                        "point_id": pid,
                        "slug": _slug_from_point_id(pid),
                        "kept_cluster": prev_cluster,
                        "dropped_cluster": cluster_key,
                        "dropped_cluster_file": str(cluster_file),
                    }
                )
                continue
            if prev_cluster is None:
                assigned[pid] = cluster_key
            unique_point_ids.append(pid)

        # Skip empty clusters after de-duplication.
        if not unique_point_ids:
            continue

        cluster_rows_by_level[level].append(
            {
                "level": str(level),
                "cluster_key": cluster_key,
                "cluster_file": str(cluster_file),
                "size_raw": str(len(point_ids)),
                "size_unique": str(len(unique_point_ids)),
                "representatives": "|".join(reps),
                "chosen_model": chosen_model,
                "reason": reason,
                "rep_gen_successes": str(rep_gen_succ),
                "rep_sr_successes": str(rep_sr_succ),
            }
        )

        for pid in unique_point_ids:
            slug = _slug_from_point_id(pid)
            fixed, succ, attempts = point_fixed_under(chosen_model, slug, gen_eval, sr_eval)
            if chosen_model == "gen" and fixed and gen_pred is not None:
                needed_gen_slugs.add(slug)
            point_rows_by_level[level].append(
                {
                    "level": str(level),
                    "cluster_key": cluster_key,
                    "point_id": pid,
                    "slug": slug,
                    "chosen_model": chosen_model,
                    "fixed": "1" if fixed else "0",
                    "successes": str(succ),
                    "attempts": str(attempts),
                    "gen_diff": "",
                    "gen_fix": "",
                }
            )

    # Pass 2: fetch GEN outputs for slugs we actually need.
    gen_first_rows: Dict[str, Dict[str, str]] = {}
    if gen_pred is not None and needed_gen_slugs:
        gen_first_rows = load_gen_pred_first_rows(gen_pred, sorted(needed_gen_slugs))

    # Pass 3: write per-level outputs.
    for level in levels:
        cluster_summary_path = args.out_dir / f"level_{level}_clusters.csv"
        point_out_path = args.out_dir / f"level_{level}_points.csv"
        fixed_out_path = args.out_dir / f"level_{level}_fixed.csv"
        dup_out_path = args.out_dir / f"level_{level}_duplicates.csv"

        cluster_rows = cluster_rows_by_level.get(level, [])
        point_rows = point_rows_by_level.get(level, [])

        if cluster_rows:
            with cluster_summary_path.open("w", newline="", encoding="utf-8") as f:
                w = csv.DictWriter(f, fieldnames=list(cluster_rows[0].keys()))
                w.writeheader()
                w.writerows(cluster_rows)
        else:
            cluster_summary_path.write_text("", encoding="utf-8")

        if point_rows:
            for r in point_rows:
                if r["chosen_model"] == "gen" and r["fixed"] == "1":
                    prow = gen_first_rows.get(r["slug"])
                    if prow:
                        r["gen_diff"] = prow.get("diff") or ""
                        r["gen_fix"] = prow.get("fix") or ""

            with point_out_path.open("w", newline="", encoding="utf-8") as f:
                w = csv.DictWriter(f, fieldnames=list(point_rows[0].keys()))
                w.writeheader()
                w.writerows(point_rows)
        else:
            point_out_path.write_text("", encoding="utf-8")

        fixed_rows = [
            {
                "level": r["level"],
                "cluster_key": r["cluster_key"],
                "slug": r["slug"],
                "chosen_model": r["chosen_model"],
                "successes": r["successes"],
                "attempts": r["attempts"],
            }
            for r in point_rows
            if r.get("fixed") == "1"
        ]
        if fixed_rows:
            with fixed_out_path.open("w", newline="", encoding="utf-8") as f:
                w = csv.DictWriter(f, fieldnames=list(fixed_rows[0].keys()))
                w.writeheader()
                w.writerows(fixed_rows)
        else:
            fixed_out_path.write_text("", encoding="utf-8")

        dup_rows = duplicates_by_level.get(level, [])
        if dup_rows:
            with dup_out_path.open("w", newline="", encoding="utf-8") as f:
                w = csv.DictWriter(f, fieldnames=list(dup_rows[0].keys()))
                w.writeheader()
                w.writerows(dup_rows)
        else:
            dup_out_path.write_text("", encoding="utf-8")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
