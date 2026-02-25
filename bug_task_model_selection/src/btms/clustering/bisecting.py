"""Bisecting KMeans clustering implementation."""

from __future__ import annotations

import numpy as np
from sklearn.cluster import BisectingKMeans

from .base import BaseClusterer, ClusteringConfig, ClusteringResult


class BisectingKMeansClusterer(BaseClusterer):
    """Bisecting KMeans clustering implementation.
    
    Recursively bisects clusters until reaching the target number of clusters.
    """
    
    SUPPORTED_STRATEGIES = {"largest_cluster", "biggest_inertia"}
    
    def __init__(self, config: ClusteringConfig) -> None:
        """Initialize Bisecting KMeans clusterer.
        
        Args:
            config: Clustering configuration
                Extra params:
                - bisecting_strategy: Strategy for selecting cluster to bisect
                    ('largest_cluster' or 'biggest_inertia', default: 'largest_cluster')
                - max_iter: Maximum iterations per bisection (default: 300)
                - n_init: Number of initializations per bisection (default: 1)
        """
        super().__init__(config)
        self.bisecting_strategy = config.extra_params.get(
            "bisecting_strategy", "largest_cluster"
        )
        self.max_iter = config.extra_params.get("max_iter", 300)
        self.n_init = config.extra_params.get("n_init", 1)
        
        if self.bisecting_strategy not in self.SUPPORTED_STRATEGIES:
            raise ValueError(
                f"Unsupported bisecting_strategy: {self.bisecting_strategy}. "
                f"Available: {self.SUPPORTED_STRATEGIES}"
            )
    
    @property
    def name(self) -> str:
        return "bisecting_kmeans"
    
    def fit(self, vectors: np.ndarray) -> ClusteringResult:
        """Perform Bisecting KMeans clustering.
        
        Args:
            vectors: Input vectors of shape (N, D)
            
        Returns:
            ClusteringResult with cluster assignments
        """
        self._validate_vectors(vectors)
        vectors = self._preprocess_vectors(vectors)
        
        model = BisectingKMeans(
            n_clusters=self.config.n_clusters,
            random_state=self.config.seed,
            bisecting_strategy=self.bisecting_strategy,
            max_iter=self.max_iter,
            n_init=self.n_init,
            init="k-means++",
        )
        labels = model.fit_predict(vectors)
        
        # Count actual clusters
        actual_n_clusters = len(np.unique(labels))
        
        return ClusteringResult(
            labels=labels,
            n_clusters=actual_n_clusters,
            config=self.config,
            metadata={
                "centers": model.cluster_centers_.tolist(),
                "inertia": float(model.inertia_),
                "bisecting_strategy": self.bisecting_strategy,
            },
        )
