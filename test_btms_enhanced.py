#!/usr/bin/env python3
"""Test script for enhanced BTMS routing mechanism.

This script validates the budget allocation implementation with sample data.
"""

import json
import logging
import sys
from pathlib import Path
from typing import Dict, Any

# Add MTSS modules to path
sys.path.insert(0, str(Path(__file__).parent))

from bug_task_model_selection.src.btms.selection import (
    BudgetAllocator,
    BinarySelector
)
from bug_task_model_selection.src.btms.selection.budget_metrics import (
    PPLGapMetric,
    VoteConsistencyMetric,
    SizeAdjustedMetric,
    HybridMetric
)
from bug_task_model_selection.src.btms.sampling.adaptive_reps import AdaptiveRepresentatives
from bug_task_model_selection.src.btms.sampling.outlier_handler import OutlierHandler

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def test_metrics():
    """Test budget allocation metrics."""
    logger.info("=" * 60)
    logger.info("Testing Budget Allocation Metrics")
    logger.info("=" * 60)
    
    # Sample data
    cluster_size = 10
    representatives = [
        {"slug": "Chart_1", "rank": 0},
        {"slug": "Chart_2", "rank": 1},
        {"slug": "Chart_3", "rank": 2},
    ]
    ppl_edit = {
        "Chart_1": 15.5,
        "Chart_2": 18.2,
        "Chart_3": 12.8,
    }
    ppl_gen = {
        "Chart_1": 20.3,
        "Chart_2": 16.1,
        "Chart_3": 22.5,
    }
    
    # Test PPL Gap Metric
    logger.info("\n1. Testing PPL Gap Metric:")
    ppl_gap = PPLGapMetric(temperature=1.0)
    ratio = ppl_gap.compute(cluster_size, representatives, ppl_edit, ppl_gen)
    logger.info(f"   Edit ratio: {ratio:.3f}")
    logger.info(f"   Confidence: {ppl_gap.get_confidence():.3f}")
    
    # Test Vote Consistency Metric
    logger.info("\n2. Testing Vote Consistency Metric:")
    vote_cons = VoteConsistencyMetric(confidence_threshold=0.5)
    ratio = vote_cons.compute(cluster_size, representatives, ppl_edit, ppl_gen)
    logger.info(f"   Edit ratio: {ratio:.3f}")
    logger.info(f"   Confidence: {vote_cons.get_confidence():.3f}")
    
    # Test Size Adjusted Metric
    logger.info("\n3. Testing Size Adjusted Metric:")
    size_adj = SizeAdjustedMetric(size_normalization_factor=10)
    ratio = size_adj.compute(cluster_size, representatives, ppl_edit, ppl_gen)
    logger.info(f"   Edit ratio: {ratio:.3f}")
    logger.info(f"   Confidence: {size_adj.get_confidence():.3f}")
    
    # Test Hybrid Metric
    logger.info("\n4. Testing Hybrid Metric:")
    hybrid = HybridMetric(
        ppl_weight=0.4,
        vote_weight=0.4,
        size_weight=0.2
    )
    ratio = hybrid.compute(cluster_size, representatives, ppl_edit, ppl_gen)
    logger.info(f"   Edit ratio: {ratio:.3f}")
    logger.info(f"   Confidence: {hybrid.get_confidence():.3f}")


def test_selectors():
    """Test selector implementations."""
    logger.info("\n" + "=" * 60)
    logger.info("Testing Selectors")
    logger.info("=" * 60)
    
    # Sample data
    cluster_id = 1
    cluster_size = 10
    representatives = [
        {"slug": "Chart_1", "rank": 0},
        {"slug": "Chart_2", "rank": 1},
    ]
    ppl_edit = {"Chart_1": 15.5, "Chart_2": 18.2}
    ppl_gen = {"Chart_1": 20.3, "Chart_2": 16.1}
    
    # Test Binary Selector
    logger.info("\n1. Testing Binary Selector:")
    binary = BinarySelector(voting_strategy="majority")
    result = binary.select(cluster_id, cluster_size, representatives, ppl_edit, ppl_gen)
    logger.info(f"   Decision: {result.decision}")
    logger.info(f"   Confidence: {result.confidence:.3f}")
    logger.info(f"   Metadata: {result.metadata}")
    
    # Test Budget Allocator with different metrics
    logger.info("\n2. Testing Budget Allocator (Hybrid):")
    allocator = BudgetAllocator(
        metric="hybrid",
        min_ratio=0.2,
        max_ratio=0.8,
        metric_params={
            "ppl_weight": 0.4,
            "vote_weight": 0.4,
            "size_weight": 0.2
        }
    )
    result = allocator.select(cluster_id, cluster_size, representatives, ppl_edit, ppl_gen)
    logger.info(f"   Decision: {result.decision}")
    logger.info(f"   Ratio: {result.ratio}")
    logger.info(f"   Confidence: {result.confidence:.3f}")
    logger.info(f"   Metadata: {result.metadata}")


