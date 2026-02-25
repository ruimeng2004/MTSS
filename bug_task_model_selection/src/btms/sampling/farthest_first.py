"""Farthest-First sampling implementation."""

from __future__ import annotations

import numpy as np

from ..utils.math import l2_normalize_rows, l2_normalize_vec
from .base import BaseSampler, SamplingConfig, SamplingResult


class FarthestFirstSampler(BaseSampler):
    """Farthest-First sampling implementation.
    
    Selects representatives by starting from the medoid and iteratively
    choosing the point farthest from all previously selected points.
    """
    
    def __init__(self, config: SamplingConfig) -> None:
        """Initialize Farthest-First sampler.
        
        Args:
            config: Sampling configuration
        """
        super().__init__(config)
        self._rng = np.random.default_rng(config.seed)
    
    @property
    def name(self) -> str:
        return "farthest_first"
    
    def sample(
        self,
        vectors: np.ndarray,
        cluster_indices: dict[int, np.ndarray],
    ) -> SamplingResult:
        """Select representatives using Farthest-First algorithm.
        
        Args:
            vectors: All vectors of shape (N, D)
            cluster_indices: Mapping from cluster_id to array of vector indices
            
        Returns:
            SamplingResult containing selected representatives
        """
        vectors = self._preprocess_vectors(vectors)
        representatives: dict[int, list[int]] = {}
        
        for cid, indices in cluster_indices.items():
            if len(indices) == 0:
                continue
            
            # Sort indices for deterministic ordering
            indices = np.array(sorted(indices.tolist()), dtype=np.int64)
            
            # Select medoid as starting point
            medoid = self._select_medoid(vectors, indices)
            
            # Farthest-first selection
            chosen = self._farthest_first(
                vectors=vectors,
                indices=indices,
                start_index=medoid,
                k=self.config.reps_per_cluster,
            )
            representatives[cid] = chosen
        
        return SamplingResult(representatives=representatives, config=self.config)
    
    def _select_medoid(
        self,
        vectors: np.ndarray,
        indices: np.ndarray,
    ) -> int:
        """Select the medoid (point closest to centroid) from a cluster.
        
        Args:
            vectors: All vectors
            indices: Indices of vectors in this cluster
            
        Returns:
            Global index of the medoid
        """
        sub = vectors[indices]
        centroid = sub.mean(axis=0)
        
        if self.config.metric == "cosine":
            centroid = l2_normalize_vec(centroid)
            sims = sub @ centroid
            best_local = int(np.argmax(sims))
            best_score = float(sims[best_local])
            
            # Stable tie-break
            ties = np.where(np.isclose(sims, best_score))[0]
            if ties.size > 1:
                best_local = int(ties[0])  # First one (indices are sorted)
        else:
            d2 = np.sum((sub - centroid) ** 2, axis=1)
            best_local = int(np.argmin(d2))
            best_score = float(d2[best_local])
            
            ties = np.where(np.isclose(d2, best_score))[0]
            if ties.size > 1:
                best_local = int(ties[0])
        
        return int(indices[best_local])
    
    def _farthest_first(
        self,
        vectors: np.ndarray,
        indices: np.ndarray,
        start_index: int,
        k: int,
    ) -> list[int]:
        """Select k points using farthest-first traversal.
        
        Args:
            vectors: All vectors
            indices: Indices of vectors in this cluster
            start_index: Global index of starting point
            k: Number of points to select
            
        Returns:
            List of global indices of selected points
        """
        chosen: list[int] = [start_index]
        if k <= 1:
            return chosen
        
        # Candidates (excluding start)
        cand = [int(i) for i in indices.tolist() if int(i) != start_index]
        if not cand:
            return chosen
        
        # Initialize min distances to chosen set
        if self.config.metric == "cosine":
            chosen_vec = vectors[start_index]
            min_dist = np.ones(len(cand), dtype=np.float64) - (
                vectors[cand] @ chosen_vec
            ).astype(np.float64)
        else:
            chosen_vec = vectors[start_index]
            min_dist = np.linalg.norm(
                vectors[cand] - chosen_vec, axis=1
            ).astype(np.float64)
        
        while len(chosen) < k and cand:
            best_pos = int(np.argmax(min_dist))
            best_d = float(min_dist[best_pos])
            
            # Stable tie-break (first candidate)
            ties = np.where(np.isclose(min_dist, best_d))[0]
            if ties.size > 1:
                best_pos = int(ties[0])
            
            nxt = cand[best_pos]
            chosen.append(nxt)
            
            # Remove chosen candidate
            cand.pop(best_pos)
            min_dist = np.delete(min_dist, best_pos)
            if not cand:
                break
            
            # Update min distances with new chosen point
            if self.config.metric == "cosine":
                d = np.ones(len(cand), dtype=np.float64) - (
                    vectors[cand] @ vectors[nxt]
                ).astype(np.float64)
            else:
                d = np.linalg.norm(
                    vectors[cand] - vectors[nxt], axis=1
                ).astype(np.float64)
            min_dist = np.minimum(min_dist, d)
        
        return chosen
