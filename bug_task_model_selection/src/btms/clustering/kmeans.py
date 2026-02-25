"""KMeans clustering implementation."""

from __future__ import annotations

import numpy as np
from sklearn.cluster import KMeans

from .base import BaseClusterer, ClusteringConfig, ClusteringResult


class KMeansClusterer(BaseClusterer):
    """KMeans clustering implementation.
    
    Uses sklearn's KMeans with k-means++ initialization.
    """
    
    def __init__(self, config: ClusteringConfig) -> None:
        """Initialize KMeans clusterer.
        
        Args:
            config: Clustering configuration
                Extra params:
                - max_iter: Maximum iterations (default: 300)
                - n_init: Number of initializations (default: 10)
        """
        super().__init__(config)
        self.max_iter = config.extra_params.get("max_iter", 300)
        self.n_init = config.extra_params.get("n_init", 10)
    
    @property
    def name(self) -> str:
        return "kmeans"
    
    def fit(self, vectors: np.ndarray) -> ClusteringResult:
        """Perform KMeans clustering.
        
        Args:
            vectors: Input vectors of shape (N, D)
            
        Returns:
            ClusteringResult with cluster assignments
        """
        self._validate_vectors(vectors)
        vectors = self._preprocess_vectors(vectors)
        
        model = KMeans(
            n_clusters=self.config.n_clusters,
            max_iter=self.max_iter,
            random_state=self.config.seed,
            n_init=self.n_init,
            init="k-means++",
        )
        labels = model.fit_predict(vectors)
        
        # Count actual clusters (some may be empty)
        actual_n_clusters = len(np.unique(labels))
        
        return ClusteringResult(
            labels=labels,
            n_clusters=actual_n_clusters,
            config=self.config,
            metadata={
                "centers": model.cluster_centers_.tolist(),
                "inertia": float(model.inertia_),
                "n_iter": int(model.n_iter_),
            },
        )
