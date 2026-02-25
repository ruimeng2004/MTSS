from __future__ import annotations

import argparse
import json
from pathlib import Path


def _fmt_stat_block(d: dict | None) -> str:
    if not d:
        return "(no data)"
    parts = []
    for k in ["n", "mean", "median", "std", "min", "max"]:
        if k not in d:
            continue
        v = d[k]
        if isinstance(v, float):
            parts.append(f"{k}={v:.4f}")
        else:
            parts.append(f"{k}={v}")
    return ", ".join(parts)


def generate_report(*, cluster_metrics_path: Path | None, overall_metrics_path: Path | None, out_path: Path) -> None:
    lines: list[str] = []
    lines.append("# Bug Task-Model Selection Report")
    lines.append("")

    if overall_metrics_path is not None and overall_metrics_path.exists():
        overall = json.loads(overall_metrics_path.read_text(encoding="utf-8"))
        lines.append("## Overall Metrics")
        lines.append("")
        lines.append(f"- n_slugs: {overall.get('n_slugs')}")
        lines.append("")

        strategies = overall.get("strategies") or {}
        for name in sorted(strategies.keys()):
            st = strategies[name]
            stats = st.get("stats") if isinstance(st, dict) else None
            lines.append(f"### {name}")
            lines.append("")
            lines.append(_fmt_stat_block(stats if isinstance(stats, dict) else None))
            lines.append("")

    if cluster_metrics_path is not None and cluster_metrics_path.exists():
        cm = json.loads(cluster_metrics_path.read_text(encoding="utf-8"))
        clusters = cm.get("clusters") or {}

        lines.append("## Cluster Metrics (Top delta clusters)")
        lines.append("")

        scored: list[tuple[int, float, dict]] = []
        for cid_str, obj in clusters.items():
            if not isinstance(obj, dict):
                continue
            deltas = obj.get("deltas")
            if not isinstance(deltas, dict) or not deltas:
                continue
            key = sorted(deltas.keys())[0]
            st = deltas.get(key)
            if not isinstance(st, dict):
                continue
            mean = st.get("mean")
            if mean is None:
                continue
            try:
                mean_f = float(mean)
            except Exception:
                continue
            scored.append((int(obj.get("cluster_id")), abs(mean_f), obj))

        scored.sort(key=lambda x: x[1], reverse=True)
        top = scored[:20]

        if not top:
            lines.append("(no cluster delta data)")
            lines.append("")
        else:
            for cid, _, obj in top:
                lines.append(f"### Cluster {cid}")
                lines.append("")
                lines.append(f"- n_items: {obj.get('n_items')}")
                if obj.get("chosen") is not None:
                    lines.append(f"- chosen: {obj.get('chosen')}")
                deltas = obj.get("deltas") or {}
                if isinstance(deltas, dict) and deltas:
                    key = sorted(deltas.keys())[0]
                    lines.append(f"- delta_key: {key}")
                    st = deltas.get(key)
                    lines.append(f"- delta_stats: {_fmt_stat_block(st if isinstance(st, dict) else None)}")
                lines.append("")

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Generate a Markdown report from metrics outputs")
    p.add_argument("--cluster-metrics", type=str, default=None, help="cluster_metrics.json from cluster_metrics.py")
    p.add_argument("--overall-metrics", type=str, default=None, help="overall_metrics.json from overall_metrics.py")
    p.add_argument("--out", type=str, required=True, help="Output Markdown path")

    args = p.parse_args(argv)

    generate_report(
        cluster_metrics_path=(Path(args.cluster_metrics) if args.cluster_metrics else None),
        overall_metrics_path=(Path(args.overall_metrics) if args.overall_metrics else None),
        out_path=Path(args.out),
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
