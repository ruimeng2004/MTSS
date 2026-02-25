from __future__ import annotations

import argparse
import json
from dataclasses import dataclass, asdict
from pathlib import Path


@dataclass(frozen=True)
class PplRecord:
    run_ts: str
    slug: str
    sample_idx: int | None
    task: str | None
    model: str | None
    base_url: str | None

    ppl: float | None
    avg_nll: float | None
    n_tokens: int | None

    ppl_io: float | None
    avg_nll_io: float | None
    n_tokens_io: int | None

    path: str


def _iter_result_json_files(root: Path):
    for p in root.rglob("result.json"):
        if p.is_file():
            yield p


def _infer_run_ts_and_slug(root: Path, result_path: Path) -> tuple[str, str]:
    rel = result_path.relative_to(root)
    parts = rel.parts
    if len(parts) >= 2:
        return str(parts[0]), str(parts[1])
    raise ValueError(f"Unexpected result.json layout under {root}: {result_path}")


def _parse_record(*, root: Path, result_path: Path) -> PplRecord | None:
    try:
        obj = json.loads(result_path.read_text(encoding="utf-8"))
    except Exception:
        return None

    run_ts, slug = _infer_run_ts_and_slug(root, result_path)

    def _f(key: str) -> float | None:
        v = obj.get(key)
        if v is None:
            return None
        try:
            return float(v)
        except Exception:
            return None

    def _i(key: str) -> int | None:
        v = obj.get(key)
        if v is None:
            return None
        try:
            return int(v)
        except Exception:
            return None

    sample_idx = _i("sample_idx")

    return PplRecord(
        run_ts=run_ts,
        slug=str(obj.get("slug") or slug),
        sample_idx=sample_idx,
        task=str(obj.get("task")) if obj.get("task") is not None else None,
        model=str(obj.get("model")) if obj.get("model") is not None else None,
        base_url=str(obj.get("base_url")) if obj.get("base_url") is not None else None,
        ppl=_f("ppl"),
        avg_nll=_f("avg_nll"),
        n_tokens=_i("n_tokens"),
        ppl_io=_f("ppl_io"),
        avg_nll_io=_f("avg_nll_io"),
        n_tokens_io=_i("n_tokens_io"),
        path=str(result_path),
    )


def export_records(*, root: Path, out_path: Path) -> int:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    n = 0
    with out_path.open("w", encoding="utf-8") as f:
        for rp in _iter_result_json_files(root):
            rec = _parse_record(root=root, result_path=rp)
            if rec is None:
                continue
            f.write(json.dumps(asdict(rec), ensure_ascii=False) + "\n")
            n += 1
    return n


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Read ppl/result outputs and export normalized records.jsonl")
    p.add_argument("--root", type=str, default="ppl/result", help="Root directory containing run_ts/slug/.../result.json")
    p.add_argument("--out", type=str, required=True, help="Output jsonl path")

    args = p.parse_args(argv)
    n = export_records(root=Path(args.root), out_path=Path(args.out))
    print(f"exported_records={n}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
