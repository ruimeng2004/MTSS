from __future__ import annotations

import argparse
import json
from dataclasses import dataclass, asdict
from pathlib import Path

import numpy as np


@dataclass(frozen=True)
class SlugPplAgg:
    run_ts: str
    slug: str
    metric: str
    agg: str
    value: float
    n: int


def _iter_jsonl(path: Path):
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            s = line.strip()
            if not s:
                continue
            yield json.loads(s)


def _choose_metric_value(obj: dict, *, prefer_io: bool) -> float | None:
    if prefer_io:
        v = obj.get("ppl_io")
        if v is not None:
            try:
                return float(v)
            except Exception:
                pass
    v = obj.get("ppl")
    if v is not None:
        try:
            return float(v)
        except Exception:
            return None
    return None


def aggregate_by_slug(
    *,
    records_path: Path,
    out_path: Path,
    agg: str = "median",
    prefer_io: bool = True,
) -> int:
    groups: dict[tuple[str, str], list[float]] = {}

    for obj in _iter_jsonl(records_path):
        run_ts = str(obj.get("run_ts") or "")
        slug = str(obj.get("slug") or "")
        if not run_ts or not slug:
            continue
        v = _choose_metric_value(obj, prefer_io=prefer_io)
        if v is None:
            continue
        groups.setdefault((run_ts, slug), []).append(float(v))

    out_path.parent.mkdir(parents=True, exist_ok=True)
    n = 0

    metric = "ppl_io" if prefer_io else "ppl"
    with out_path.open("w", encoding="utf-8") as f:
        for (run_ts, slug), vals in sorted(groups.items(), key=lambda x: (x[0][0], x[0][1])):
            arr = np.asarray(vals, dtype=np.float64)
            if arr.size == 0:
                continue
            if agg == "median":
                value = float(np.median(arr))
            elif agg == "mean":
                value = float(np.mean(arr))
            else:
                raise ValueError(f"Unsupported agg: {agg}")

            rec = SlugPplAgg(run_ts=run_ts, slug=slug, metric=metric, agg=agg, value=value, n=int(arr.size))
            f.write(json.dumps(asdict(rec), ensure_ascii=False) + "\n")
            n += 1

    return n


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Aggregate ppl records by slug")
    p.add_argument("--records", type=str, required=True, help="records.jsonl from ppl_reader")
    p.add_argument("--out", type=str, required=True, help="Output jsonl path")
    p.add_argument("--agg", type=str, default="median", help="median|mean")
    p.add_argument("--no-prefer-io", action="store_true", help="Prefer ppl instead of ppl_io")

    args = p.parse_args(argv)
    n = aggregate_by_slug(
        records_path=Path(args.records),
        out_path=Path(args.out),
        agg=str(args.agg),
        prefer_io=(not bool(args.no_prefer_io)),
    )
    print(f"aggregated_rows={n}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
