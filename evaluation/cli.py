"""Command-line interface for D4J fix evaluation system.

This module provides a CLI for evaluating Defects4J bug fixes.
"""

import argparse
import logging
import sys
from pathlib import Path
from typing import List, Optional

from evaluation.core.config_loader import load_config
from evaluation.core.evaluator import D4JFixEvaluator
from evaluation.utils.logging_config import setup_evaluation_logging

logger = logging.getLogger(__name__)


def parse_args(args: Optional[List[str]] = None) -> argparse.Namespace:
    """Parse command-line arguments.
    
    Args:
        args: List of arguments to parse (None = sys.argv).
        
    Returns:
        Parsed arguments namespace.
    """
    parser = argparse.ArgumentParser(
        prog='evaluation',
        description='Evaluate Defects4J bug fixes from model outputs',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Basic usage
  python -m evaluation.cli --result-folder ppl/result/20260105_132306
  
  # With custom output directory
  python -m evaluation.cli --result-folder results/ --output eval_output/
  
  # Parallel evaluation with 4 workers
  python -m evaluation.cli --result-folder results/ --workers 4
  
  # Evaluate specific bugs only
  python -m evaluation.cli --result-folder results/ --bugs Chart_1,Chart_2
  
  # Verbose mode with custom config
  python -m evaluation.cli --result-folder results/ --verbose --config custom.yaml
        """
    )
    
    # Required arguments
    parser.add_argument(
        '--result-folder',
        type=str,
        required=True,
        help='Path to result folder containing fix attempts (required)'
    )
    
    # Optional arguments
    parser.add_argument(
        '--output',
        type=str,
        default='./evaluation_output',
        help='Output directory for evaluation results (default: ./evaluation_output)'
    )
    
    parser.add_argument(
        '--workers',
        type=int,
        default=1,
        help='Number of parallel workers (default: 1, not yet implemented)'
    )
    
    parser.add_argument(
        '--verbose',
        action='store_true',
        help='Enable verbose logging'
    )
    
    parser.add_argument(
        '--config',
        type=str,
        default='config.yaml',
        help='Path to configuration file (default: config.yaml)'
    )
    
    parser.add_argument(
        '--bugs',
        type=str,
        default=None,
        help='Comma-separated list of bug slugs to evaluate (e.g., Chart_1,Chart_2)'
    )
    
    parser.add_argument(
        '--log-file',
        type=str,
        default=None,
        help='Path to log file (default: None, logs to console only)'
    )
    
    return parser.parse_args(args)


def validate_args(args: argparse.Namespace) -> None:
    """Validate command-line arguments.
    
    Args:
        args: Parsed arguments.
        
    Raises:
        ValueError: If arguments are invalid.
    """
    # Validate result folder exists
    result_folder = Path(args.result_folder)
    if not result_folder.exists():
        raise ValueError(
            f"Result folder does not exist: {args.result_folder}"
        )
    
    if not result_folder.is_dir():
        raise ValueError(
            f"Result folder is not a directory: {args.result_folder}"
        )
    
    # Validate workers
    if args.workers < 1:
        raise ValueError(
            f"Number of workers must be >= 1, got: {args.workers}"
        )
    
    # Validate config file exists
    config_path = Path(args.config)
    if not config_path.exists():
        raise ValueError(
            f"Config file does not exist: {args.config}"
        )


def parse_bug_list(bug_string: Optional[str]) -> Optional[List[str]]:
    """Parse comma-separated bug list.
    
    Args:
        bug_string: Comma-separated bug slugs (e.g., "Chart_1,Chart_2").
        
    Returns:
        List of bug slugs, or None if bug_string is None.
    """
    if bug_string is None:
        return None
    
    # Split by comma and strip whitespace
    bugs = [b.strip() for b in bug_string.split(',')]
    
    # Filter out empty strings
    bugs = [b for b in bugs if b]
    
    return bugs if bugs else None


def main(args: Optional[List[str]] = None) -> int:
    """Main entry point for CLI.
    
    Args:
        args: List of arguments to parse (None = sys.argv).
        
    Returns:
        Exit code (0 = success, 1 = error).
    """
    try:
        # Parse arguments
        parsed_args = parse_args(args)
        
        # Setup logging
        log_level = 'DEBUG' if parsed_args.verbose else 'INFO'
        from evaluation.utils.logging_config import setup_logging
        setup_logging(
            level=log_level,
            log_file=Path(parsed_args.log_file) if parsed_args.log_file else None
        )
        
        logger.info("=" * 80)
        logger.info("D4J Fix Evaluation System")
        logger.info("=" * 80)
        
        # Validate arguments
        try:
            validate_args(parsed_args)
        except ValueError as e:
            logger.error(f"Invalid arguments: {e}")
            return 1
        
        # Load configuration
        logger.info(f"Loading configuration from: {parsed_args.config}")
        try:
            config = load_config(parsed_args.config)
        except Exception as e:
            logger.error(f"Failed to load configuration: {e}")
            return 1
        
        # Parse bug filter
        bug_filter = parse_bug_list(parsed_args.bugs)
        if bug_filter:
            logger.info(f"Bug filter: {bug_filter}")
        
        # Create evaluator
        logger.info(f"Result folder: {parsed_args.result_folder}")
        logger.info(f"Output directory: {parsed_args.output}")
        logger.info(f"Workers: {parsed_args.workers}")
        
        evaluator = D4JFixEvaluator(
            result_folder=Path(parsed_args.result_folder),
            output_dir=Path(parsed_args.output),
            config=config
        )
        
        # Run evaluation
        logger.info("Starting evaluation...")
        batch_result = evaluator.evaluate(
            parallel=parsed_args.workers,
            verbose=parsed_args.verbose,
            bug_filter=bug_filter
        )
        
        # Print summary
        logger.info("=" * 80)
        logger.info("EVALUATION SUMMARY")
        logger.info("=" * 80)
        logger.info(f"Total bugs: {batch_result.total_bugs}")
        logger.info(f"Fixed bugs: {batch_result.fixed_bugs}")
        logger.info(f"Failed bugs: {batch_result.failed_bugs}")
        logger.info(f"Fix rate: {batch_result.fix_rate:.2f}%")
        logger.info("=" * 80)
        
        # Print statistics by modeling type
        if batch_result.statistics:
            stats = batch_result.statistics
            if 'by_modeling_type' in stats:
                logger.info("By modeling type:")
                for mtype, mstats in stats['by_modeling_type'].items():
                    logger.info(
                        f"  {mtype}: {mstats.get('fixed', 0)}/"
                        f"{mstats.get('total', 0)} "
                        f"({mstats.get('fix_rate', 0):.2f}%)"
                    )
        
        logger.info(f"\nResults saved to: {parsed_args.output}")
        
        # Return success if at least one bug was fixed
        return 0 if batch_result.fixed_bugs > 0 else 1
        
    except KeyboardInterrupt:
        logger.warning("\nEvaluation interrupted by user")
        return 130  # Standard exit code for SIGINT
        
    except Exception as e:
        logger.error(f"Evaluation failed: {e}", exc_info=True)
        return 1


if __name__ == '__main__':
    sys.exit(main())
