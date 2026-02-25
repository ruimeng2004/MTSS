"""Report generation for experiment results."""

from __future__ import annotations

import csv
import json
from typing import Any

from .config import ExperimentConfig


class ReportGenerator:
    """Generator for experiment reports in JSON and CSV formats."""
    
    def __init__(self, config: ExperimentConfig, results: list[dict[str, Any]]):
        """Initialize report generator.
        
        Args:
            config: Experiment configuration
            results: List of experiment results
        """
        self.config = config
        self.results = results
    
    def generate(self) -> None:
        """Generate all report formats."""
        self.config.output_dir.mkdir(parents=True, exist_ok=True)
        
        self._generate_json_report()
        self._generate_csv_report()
        self._generate_summary()
    
    def _generate_json_report(self) -> None:
        """Generate comprehensive JSON report."""
        report = {
            "config": self.config.to_dict(),
            "results": self.results,
            "summary": self._compute_summary(),
        }
        
        out_path = self.config.output_dir / "experiment_report.json"
        with out_path.open("w", encoding="utf-8") as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
    
    def _generate_csv_report(self) -> None:
        """Generate CSV report for easy analysis."""
        out_path = self.config.output_dir / "experiment_results.csv"
        
        # Collect all possible columns
        param_keys = set()
        metric_keys = set()
        
        for result in self.results:
            if "params" in result:
                param_keys.update(result["params"].keys())
            if "metrics" in result and isinstance(result["metrics"], dict):
                metric_keys.update(result["metrics"].keys())
        
        param_keys = sorted(param_keys)
        metric_keys = sorted(metric_keys)
        
        fieldnames = ["status"] + param_keys + metric_keys
        
        with out_path.open("w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            
            for result in self.results:
                row = {"status": result.get("status", "unknown")}
                
                # Add params
                params = result.get("params", {})
                for key in param_keys:
                    row[key] = params.get(key, "")
                
                # Add metrics
                metrics = result.get("metrics", {})
                if isinstance(metrics, dict):
                    for key in metric_keys:
                        row[key] = metrics.get(key, "")
                
                writer.writerow(row)
    
    def _generate_summary(self) -> None:
        """Generate summary report."""
        summary = self._compute_summary()
        
        out_path = self.config.output_dir / "experiment_summary.json"
        with out_path.open("w", encoding="utf-8") as f:
            json.dump(summary, f, indent=2, ensure_ascii=False)
    
    def _compute_summary(self) -> dict[str, Any]:
        """Compute summary statistics.
        
        Returns:
            Summary dictionary
        """
        completed = [r for r in self.results if r.get("status") == "completed"]
        skipped = [r for r in self.results if r.get("status") == "skipped"]
        failed = [r for r in self.results if r.get("status") == "failed"]
        
        # Find best configuration by win_rate
        best_config = None
        best_win_rate = -1.0
        
        for result in completed + skipped:
            metrics = result.get("metrics", {})
            win_rate = metrics.get("win_rate", 0.0)
            if win_rate > best_win_rate:
                best_win_rate = win_rate
                best_config = result.get("params")
        
        # Compute aggregates by dimension
        aggregates = self._compute_aggregates()
        
        return {
            "total_experiments": len(self.results),
            "completed": len(completed),
            "skipped": len(skipped),
            "failed": len(failed),
            "best_config": best_config,
            "best_win_rate": best_win_rate,
            "aggregates": aggregates,
        }
    
    def _compute_aggregates(self) -> dict[str, dict[str, float]]:
        """Compute aggregate statistics by each parameter dimension.
        
        Returns:
            Dict mapping dimension name to {value: mean_win_rate}
        """
        dimensions = [
            "view",
            "clustering_algorithm",
            "k",
            "sampling_method",
            "reps_per_cluster",
        ]
        
        aggregates = {}
        
        for dim in dimensions:
            dim_stats: dict[Any, list[float]] = {}
            
            for result in self.results:
                if result.get("status") not in ("completed", "skipped"):
                    continue
                
                params = result.get("params", {})
                metrics = result.get("metrics", {})
                
                value = params.get(dim)
                win_rate = metrics.get("win_rate")
                
                if value is not None and win_rate is not None:
                    if value not in dim_stats:
                        dim_stats[value] = []
                    dim_stats[value].append(win_rate)
            
            # Compute means
            aggregates[dim] = {
                str(k): sum(v) / len(v) if v else 0.0
                for k, v in sorted(dim_stats.items(), key=lambda x: str(x[0]))
            }
        
        return aggregates


def generate_report(
    config: ExperimentConfig,
    results: list[dict[str, Any]],
) -> None:
    """Convenience function to generate all reports.
    
    Args:
        config: Experiment configuration
        results: List of experiment results
    """
    generator = ReportGenerator(config, results)
    generator.generate()
