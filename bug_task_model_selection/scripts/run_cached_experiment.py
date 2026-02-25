#!/usr/bin/env python
"""CLI entry point for running cached BTMS experiments."""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.btms.experiment import (
    ExperimentConfig,
    generate_report,
    load_experiment_config,
)
from src.btms.experiment.cached_runner import CachedExperimentRunner


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
        description="Run BTMS experiments with caching (faster for large parameter grids)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Run from config file
  python run_cached_experiment.py --config configs/exp_full_coder.yaml
  
  # With verbose logging
  python run_cached_experiment.py --config configs/exp_full_coder.yaml --verbose
        """,
    )
    
    parser.add_argument(
        "--config", "-c",
        type=Path,
        required=True,
        help="Path to YAML configuration file",
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Enable verbose logging",
    )
    
    return parser.parse_args()


def main() -> int:
    """Main entry point."""
    args = parse_args()
    setup_logging(args.verbose)
    
    logger = logging.getLogger(__name__)
    
    try:
        # Load config
        logger.info(f"Loading config from {args.config}")
        config = load_experiment_config(args.config)
        
        # Log experiment info
        logger.info(f"Experiment: {config.name}")
        logger.info(f"Total combinations: {config.total_combinations()}")
        logger.info(f"Views: {len(config.views)}")
        logger.info(f"Algorithms: {len(config.clustering_algorithms)}")
        logger.info(f"K values: {config.k_values}")
        logger.info(f"Sampling methods: {config.sampling_methods}")
        logger.info(f"Reps: {config.reps_per_cluster_values}")
        logger.info(f"Seeds: {config.seeds}")
        logger.info(f"Voting strategies: {config.voting_strategies}")
        logger.info(f"Output directory: {config.output_dir}")
        
        # Run experiments with caching
        runner = CachedExperimentRunner(config)
        results = runner.run()
        
        # Generate reports
        logger.info("Generating reports...")
        generate_report(config, results)
        
        # Summary
        completed = sum(1 for r in results if r.get("status") == "completed")
        failed = sum(1 for r in results if r.get("status") == "failed")
        
        logger.info(f"Done! Completed: {completed}, Failed: {failed}")
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
