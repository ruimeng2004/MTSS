#!/usr/bin/env python3
"""Test 20 Gen format bugs to diagnose issues."""

import os
import sys
import logging
from pathlib import Path
from datetime import datetime

# Add evaluation module to path
sys.path.insert(0, str(Path(__file__).parent / "evaluation"))

from evaluation.core.evaluator import D4JFixEvaluator
from evaluation.core.config_loader import ConfigLoader

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Select 20 bugs from different projects for testing
TEST_BUGS = [
    "Chart_1", "Chart_2", "Chart_3", "Chart_4", "Chart_5",
    "Cli_11", "Cli_12", "Cli_13", "Cli_14", "Cli_15",
    "Closure_1", "Closure_2", "Closure_3", "Closure_4", "Closure_5",
    "Lang_1", "Lang_2", "Lang_3", "Math_1", "Math_2"
]

def main():
    """Run evaluation on 20 test bugs."""
    input_dir = Path("ppl/result/20260106_030425")
    
    # Check if input directory exists
    if not input_dir.exists():
        logger.error(f"Input directory not found: {input_dir}")
        sys.exit(1)
    
    # Create output directory with timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_dir = Path(f"evaluation_output/gen_20_test_{timestamp}")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    logger.info(f"Testing {len(TEST_BUGS)} Gen format bugs...")
    logger.info(f"Input: {input_dir}")
    logger.info(f"Output: {output_dir}")
    logger.info(f"Bugs: {', '.join(TEST_BUGS)}")
    
    # Initialize evaluator
    config = {
        'evaluation_config': {
            'd4j_path': '/Users/mengrui/Desktop/D4J/defects4j',
            'workspace_dir': './test_workspace',
            'timeout': 600
        }
    }
    
    evaluator = D4JFixEvaluator(
        result_folder=input_dir,
        output_dir=output_dir,
        config=config
    )
    
    # Evaluate each bug
    successful = 0
    failed = 0
    
    for bug_slug in TEST_BUGS:
        logger.info(f"\n{'='*60}")
        logger.info(f"Evaluating: {bug_slug}")
        logger.info(f"{'='*60}")
        
        try:
            result = evaluator.evaluate_bug(bug_slug)
            
            if result.is_fixed:
                successful += 1
                logger.info(f"✓ {bug_slug} FIXED (attempt {result.successful_attempt})")
            else:
                failed += 1
                logger.warning(f"✗ {bug_slug} FAILED: {result.failure_reason}")
                
        except Exception as e:
            failed += 1
            logger.error(f"✗ {bug_slug} ERROR: {e}", exc_info=True)
    
    # Print summary
    logger.info(f"\n{'='*60}")
    logger.info("SUMMARY")
    logger.info(f"{'='*60}")
    logger.info(f"Total: {len(TEST_BUGS)}")
    logger.info(f"Successful: {successful} ({successful/len(TEST_BUGS)*100:.1f}%)")
    logger.info(f"Failed: {failed} ({failed/len(TEST_BUGS)*100:.1f}%)")
    logger.info(f"Output directory: {output_dir}")

if __name__ == "__main__":
    main()
