"""Base classes for sampling algorithms."""

from __future__ import annotations

import json
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import numpy as np

from ..utils.math import l2_normalize_rows


@dataclass
class SamplingConfig:
    """Configuration for sampling algorithms.
    
    Attributes:
        reps_per_cluster: Number of representatives to select per cluster
        metric: Distance metric ('cosine' or 'euclidean')
        seed: Random seed for reproducibility
        extra_params: Algorithm-specific parameters
    """
    reps_per_cluster: int = 1
    metric: str = "cosine"
    seed: int = 42
    extra_params: dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self) -> None:
        if self.reps_per_cluster <= 0:
            raise ValueError(f"reps_per_cluster must be > 0, got {self.reps_per_cluster}")
        if self.metric not in {"cosine", "euclidean"}:
            raise ValueError(f"metric must be 'cosine' or 'euclidean', got {self.metric}")
        if self.extra_params is None:
            self.extra_params = {}


@dataclass
class SamplingResult:
    """Result of a sampling operation.
    
    Attributes:
        representatives: Mapping from cluster_id to list of global vector indices
        config: Configuration used for sampling
    """
    representatives: dict[int, list[int]]
    config: SamplingConfig


class BaseSampler(ABC):
    """Abstract base class for sampling algorithms.
    
    All sampling algorithms should inherit from this class and implement
    the `sample` method.
    """
    
    def __init__(self, config: SamplingConfig) -> None:
        """Initialize the sampler.
        
        Args:
            config: Sampling configuration
        """
        self.config = config
    
    @property
    @abstractmethod
    def name(self) -> str:
        """Return the algorithm name."""
        pass
    
    @abstractmethod
    def sample(
        self,
        vectors: np.ndarray,
        cluster_indices: dict[int, np.ndarray],
    ) -> SamplingResult:
        """Select representatives from each cluster.
        
        Args:
            vectors: All vectors of shape (N, D)
            cluster_indices: Mapping from cluster_id to array of vector indices
            
        Returns:
            SamplingResult containing selected representatives
        """
        pass
    
    def _preprocess_vectors(self, vectors: np.ndarray) -> np.ndarray:
        """Preprocess vectors before sampling.
        
        Args:
            vectors: Input vectors
            
        Returns:
            Preprocessed vectors
        """
        vectors = np.asarray(vectors, dtype=np.float32)
        if self.config.metric == "cosine":
            vectors = l2_normalize_rows(vectors)
        return vectors
    
    @staticmethod
    def _meta_to_dict(m: Any) -> dict[str, Any]:
        """Convert metadata object to dictionary.
        
        Args:
            m: Metadata object (dict, dataclass, or object with attributes)
            
        Returns:
            Dictionary representation
        """
        if m is None:
            return {}
        if isinstance(m, dict):
            return dict(m)
        
        out: dict[str, Any] = {}
        for k in [
            "item_id",
            "slug",
            "view",
            "source_file",
            "tokens",
            "embedding_model",
            "embedding_proxy",
        ]:
            if hasattr(m, k):
                out[k] = getattr(m, k)
        return out
    
    def export_representatives(
        self,
        result: SamplingResult,
        ids: list[str],
        meta: dict[str, Any],
        out_path: Path,
    ) -> None:
        """Export representatives to JSONL file.
        
        Args:
            result: Sampling result
            ids: Item IDs corresponding to each vector
            meta: Metadata mapping item_id -> metadata
            out_path: Output file path
        """
        out_path.parent.mkdir(parents=True, exist_ok=True)
        with out_path.open("w", encoding="utf-8") as f:
            for cid in sorted(result.representatives.keys()):
                indices = result.representatives[cid]
                for rank, idx in enumerate(indices, start=1):
                    item_id = ids[idx]
                    md = self._meta_to_dict(meta.get(item_id))
                    f.write(
                        json.dumps(
                            {
                                "cluster_id": cid,
                                "rank": rank,
                                "item_id": item_id,
                                **md,
                            },
                            ensure_ascii=False,
                        )
                        + "\n"
                    )
    
    def export_summary(
        self,
        result: SamplingResult,
        ids: list[str],
        out_path: Path,
    ) -> None:
        """Export cluster summary to JSON file.
        
        Args:
            result: Sampling result
            ids: Item IDs corresponding to each vector
            out_path: Output file path
        """
        summary: dict[str, dict[str, Any]] = {}
        for cid, indices in result.representatives.items():
            rep_ids = [ids[idx] for idx in indices]
            summary[str(cid)] = {
                "cluster_id": cid,
                "size": len(indices),
                "representatives": rep_ids,
            }
        
        out_path.parent.mkdir(parents=True, exist_ok=True)
        with out_path.open("w", encoding="utf-8") as f:
            json.dump(summary, f, ensure_ascii=False, indent=2)


def build_cluster_indices(labels: np.ndarray) -> dict[int, np.ndarray]:
    """Build mapping from cluster_id to vector indices.
    
    Args:
        labels: Cluster labels for each vector
        
    Returns:
        Mapping from cluster_id to array of vector indices
    """
    cluster_indices: dict[int, list[int]] = {}
    for idx, label in enumerate(labels):
        cid = int(label)
        cluster_indices.setdefault(cid, []).append(idx)
    
    return {cid: np.array(indices, dtype=np.int64) for cid, indices in cluster_indices.items()}
