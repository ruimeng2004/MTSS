"""Hierarchical Agglomerative Clustering implementation."""

from __future__ import annotations

import warnings

import numpy as np
from sklearn.cluster import AgglomerativeClustering

from .base import BaseClusterer, ClusteringConfig, ClusteringResult


class HACClusterer(BaseClusterer):
    """Hierarchical Agglomerative Clustering implementation.
    
    Supports multiple linkage methods: average, ward, complete, single.
    Note: Ward linkage requires euclidean metric.
    """
    
    SUPPORTED_LINKAGES = {"average", "ward", "complete", "single"}
    
    def __init__(self, config: ClusteringConfig) -> None:
        """Initialize HAC clusterer.
        
        Args:
            config: Clustering configuration
                Extra params:
                - linkage: Linkage method (default: 'average')
        """
        super().__init__(config)
        self.linkage = config.extra_params.get("linkage", "average")
        
        if self.linkage not in self.SUPPORTED_LINKAGES:
            raise ValueError(
                f"Unsupported linkage: {self.linkage}. "
                f"Available: {self.SUPPORTED_LINKAGES}"
            )
        
        # Ward linkage requires euclidean metric
        if self.linkage == "ward" and config.metric == "cosine":
            warnings.warn(
                "Ward linkage requires euclidean metric. "
                "Automatically switching from cosine to euclidean.",
                UserWarning,
            )
    
    @property
    def name(self) -> str:
        return f"hac_{self.linkage}"
    
    def fit(self, vectors: np.ndarray) -> ClusteringResult:
        """Perform HAC clustering.
        
        Args:
            vectors: Input vectors of shape (N, D)
            
        Returns:
            ClusteringResult with cluster assignments
        """
        self._validate_vectors(vectors)
        vectors = self._preprocess_vectors(vectors)
        
        # Ward linkage requires euclidean metric
        if self.linkage == "ward":
            metric = "euclidean"
        else:
            metric = self.config.metric
        
        model = AgglomerativeClustering(
            n_clusters=self.config.n_clusters,
            metric=metric,
            linkage=self.linkage,
        )
        labels = model.fit_predict(vectors)
        
        # Count actual clusters
        actual_n_clusters = len(np.unique(labels))
        
        return ClusteringResult(
            labels=labels,
            n_clusters=actual_n_clusters,
            config=self.config,
            metadata={
                "linkage": self.linkage,
                "metric_used": metric,
            },
        )
