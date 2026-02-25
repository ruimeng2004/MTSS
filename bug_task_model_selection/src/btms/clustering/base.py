"""Base classes for clustering algorithms."""

from __future__ import annotations

import json
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import numpy as np

from ..utils.math import l2_normalize_rows


@dataclass
class ClusteringConfig:
    """Configuration for clustering algorithms.
    
    Attributes:
        n_clusters: Number of clusters to create
        metric: Distance metric ('cosine' or 'euclidean')
        normalize: Whether to L2 normalize vectors before clustering
        seed: Random seed for reproducibility
        extra_params: Algorithm-specific parameters
    """
    n_clusters: int
    metric: str = "cosine"
    normalize: bool = True
    seed: int = 42
    extra_params: dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self) -> None:
        if self.n_clusters <= 0:
            raise ValueError(f"n_clusters must be > 0, got {self.n_clusters}")
        if self.metric not in {"cosine", "euclidean"}:
            raise ValueError(f"metric must be 'cosine' or 'euclidean', got {self.metric}")
        if self.extra_params is None:
            self.extra_params = {}


@dataclass
class ClusteringResult:
    """Result of a clustering operation.
    
    Attributes:
        labels: Cluster assignment for each sample, shape (n_samples,)
        n_clusters: Actual number of clusters created
        config: Configuration used for clustering
        metadata: Algorithm-specific metadata (e.g., cluster centers)
    """
    labels: np.ndarray
    n_clusters: int
    config: ClusteringConfig
    metadata: dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self) -> None:
        if self.metadata is None:
            self.metadata = {}


class BaseClusterer(ABC):
    """Abstract base class for clustering algorithms.
    
    All clustering algorithms should inherit from this class and implement
    the `fit` method.
    """
    
    def __init__(self, config: ClusteringConfig) -> None:
        """Initialize the clusterer.
        
        Args:
            config: Clustering configuration
        """
        self.config = config
    
    @property
    @abstractmethod
    def name(self) -> str:
        """Return the algorithm name."""
        pass
    
    @abstractmethod
    def fit(self, vectors: np.ndarray) -> ClusteringResult:
        """Perform clustering on the input vectors.
        
        Args:
            vectors: Input vectors of shape (N, D)
            
        Returns:
            ClusteringResult containing cluster assignments and metadata
            
        Raises:
            ValueError: If vectors are invalid or n_clusters > n_samples
        """
        pass
    
    def _validate_vectors(self, vectors: np.ndarray) -> None:
        """Validate input vectors.
        
        Args:
            vectors: Input vectors to validate
            
        Raises:
            ValueError: If vectors are invalid
        """
        if vectors.ndim != 2:
            raise ValueError(f"Expected 2D vectors, got shape {vectors.shape}")
        if vectors.shape[0] == 0:
            raise ValueError("Empty input vectors")
        if self.config.n_clusters > vectors.shape[0]:
            raise ValueError(
                f"n_clusters ({self.config.n_clusters}) > n_samples ({vectors.shape[0]})"
            )
    
    def _preprocess_vectors(self, vectors: np.ndarray) -> np.ndarray:
        """Preprocess vectors before clustering.
        
        Args:
            vectors: Input vectors
            
        Returns:
            Preprocessed vectors
        """
        vectors = np.asarray(vectors, dtype=np.float32)
        if self.config.normalize and self.config.metric == "cosine":
            vectors = l2_normalize_rows(vectors)
        return vectors
    
    def export_assignments(
        self,
        result: ClusteringResult,
        ids: list[str],
        out_path: Path,
    ) -> None:
        """Export cluster assignments to JSONL file.
        
        Args:
            result: Clustering result
            ids: Item IDs corresponding to each vector
            out_path: Output file path
            
        Raises:
            ValueError: If number of IDs doesn't match number of labels
        """
        if len(ids) != len(result.labels):
            raise ValueError(
                f"Number of IDs ({len(ids)}) != number of labels ({len(result.labels)})"
            )
        
        out_path.parent.mkdir(parents=True, exist_ok=True)
        with out_path.open("w", encoding="utf-8") as f:
            for item_id, label in zip(ids, result.labels):
                f.write(
                    json.dumps(
                        {"item_id": item_id, "cluster_id": int(label)},
                        ensure_ascii=False,
                    )
                    + "\n"
                )
    
    def export_clusters_json(
        self,
        result: ClusteringResult,
        ids: list[str],
        out_path: Path,
    ) -> None:
        """Export clusters as JSON mapping cluster_id -> [item_ids].
        
        Args:
            result: Clustering result
            ids: Item IDs corresponding to each vector
            out_path: Output file path
        """
        clusters: dict[str, list[str]] = {}
        for item_id, label in zip(ids, result.labels):
            key = str(int(label))
            clusters.setdefault(key, []).append(item_id)
        
        out_path.parent.mkdir(parents=True, exist_ok=True)
        with out_path.open("w", encoding="utf-8") as f:
            json.dump(clusters, f, ensure_ascii=False, indent=2)
    
    def export_metadata(
        self,
        result: ClusteringResult,
        out_path: Path,
        extra: dict[str, Any] | None = None,
    ) -> None:
        """Export clustering metadata to JSON file.
        
        Args:
            result: Clustering result
            out_path: Output file path
            extra: Additional metadata to include
        """
        meta = {
            "algorithm": self.name,
            "n_clusters": result.n_clusters,
            "n_samples": len(result.labels),
            "metric": self.config.metric,
            "normalize": self.config.normalize,
            "seed": self.config.seed,
            **self.config.extra_params,
        }
        if extra:
            meta.update(extra)
        
        out_path.parent.mkdir(parents=True, exist_ok=True)
        with out_path.open("w", encoding="utf-8") as f:
            json.dump(meta, f, ensure_ascii=False, indent=2)
