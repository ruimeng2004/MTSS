"""Budget allocator for task modeling selection.

This module implements the BudgetAllocator which computes ratio-based
allocation between edit and gen modes using different metrics.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from .base_selector import BaseSelector, SelectionResult
from .budget_metrics import (
    BudgetMetric,
    PPLGapMetric,
    VoteConsistencyMetric,
    SizeAdjustedMetric,
    HybridMetric
)


class BudgetAllocator(BaseSelector):
    """Budget allocator for edit/gen task modeling selection.
    
    Computes ratio allocation between edit and gen modes based on
    PPL scores and cluster properties.
    """
    
    def __init__(
        self,
        metric: str = "vote_consistency",
        min_ratio: float = 0.2,
        max_ratio: float = 0.8,
        metric_params: Optional[Dict[str, Any]] = None
    ):
        """Initialize BudgetAllocator.
        
        Args:
            metric: Metric name ("ppl_gap", "vote_consistency", 
                    "size_adjusted", "hybrid").
            min_ratio: Minimum allocation for either mode.
            max_ratio: Maximum allocation for either mode.
            metric_params: Parameters for the metric.
        """
        self.metric_name = metric
        self.min_ratio = min_ratio
        self.max_ratio = max_ratio
        self.metric_params = metric_params or {}
        
        # Initialize metric calculator
        self.calculator = self._get_metric_calculator()
    
    def _get_metric_calculator(self) -> BudgetMetric:
        """Get the appropriate metric calculator."""
        if self.metric_name == "ppl_gap":
            temperature = self.metric_params.get("temperature", 1.0)
            return PPLGapMetric(temperature=temperature)
        
        elif self.metric_name == "vote_consistency":
            threshold = self.metric_params.get("confidence_threshold", 0.5)
            return VoteConsistencyMetric(confidence_threshold=threshold)
        
        elif self.metric_name == "size_adjusted":
            size_norm = self.metric_params.get("size_normalization_factor", 10)
            return SizeAdjustedMetric(size_normalization_factor=size_norm)
        
        elif self.metric_name == "hybrid":
            return HybridMetric(
                ppl_weight=self.metric_params.get("ppl_weight", 0.4),
                vote_weight=self.metric_params.get("vote_weight", 0.4),
                size_weight=self.metric_params.get("size_weight", 0.2),
                temperature=self.metric_params.get("temperature", 1.0),
                confidence_threshold=self.metric_params.get(
                    "confidence_threshold", 0.5
                ),
                size_normalization_factor=self.metric_params.get(
                    "size_normalization_factor", 10
                )
            )
        
        else:
            raise ValueError(f"Unknown metric: {self.metric_name}")
    
    def select(
        self,
        cluster_id: int,
        cluster_size: int,
        representatives: List[Dict[str, Any]],
        ppl_edit: Dict[str, float],
        ppl_gen: Dict[str, float]
    ) -> SelectionResult:
        """Select task modeling strategy with ratio allocation.
        
        Args:
            cluster_id: Cluster identifier.
            cluster_size: Total number of bugs in the cluster.
            representatives: List of representative dicts.
            ppl_edit: PPL scores for edit mode.
            ppl_gen: PPL scores for gen mode.
            
        Returns:
            SelectionResult with ratio allocation.
        """
        # Compute raw ratio using the metric
        raw_ratio = self.calculator.compute(
            cluster_size, representatives, ppl_edit, ppl_gen
        )
        
        # Clamp ratio to boundaries
        edit_ratio = self._clamp(raw_ratio, self.min_ratio, self.max_ratio)
        gen_ratio = 1.0 - edit_ratio
        
        # Determine primary decision
        if abs(edit_ratio - 0.5) < 0.05:
            decision = "mixed"
        elif edit_ratio > 0.5:
            decision = "edit"
        else:
            decision = "gen"
        
        # Get confidence
        confidence = self.calculator.get_confidence()
        
        return SelectionResult(
            cluster_id=cluster_id,
            decision=decision,
            ratio={"edit": edit_ratio, "gen": gen_ratio},
            confidence=confidence,
            metadata={
                "metric": self.metric_name,
                "raw_ratio": raw_ratio,
                "clamped": abs(raw_ratio - edit_ratio) > 1e-6,
                "cluster_size": cluster_size,
                "n_representatives": len(representatives)
            }
        )
    
    @staticmethod
    def _clamp(value: float, min_val: float, max_val: float) -> float:
        """Clamp value to [min_val, max_val] range."""
        return max(min_val, min(max_val, value))
