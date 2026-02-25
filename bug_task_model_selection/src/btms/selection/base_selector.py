"""Base selector interface for task modeling selection.

This module provides the abstract base class for all task modeling selectors,
both binary (edit/gen) and budget allocation (ratio-based).
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class SelectionResult:
    """Result of task modeling selection for a cluster.
    
    Attributes:
        cluster_id: Cluster identifier.
        decision: Primary decision ("edit", "gen", or "mixed").
        ratio: Optional ratio allocation {"edit": 0.6, "gen": 0.4}.
        confidence: Confidence score [0, 1].
        metadata: Additional information about the selection.
    """
    
    cluster_id: int
    decision: str  # "edit", "gen", or "mixed"
    ratio: Optional[Dict[str, float]] = None
    confidence: Optional[float] = None
    metadata: Optional[Dict[str, Any]] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary format."""
        return {
            "cluster_id": self.cluster_id,
            "decision": self.decision,
            "ratio": self.ratio,
            "confidence": self.confidence,
            "metadata": self.metadata
        }


class BaseSelector(ABC):
    """Abstract base class for task modeling selectors.
    
    All selectors (binary and budget allocation) must implement the select()
    method which takes cluster information and PPL data and returns a
    SelectionResult.
    """
    
    @abstractmethod
    def select(
        self,
        cluster_id: int,
        cluster_size: int,
        representatives: List[Dict[str, Any]],
        ppl_edit: Dict[str, float],
        ppl_gen: Dict[str, float]
    ) -> SelectionResult:
        """Select task modeling strategy for a cluster.
        
        Args:
            cluster_id: Cluster identifier.
            cluster_size: Total number of bugs in the cluster.
            representatives: List of representative dicts with 'slug', 'rank', etc.
            ppl_edit: PPL scores for edit mode {slug: ppl_score}.
            ppl_gen: PPL scores for gen mode {slug: ppl_score}.
            
        Returns:
            SelectionResult with decision and optional ratio allocation.
        """
        pass
