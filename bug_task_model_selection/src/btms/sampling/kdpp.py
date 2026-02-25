"""k-DPP (k-Determinantal Point Process) sampling implementation."""

from __future__ import annotations

import numpy as np

from ..utils.math import l2_normalize_rows
from .base import BaseSampler, SamplingConfig, SamplingResult


class KDPPSampler(BaseSampler):
    """k-DPP sampling implementation.
    
    Uses greedy DPP algorithm based on Cholesky decomposition to select
    diverse representatives that maximize the determinant of the kernel matrix.
    """
    
    def __init__(self, config: SamplingConfig) -> None:
        """Initialize k-DPP sampler.
        
        Args:
            config: Sampling configuration
        """
        super().__init__(config)
    
    @property
    def name(self) -> str:
        return "kdpp"
    
    def sample(
        self,
        vectors: np.ndarray,
        cluster_indices: dict[int, np.ndarray],
    ) -> SamplingResult:
        """Select representatives using greedy k-DPP algorithm.
        
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
            
            sub_vectors = vectors[indices]
            cluster_seed = self.config.seed * 1000003 + cid
            
            # Greedy DPP selection
            local_indices = self._greedy_dpp_order(
                X=sub_vectors,
                max_items=self.config.reps_per_cluster,
                seed=cluster_seed,
            )
            
            representatives[cid] = [int(indices[i]) for i in local_indices]
        
        return SamplingResult(representatives=representatives, config=self.config)
    
    def _greedy_dpp_order(
        self,
        X: np.ndarray,
        max_items: int,
        seed: int,
    ) -> list[int]:
        """Greedy DPP sampling algorithm.
        
        Based on Cholesky decomposition, iteratively selects items that
        maximize the determinant of the kernel matrix.
        
        Args:
            X: Vectors of shape (n, d)
            max_items: Maximum number of items to select
            seed: Random seed for tie-breaking
            
        Returns:
            List of local indices of selected items
        """
        if X.ndim != 2:
            raise ValueError(f"X must be 2D, got shape={X.shape}")
        
        n, _ = X.shape
        if n == 0:
            return []
        
        max_items = min(max(1, int(max_items)), n)
        
        # Normalize for cosine similarity kernel
        Xn = l2_normalize_rows(X.astype(np.float32, copy=False))
        
        # Residual norms (diagonal of kernel after projection)
        residual = np.einsum("ij,ij->i", Xn, Xn).astype(np.float64)
        
        selected: list[int] = []
        chosen = np.zeros(n, dtype=bool)
        Q: list[np.ndarray] = []  # Orthonormal basis
        rng = np.random.default_rng(int(seed))
        
        for _ in range(max_items):
            # Add small jitter for tie-breaking
            jitter = rng.uniform(low=0.0, high=1e-9, size=n)
            scores = residual + jitter
            scores[chosen] = -np.inf
            
            i = int(np.argmax(scores))
            if not np.isfinite(scores[i]) or residual[i] <= 1e-14:
                break
            
            selected.append(i)
            chosen[i] = True
            
            # Update orthonormal basis using Gram-Schmidt
            xi = Xn[i].astype(np.float64, copy=False)
            vi = xi.copy()
            for q in Q:
                vi -= float(np.dot(q, xi)) * q
            
            vi_norm2 = float(np.dot(vi, vi))
            if vi_norm2 <= 1e-14:
                continue
            
            q_new = (vi / float(np.sqrt(vi_norm2))).astype(np.float64)
            Q.append(q_new)
            
            # Update residuals
            proj = Xn.astype(np.float64) @ q_new
            residual = residual - proj * proj
            residual = np.maximum(residual, 0.0)
        
        return selected
