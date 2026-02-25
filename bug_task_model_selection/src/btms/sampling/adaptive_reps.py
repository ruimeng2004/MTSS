"""Adaptive representatives module for dynamic sampling.

This module provides functionality to dynamically determine the number
of representatives per cluster based on cluster size.
"""

from __future__ import annotations

import logging
from typing import Dict, List

logger = logging.getLogger(__name__)


class AdaptiveRepresentatives:
    """Compute adaptive number of representatives per cluster.
    
    Dynamically determines the number of representatives based on
    cluster size using a simple formula:
        reps = min(max(1, cluster_size // divisor), max_reps)
    """
    
    def __init__(
        self,
        divisor: int = 3,
        max_reps: int = 7,
        min_reps: int = 1
    ):
        """Initialize adaptive representatives calculator.
        
        Args:
            divisor: Cluster size divided by this to get base reps.
            max_reps: Maximum representatives per cluster.
            min_reps: Minimum representatives per cluster.
            
        Examples:
            With divisor=3, max_reps=7:
            - cluster_size=1-2  → reps=1
            - cluster_size=3-5  → reps=1
            - cluster_size=6-8  → reps=2
            - cluster_size=9-11 → reps=3
            - cluster_size=21+  → reps=7 (capped)
        """
        self.divisor = divisor
        self.max_reps = max_reps
        self.min_reps = min_reps
        
        logger.info(
            f"Initialized AdaptiveRepresentatives: "
            f"divisor={divisor}, max_reps={max_reps}, min_reps={min_reps}"
        )
    
    def compute(
        self,
        cluster_sizes: Dict[int, int]
    ) -> Dict[int, int]:
        """Compute number of representatives for each cluster.
        
        Args:
            cluster_sizes: Mapping from cluster_id to cluster size.
            
        Returns:
            Mapping from cluster_id to number of representatives.
        """
        reps_per_cluster: Dict[int, int] = {}
        
        for cluster_id, size in cluster_sizes.items():
            reps = self._compute_for_size(size)
            reps_per_cluster[cluster_id] = reps
        
        # Log statistics
        if reps_per_cluster:
            values = list(reps_per_cluster.values())
            logger.info(
                f"Adaptive representatives computed: "
                f"mean={sum(values)/len(values):.1f}, "
                f"min={min(values)}, max={max(values)}"
            )
        
        return reps_per_cluster
    
    def _compute_for_size(self, cluster_size: int) -> int:
        """Compute number of representatives for a specific cluster size.
        
        Args:
            cluster_size: Size of the cluster.
            
        Returns:
            Number of representatives.
        """
        if cluster_size <= 0:
            return self.min_reps
        
        # Formula: reps = min(max(min_reps, cluster_size // divisor), max_reps)
        reps = max(self.min_reps, cluster_size // self.divisor)
        reps = min(reps, self.max_reps)
        
        return reps
    
    def get_table(
        self,
        max_cluster_size: int = 50
    ) -> List[tuple[int, int]]:
        """Get a lookup table for cluster size to reps mapping.
        
        Args:
            max_cluster_size: Maximum cluster size to include.
            
        Returns:
            List of (cluster_size, num_reps) tuples.
        """
        table = []
        for size in range(1, max_cluster_size + 1):
            reps = self._compute_for_size(size)
            table.append((size, reps))
        return table
