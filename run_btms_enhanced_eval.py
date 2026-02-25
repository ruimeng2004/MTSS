#!/usr/bin/env python3
"""Enhanced evaluation script with budget allocation routing.

This script extends the MTSS evaluation to use the new budget allocation
routing mechanism for task modeling selection.
"""

import argparse
import json
import logging
import sys
import yaml
from pathlib import Path
from typing import Dict, Any, Optional

# Add MTSS modules to path
sys.path.insert(0, str(Path(__file__).parent))

from bug_task_model_selection.src.btms.selection import EnhancedTaskModelSelector

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class BTMSEnhancedEvaluator:
    """Enhanced evaluator using budget allocation for routing."""
    
    def __init__(self, config_path: str):
        """Initialize evaluator from config file.
        
        Args:
            config_path: Path to YAML configuration file.
        """
        self.config = self._load_config(config_path)
        self.selector = self._create_selector()
        
        logger.info(f"Initialized BTMSEnhancedEvaluator")
        logger.info(f"Selector type: {self.config['selector_type']}")
    
    def _load_config(self, config_path: str) -> Dict[str, Any]:
        """Load configuration from YAML file."""
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)
        return config
    
    def _create_selector(self) -> EnhancedTaskModelSelector:
        """Create selector from configuration."""
        selector_type = self.config.get('selector_type', 'binary')
        
        if selector_type == 'binary':
            selector_config = self.config.get('binary_selector', {})
        else:
            selector_config = self.config.get('budget_allocator', {})
        
        return EnhancedTaskModelSelector(
            selector_type=selector_type,
            selector_config=selector_config
        )
    
    def run_selection(
        self,
        representatives_path: Optional[str] = None,
        ppl_edit_path: Optional[str] = None,
        ppl_gen_path: Optional[str] = None,
        assignments_path: Optional[str] = None,
        output_dir: Optional[str] = None
    ) -> Dict[str, Dict[str, Any]]:
        """Run task modeling selection.
        
        Args:
            representatives_path: Path to representatives file.
            ppl_edit_path: Path to edit PPL scores.
            ppl_gen_path: Path to gen PPL scores.
            assignments_path: Path to cluster assignments.
            output_dir: Output directory for results.
            
        Returns:
            Dictionary of cluster choices.
        """
        # Use config paths if not provided
        data_paths = self.config.get('data_paths', {})
        representatives_path = representatives_path or data_paths.get('representatives')
        ppl_edit_path = ppl_edit_path or data_paths.get('ppl_edit')
        ppl_gen_path = ppl_gen_path or data_paths.get('ppl_gen')
        assignments_path = assignments_path or data_paths.get('assignments')
        
        output_config = self.config.get('output', {})
        output_dir = output_dir or output_config.get('base_dir')
        
        # Validate paths
        for name, path in [
            ('representatives', representatives_path),
            ('ppl_edit', ppl_edit_path),
            ('ppl_gen', ppl_gen_path),
            ('assignments', assignments_path)
        ]:
            if not path or not Path(path).exists():
                raise FileNotFoundError(f"{name} file not found: {path}")
        
        logger.info("Running task modeling selection...")
        logger.info(f"  Representatives: {representatives_path}")
        logger.info(f"  Edit PPL: {ppl_edit_path}")
        logger.info(f"  Gen PPL: {ppl_gen_path}")
        logger.info(f"  Assignments: {assignments_path}")
        logger.info(f"  Output: {output_dir}")
        
        # Run selection
        cluster_choices = self.selector.select(
            representatives_path=Path(representatives_path),
            ppl_edit_path=Path(ppl_edit_path),
            ppl_gen_path=Path(ppl_gen_path),
            assignments_path=Path(assignments_path),
            out_dir=Path(output_dir)
        )
        
        logger.info(f"Selection completed for {len(cluster_choices)} clusters")
        
        return cluster_choices
    
    def generate_routing_decisions(
        self,
        cluster_choices: Dict[str, Dict[str, Any]],
        assignments_path: str,
        output_path: str
    ):
        """Generate bug-level routing decisions from cluster choices.
        
        Args:
            cluster_choices: Cluster-level choices from selection.
            assignments_path: Path to cluster assignments.
            output_path: Path to save routing decisions.
        """
        logger.info("Generating bug-level routing decisions...")
        
        # Load assignments
        with open(assignments_path, 'r') as f:
            assignments = [json.loads(line) for line in f]
        
        # Create bug routing decisions
        routing = {}
        
        for item in assignments:
            slug = item.get('slug')
            cluster_id = str(item.get('cluster_id'))
            
            if cluster_id in cluster_choices:
                choice = cluster_choices[cluster_id]
                routing[slug] = {
                    'slug': slug,
                    'cluster_id': int(cluster_id),
                    'decision': choice.get('decision'),
                    'ratio': choice.get('ratio'),
                    'confidence': choice.get('confidence')
                }
        
        # Save routing decisions
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_path, 'w') as f:
            json.dump(routing, f, indent=2)
        
        logger.info(f"Saved routing decisions to {output_path}")
        logger.info(f"  Total bugs: {len(routing)}")
        
        # Log statistics
        decisions = [r['decision'] for r in routing.values()]
        decision_counts = {}
        for d in decisions:
            decision_counts[d] = decision_counts.get(d, 0) + 1
        
        logger.info("Routing decision distribution:")
        for decision, count in sorted(decision_counts.items()):
            logger.info(f"  {decision}: {count} ({count/len(decisions)*100:.1f}%)")
        
        return routing


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description='Enhanced BTMS evaluation with budget allocation'
    )
    parser.add_argument(
        '--config',
        type=str,
        default='btms_config.yaml',
        help='Path to configuration file'
    )
    parser.add_argument(
        '--representatives',
        type=str,
        help='Path to representatives file (overrides config)'
    )
    parser.add_argument(
        '--ppl-edit',
        type=str,
        help='Path to edit PPL scores (overrides config)'
    )
    parser.add_argument(
        '--ppl-gen',
        type=str,
        help='Path to gen PPL scores (overrides config)'
    )
    parser.add_argument(
        '--assignments',
        type=str,
        help='Path to cluster assignments (overrides config)'
    )
    parser.add_argument(
        '--output',
        type=str,
        help='Output directory (overrides config)'
    )
    parser.add_argument(
        '--routing-output',
        type=str,
        help='Path to save bug-level routing decisions'
    )
    
    args = parser.parse_args()
    
    try:
        # Initialize evaluator
        evaluator = BTMSEnhancedEvaluator(args.config)
        
        # Run selection
        cluster_choices = evaluator.run_selection(
            representatives_path=args.representatives,
            ppl_edit_path=args.ppl_edit,
            ppl_gen_path=args.ppl_gen,
            assignments_path=args.assignments,
            output_dir=args.output
        )
        
        # Generate bug-level routing if requested
        if args.routing_output:
            assignments_path = args.assignments or \
                evaluator.config['data_paths']['assignments']
            
            evaluator.generate_routing_decisions(
                cluster_choices,
                assignments_path,
                args.routing_output
            )
        
        logger.info("Enhanced BTMS evaluation completed successfully!")
        return 0
        
    except Exception as e:
        logger.error(f"Evaluation failed: {e}", exc_info=True)
        return 1


if __name__ == '__main__':
    sys.exit(main())
