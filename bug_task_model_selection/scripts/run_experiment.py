#!/usr/bin/env python
"""CLI entry point for running BTMS experiments."""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.btms.experiment import (
    ExperimentConfig,
    ExperimentRunner,
    generate_report,
    load_experiment_config,
)


def setup_logging(verbose: bool = False) -> None:
    """Setup logging configuration."""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )


def parse_args() -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Run BTMS pipeline experiments",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Run from config file
  python run_experiment.py --config configs/experiment.yaml
  
  # Run single experiment with CLI args
  python run_experiment.py \\
    --embeddings data/embeddings.jsonl \\
    --ppl edit:data/edit_ppl.jsonl gen:data/gen_ppl.jsonl \\
    --view buggy_code \\
    --algorithm kmeans \\
    --k 100 \\
    --sampling farthest_first \\
    --reps 3 \\
    --output results/
        """,
    )
    
    # Config file mode
    parser.add_argument(
        "--config", "-c",
        type=Path,
        help="Path to YAML configuration file",
    )
    
    # CLI mode arguments
    parser.add_argument(
        "--embeddings", "-e",
        type=Path,
        help="Path to embeddings.jsonl",
    )
    parser.add_argument(
        "--ppl",
        nargs="+",
        help="PPL score files in format name:path (e.g., edit:edit.jsonl gen:gen.jsonl)",
    )
    parser.add_argument(
        "--view", "-v",
        nargs="+",
        default=["buggy_code"],
        help="Views to experiment with (default: buggy_code)",
    )
    parser.add_argument(
        "--algorithm", "-a",
        nargs="+",
        default=["kmeans"],
        choices=["kmeans", "hac_average", "hac_ward", "hac_complete", "hac_single", "bisecting_kmeans"],
        help="Clustering algorithms (default: kmeans)",
    )
    parser.add_argument(
        "--k",
        nargs="+",
        type=int,
        default=[100],
        help="Number of clusters (default: 100)",
    )
    parser.add_argument(
        "--sampling", "-s",
        nargs="+",
        default=["farthest_first"],
        choices=["farthest_first", "kdpp"],
        help="Sampling methods (default: farthest_first)",
    )
    parser.add_argument(
        "--reps", "-r",
        nargs="+",
        type=int,
        default=[1],
        help="Representatives per cluster (default: 1)",
    )
    parser.add_argument(
        "--output", "-o",
        type=Path,
        default=Path("results"),
        help="Output directory (default: results)",
    )
    parser.add_argument(
        "--name", "-n",
        default="experiment",
        help="Experiment name (default: experiment)",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=42,
        help="Random seed (default: 42)",
    )
    parser.add_argument(
        "--parallel", "-p",
        action="store_true",
        help="Run experiments in parallel",
    )
    parser.add_argument(
        "--workers", "-w",
        type=int,
        default=4,
        help="Number of parallel workers (default: 4)",
    )
    parser.add_argument(
        "--no-skip",
        action="store_true",
        help="Don't skip existing experiments",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose logging",
    )
    
    return parser.parse_args()


def build_config_from_args(args: argparse.Namespace) -> ExperimentConfig:
    """Build ExperimentConfig from CLI arguments."""
    if not args.embeddings:
        raise ValueError("--embeddings is required when not using --config")
    if not args.ppl:
        raise ValueError("--ppl is required when not using --config")
    
    # Parse PPL paths
    ppl_paths = {}
    for item in args.ppl:
        if ":" not in item:
            raise ValueError(f"Invalid PPL format: {item}. Expected name:path")
        name, path = item.split(":", 1)
        ppl_paths[name] = Path(path)
    
    return ExperimentConfig(
        name=args.name,
        embeddings_path=args.embeddings,
        ppl_paths=ppl_paths,
        views=args.view,
        clustering_algorithms=args.algorithm,
        k_values=args.k,
        sampling_methods=args.sampling,
        reps_per_cluster_values=args.reps,
        output_dir=args.output,
        seed=args.seed,
        parallel=args.parallel,
        n_workers=args.workers,
        skip_existing=not args.no_skip,
    )


def main() -> int:
    """Main entry point."""
    args = parse_args()
    setup_logging(args.verbose)
    
    logger = logging.getLogger(__name__)
    
    try:
        # Load or build config
        if args.config:
            logger.info(f"Loading config from {args.config}")
            config = load_experiment_config(args.config)
        else:
            logger.info("Building config from CLI arguments")
            config = build_config_from_args(args)
        
        # Log experiment info
        logger.info(f"Experiment: {config.name}")
        logger.info(f"Total combinations: {config.total_combinations()}")
        logger.info(f"Output directory: {config.output_dir}")
        
        # Run experiments
        runner = ExperimentRunner(config)
        results = runner.run()
        
        # Generate reports
        logger.info("Generating reports...")
        generate_report(config, results)
        
        # Summary
        completed = sum(1 for r in results if r.get("status") == "completed")
        skipped = sum(1 for r in results if r.get("status") == "skipped")
        failed = sum(1 for r in results if r.get("status") == "failed")
        
        logger.info(f"Done! Completed: {completed}, Skipped: {skipped}, Failed: {failed}")
        logger.info(f"Reports saved to {config.output_dir}")
        
        return 0 if failed == 0 else 1
        
    except Exception as e:
        logger.error(f"Error: {e}")
        if args.verbose:
            import traceback
            traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