def test_adaptive_representatives():
    """Test adaptive representatives calculation."""
    logger.info("\n" + "=" * 60)
    logger.info("Testing Adaptive Representatives")
    logger.info("=" * 60)
    
    adaptive = AdaptiveRepresentatives(divisor=3, max_reps=7, min_reps=1)
    
    # Sample cluster sizes
    cluster_sizes = {
        0: 2,   # Small cluster
        1: 5,   # Small cluster
        2: 10,  # Medium cluster
        3: 15,  # Medium cluster
        4: 30,  # Large cluster
    }
    
    reps_per_cluster = adaptive.compute(cluster_sizes)
    
    logger.info("\nCluster size → Representatives mapping:")
    for cid, size in sorted(cluster_sizes.items()):
        reps = reps_per_cluster[cid]
        logger.info(f"   Cluster {cid}: size={size:2d} → reps={reps}")
    
    # Show lookup table
    logger.info("\nLookup table (size → reps):")
    table = adaptive.get_table(max_cluster_size=20)
    for i in range(0, len(table), 5):
        entries = table[i:i+5]
        line = "   " + ", ".join(f"{s}→{r}" for s, r in entries)
        logger.info(line)


def test_outlier_handler():
    """Test outlier detection and merging."""
    logger.info("\n" + "=" * 60)
    logger.info("Testing Outlier Handler")
    logger.info("=" * 60)
    
    handler = OutlierHandler(threshold=2, merge_strategy="single")
    
    # Sample cluster sizes
    cluster_sizes = {
        0: 1,   # Outlier
        1: 2,   # Outlier
        2: 10,  # Normal
        3: 1,   # Outlier
        4: 15,  # Normal
    }
    
    logger.info("\nCluster sizes:")
    for cid, size in sorted(cluster_sizes.items()):
        logger.info(f"   Cluster {cid}: {size}")
    
    # Detect outliers
    outliers, normal = handler.detect_outliers(cluster_sizes)
    logger.info(f"\nOutlier clusters (size <= 2): {outliers}")
    logger.info(f"Normal clusters: {normal}")
    
    # Merge outliers
    mapping = handler.merge_outliers(outliers)
    logger.info(f"\nMerge mapping: {mapping}")
    
    # Apply to assignments
    assignments = {
        "Chart_1": 0,  # Outlier cluster
        "Chart_2": 2,  # Normal cluster
        "Chart_3": 1,  # Outlier cluster
        "Chart_4": 4,  # Normal cluster
    }
    
    logger.info(f"\nOriginal assignments: {assignments}")
    updated = handler.apply_mapping(assignments, mapping)
    logger.info(f"Updated assignments: {updated}")


def test_end_to_end():
    """Test end-to-end selection flow."""
    logger.info("\n" + "=" * 60)
    logger.info("Testing End-to-End Selection Flow")
    logger.info("=" * 60)
    
    # Simulate complete workflow
    logger.info("\n1. Setup:")
    
    # Cluster data
    cluster_sizes = {0: 2, 1: 5, 2: 10, 3: 15}
    logger.info(f"   Cluster sizes: {cluster_sizes}")
    
    # Adaptive representatives
    adaptive = AdaptiveRepresentatives(divisor=3, max_reps=7)
    reps_per_cluster = adaptive.compute(cluster_sizes)
    logger.info(f"   Representatives per cluster: {reps_per_cluster}")
    
    # Outlier detection
    handler = OutlierHandler(threshold=2)
    outliers, normal = handler.detect_outliers(cluster_sizes)
    logger.info(f"   Outliers: {outliers}, Normal: {normal}")
    
    logger.info("\n2. Selection for each cluster:")
    
    # Budget allocator
    allocator = BudgetAllocator(metric="hybrid", min_ratio=0.2, max_ratio=0.8)
    
    # Sample PPL data
    all_ppl_edit = {
        f"Bug_{i}": 15.0 + i * 0.5 for i in range(32)
    }
    all_ppl_gen = {
        f"Bug_{i}": 18.0 + i * 0.3 for i in range(32)
    }
    
    # Select for each cluster
    for cid in sorted(cluster_sizes.keys()):
        n_reps = reps_per_cluster[cid]
        
        # Simulate representatives
        representatives = [
            {"slug": f"Bug_{cid*10 + i}", "rank": i}
            for i in range(n_reps)
        ]
        
        result = allocator.select(
            cid, cluster_sizes[cid], representatives,
            all_ppl_edit, all_ppl_gen
        )
        
        logger.info(
            f"\n   Cluster {cid} (size={cluster_sizes[cid]}, reps={n_reps}):"
        )
        logger.info(f"      Decision: {result.decision}")
        if result.ratio:
            logger.info(
                f"      Ratio: edit={result.ratio['edit']:.2f}, "
                f"gen={result.ratio['gen']:.2f}"
            )
        logger.info(f"      Confidence: {result.confidence:.3f}")


def main():
    """Run all tests."""
    logger.info("Starting BTMS Enhanced Routing Tests\n")
    
    try:
        test_metrics()
        test_selectors()
        test_adaptive_representatives()
        test_outlier_handler()
        test_end_to_end()
        
        logger.info("\n" + "=" * 60)
        logger.info("All tests completed successfully!")
        logger.info("=" * 60)
        
        return 0
        
    except Exception as e:
        logger.error(f"\nTest failed: {e}", exc_info=True)
        return 1


if __name__ == '__main__':
    sys.exit(main())
