"""Aggregate PPL results from nested directory structure to JSONL format."""
from __future__ import annotations

import argparse
import json
from collections import defaultdict
from pathlib import Path


def extract_config(result: dict) -> tuple[str, str]:
    """Extract (model_short_name, task) from result.json."""
    model_path = result.get("model", "")
    task = result.get("task", "")
    
    # Extract model short name
    if "Qwen3-Coder" in model_path:
        model_short = "qwen3_coder"
    elif "Qwen3-30B-A3B" in model_path:
        model_short = "qwen3_30b"
    else:
        model_short = "unknown"
    
    # Extract task type
    if task == "d4j_edit":
        task_short = "edit"
    elif task == "d4j_gen":
        task_short = "gen"
    else:
        task_short = "unknown"
    
    return model_short, task_short


def aggregate_ppl(result_dirs: list[Path], outdir: Path, metric: str = "avg_nll") -> None:
    """Aggregate PPL results by (model, task) combination."""
    outdir.mkdir(parents=True, exist_ok=True)
    
    # Collect all results: {(model, task): {slug: [values]}}
    data: dict[tuple[str, str], dict[str, list[float]]] = defaultdict(lambda: defaultdict(list))
    
    for result_dir in result_dirs:
        if not result_dir.is_dir():
            continue
        
        # Iterate over slug directories
        for slug_dir in result_dir.iterdir():
            if not slug_dir.is_dir():
                continue
            
            slug = slug_dir.name
            
            # Check if it has sample subdirectories (1/, 2/, ...) or direct result.json
            sample_dirs = [d for d in slug_dir.iterdir() if d.is_dir() and d.name.isdigit()]
            
            if sample_dirs:
                # Multiple samples
                for sample_dir in sample_dirs:
                    result_file = sample_dir / "result.json"
                    if result_file.exists():
                        try:
                            with result_file.open("r", encoding="utf-8") as f:
                                result = json.load(f)
                            model, task = extract_config(result)
                            value = result.get(metric)
                            if value is not None and not (isinstance(value, float) and value != value):  # check NaN
                                data[(model, task)][slug].append(float(value))
                        except Exception as e:
                            print(f"Error reading {result_file}: {e}")
            else:
                # Single result
                result_file = slug_dir / "result.json"
                if result_file.exists():
                    try:
                        with result_file.open("r", encoding="utf-8") as f:
                            result = json.load(f)
                        model, task = extract_config(result)
                        value = result.get(metric)
                        if value is not None and not (isinstance(value, float) and value != value):
                            data[(model, task)][slug].append(float(value))
                    except Exception as e:
                        print(f"Error reading {result_file}: {e}")
    
    # Write aggregated results
    for (model, task), slug_values in data.items():
        out_file = outdir / f"{model}_{task}.jsonl"
        with out_file.open("w", encoding="utf-8") as f:
            for slug, values in sorted(slug_values.items()):
                avg_value = sum(values) / len(values)
                f.write(json.dumps({"slug": slug, "value": avg_value}, ensure_ascii=False) + "\n")
        print(f"Written {out_file} with {len(slug_values)} slugs")


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Aggregate PPL results to JSONL")
    p.add_argument("--result-dirs", type=str, nargs="+", required=True, help="PPL result directories")
    p.add_argument("--outdir", type=str, required=True, help="Output directory")
    p.add_argument("--metric", type=str, default="avg_nll", help="Metric to aggregate (avg_nll or ppl)")
    
    args = p.parse_args(argv)
    
    result_dirs = [Path(d) for d in args.result_dirs]
    aggregate_ppl(result_dirs, Path(args.outdir), args.metric)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
