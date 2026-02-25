"""Mathematical utility functions for BTMS pipeline."""

from __future__ import annotations

import numpy as np


def l2_normalize_rows(x: np.ndarray, *, eps: float = 1e-12) -> np.ndarray:
    """L2 normalize each row of a matrix.
    
    Args:
        x: Input matrix of shape (N, D)
        eps: Small value to avoid division by zero
        
    Returns:
        Normalized matrix of shape (N, D)
    """
    norms = np.linalg.norm(x, axis=1, keepdims=True)
    norms = np.maximum(norms, eps)
    return x / norms


def l2_normalize_vec(x: np.ndarray, *, eps: float = 1e-12) -> np.ndarray:
    """L2 normalize a single vector.
    
    Args:
        x: Input vector of shape (D,)
        eps: Small value to avoid division by zero
        
    Returns:
        Normalized vector of shape (D,)
    """
    n = float(np.linalg.norm(x))
    if n <= eps:
        return x
    return x / n


def cosine_distance(a: np.ndarray, b: np.ndarray) -> float:
    """Compute cosine distance between two vectors.
    
    Args:
        a: First vector
        b: Second vector
        
    Returns:
        Cosine distance (1 - cosine_similarity)
    """
    a_norm = l2_normalize_vec(a)
    b_norm = l2_normalize_vec(b)
    return 1.0 - float(np.dot(a_norm, b_norm))


def euclidean_distance(a: np.ndarray, b: np.ndarray) -> float:
    """Compute Euclidean distance between two vectors.
    
    Args:
        a: First vector
        b: Second vector
        
    Returns:
        Euclidean distance
    """
    return float(np.linalg.norm(a - b))
