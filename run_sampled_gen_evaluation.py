#!/usr/bin/env python3
"""Run evaluation on sampled bugs from each project type."""

import argparse
import json
import logging
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path
from typing import List

sys.path.insert(0, str(Path(__file__).parent))

from evaluation.core.evaluator import D4JFixEvaluator
from evaluation.core.data_structures import BugEvaluationResult
from run_gen_batch_evaluation import GenBatchEvaluator

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('sampled_gen_evaluation.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


def load_bug_list(bug_list_file: str) -> List[str]:
    """Load bug list from file."""
    path = Path(bug_list_file)
    
    if path.suffix == '.json':
        with open(path, 'r') as f:
            data = json.load(f)
            return data.get('bugs', [])
    else:
        with open(path, 'r') as f:
            return [line.strip() for line in f if line.strip()]


class FilteredGenBatchEvaluator(GenBatchEvaluator):
    """Evaluator with bug filtering."""
    
    def __init__(self, *args, bug_filter=None, **kwargs):
        self.bug_filter_list = bug_filter
        super().__init__(*args, **kwargs)
    
    def get_all_bugs(self) -> List[str]:
        """Get filtered list of bugs."""
        if self.bug_filter_list:
            bug_set = set(self.bug_filter_list)
            all_bugs = [b for b in self.bug_filter_list if (self.input_dir / b).is_dir()]
            logger.info(f"Found {len(all_bugs)} bugs to evaluate (filtered from {len(self.bug_filter_list)})")
        else:
            all_bugs = super().get_all_bugs()
        
        return all_bugs


def main():
    """Main function."""
    parser = argparse.ArgumentParser(
        description="Run evaluation on sampled bugs"
    )
    parser.add_argument(
        "--input-dir",
        type=str,
        required=True,
        help="Directory containing gen batch results"
    )
    parser.add_argument(
        "--bug-list",
        type=str,
        required=True,
        help="File containing list of bugs to evaluate"
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default=None,
        help="Output directory (default: auto-generated)"
    )
    parser.add_argument(
        "--d4j-path",
        type=str,
        default="/Users/mengrui/Desktop/D4J/defects4j",
        help="Path to Defects4J installation"
    )
    parser.add_argument(
        "--workspace",
        type=str,
        default="./parallel_workspace",
        help="Base workspace directory"
    )
    parser.add_argument(
        "--workers",
        type=int,
        default=20,
        help="Number of parallel workers"
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=240,
        help="Timeout per bug in seconds"
    )
    
    args = parser.parse_args()
    
    # Load bug list
    logger.info(f"Loading bug list from: {args.bug_list}")
    bug_list = load_bug_list(args.bug_list)
    logger.info(f"Loaded {len(bug_list)} bugs")
    
    # Generate output directory name if not specified
    if args.output_dir is None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        args.output_dir = f"evaluation_output/sampled_gen_eval_{timestamp}"
    
    # Create evaluator
    evaluator = FilteredGenBatchEvaluator(
        input_dir=args.input_dir,
        output_dir=args.output_dir,
        d4j_path=args.d4j_path,
        base_workspace=args.workspace,
        num_workers=args.workers,
        timeout=args.timeout,
        bug_filter=bug_list
    )
    
    # Run evaluation
    evaluator.evaluate_parallel()


if __name__ == "__main__":
    main()
