"""Outlier detection and merging for small clusters.

This module provides functionality to detect small outlier clusters
and merge them into larger groups.
"""

from __future__ import annotations

import logging
from typing import Dict, List, Optional, Tuple

import numpy as np
from scipy.cluster.hierarchy import linkage, fcluster
from scipy.spatial.distance import pdist, squareform

logger = logging.getLogger(__name__)


class OutlierHandler:
    """Detect and merge small outlier clusters.
    
    Small clusters (size <= threshold) are considered outliers.
    They can be merged into a single "outlier" cluster or grouped
    by similarity.
    """
    
    def __init__(
        self,
        threshold: int = 2,
        merge_strategy: str = "single",
        similarity_threshold: float = 0.3,
        similarity_linkage: str = "average"
    ):
        """Initialize outlier handler.
        
        Args:
            threshold: Clusters with size <= threshold are outliers.
            merge_strategy: "single" (merge all into one) or 
                           "similarity" (group by similarity).
            similarity_threshold: Distance threshold for similarity-based grouping.
            similarity_linkage: Linkage method ('average', 'complete', 'single').
        """
        self.threshold = threshold
        self.merge_strategy = merge_strategy
        self.similarity_threshold = similarity_threshold
        self.similarity_linkage = similarity_linkage
        
        logger.info(
            f"Initialized OutlierHandler: threshold={threshold}, "
            f"strategy={merge_strategy}"
        )
    
    def detect_outliers(
        self,
        cluster_sizes: Dict[int, int]
    ) -> Tuple[List[int], List[int]]:
        """Detect outlier clusters.
        
        Args:
            cluster_sizes: Mapping from cluster_id to cluster size.
            
        Returns:
            Tuple of (outlier_cluster_ids, normal_cluster_ids).
        """
        outliers = []
        normal = []
        
        for cluster_id, size in cluster_sizes.items():
            if size <= self.threshold:
                outliers.append(cluster_id)
            else:
                normal.append(cluster_id)
        
        logger.info(
            f"Detected {len(outliers)} outlier clusters "
            f"(size <= {self.threshold})"
        )
        
        return outliers, normal
    
    def merge_outliers(
        self,
        outlier_ids: List[int],
        cluster_centers: Optional[np.ndarray] = None,
        cluster_id_to_idx: Optional[Dict[int, int]] = None
    ) -> Dict[int, int]:
        """Merge outlier clusters.
        
        Args:
            outlier_ids: List of outlier cluster IDs.
            cluster_centers: Optional cluster center vectors for similarity merging.
            cluster_id_to_idx: Optional mapping from cluster_id to center index.
            
        Returns:
            Mapping from old_cluster_id to new_cluster_id.
        """
        if not outlier_ids:
            logger.info("No outliers to merge")
            return {}
        
        if self.merge_strategy == "single":
            # Merge all outliers into a single group
            return self._merge_single(outlier_ids)
        
        elif self.merge_strategy == "similarity":
            # Group outliers by similarity
            if cluster_centers is None or cluster_id_to_idx is None:
                logger.warning(
                    "Similarity-based merging requires cluster_centers "
                    "and cluster_id_to_idx. Falling back to single merge."
                )
                return self._merge_single(outlier_ids)
            
            return self._merge_by_similarity(
                outlier_ids, cluster_centers, cluster_id_to_idx
            )
        
        else:
            raise ValueError(f"Unknown merge strategy: {self.merge_strategy}")
    
    def _merge_single(
        self,
        outlier_ids: List[int]
    ) -> Dict[int, int]:
        """Merge all outliers into a single cluster.
        
        Args:
            outlier_ids: List of outlier cluster IDs.
            
        Returns:
            Mapping from old_cluster_id to new_cluster_id.
        """
        if not outlier_ids:
            return {}
        
        # Use a negative ID for the merged outlier cluster
        merged_id = -1
        mapping = {old_id: merged_id for old_id in outlier_ids}
        
        logger.info(
            f"Merged {len(outlier_ids)} outliers into single cluster {merged_id}"
        )
        
        return mapping
    
    def _merge_by_similarity(
        self,
        outlier_ids: List[int],
        cluster_centers: np.ndarray,
        cluster_id_to_idx: Dict[int, int]
    ) -> Dict[int, int]:
        """Group outliers by similarity.
        
        Args:
            outlier_ids: List of outlier cluster IDs.
            cluster_centers: Cluster center vectors (N, D).
            cluster_id_to_idx: Mapping from cluster_id to center index.
            
        Returns:
            Mapping from old_cluster_id to new_cluster_id.
        """
        if len(outlier_ids) <= 1:
            return {}
        
        # Get outlier centers
        outlier_indices = [
            cluster_id_to_idx[cid] for cid in outlier_ids
            if cid in cluster_id_to_idx
        ]
        
        if len(outlier_indices) <= 1:
            return self._merge_single(outlier_ids)
        
        outlier_centers = cluster_centers[outlier_indices]
        
        # Compute pairwise distances
        distances = pdist(outlier_centers, metric='cosine')
        
        # Hierarchical clustering
        Z = linkage(distances, method=self.similarity_linkage)
        
        # Cut dendrogram at threshold
        labels = fcluster(
            Z, 
            self.similarity_threshold, 
            criterion='distance'
        )
        
        # Create mapping (use negative IDs for merged groups)
        mapping = {}
        for i, old_id in enumerate(outlier_ids):
            if i < len(labels):
                new_id = -labels[i]  # Negative to distinguish from normal clusters
                mapping[old_id] = new_id
        
        n_groups = len(set(labels))
        logger.info(
            f"Grouped {len(outlier_ids)} outliers into {n_groups} "
            f"similarity-based groups"
        )
        
        return mapping
    
    def apply_mapping(
        self,
        assignments: Dict[str, int],
        mapping: Dict[int, int]
    ) -> Dict[str, int]:
        """Apply cluster ID mapping to assignments.
        
        Args:
            assignments: Original assignments {slug: cluster_id}.
            mapping: Cluster ID mapping {old_id: new_id}.
            
        Returns:
            Updated assignments {slug: cluster_id}.
        """
        if not mapping:
            return assignments
        
        updated = {}
        for slug, cluster_id in assignments.items():
            updated[slug] = mapping.get(cluster_id, cluster_id)
        
        return updated
