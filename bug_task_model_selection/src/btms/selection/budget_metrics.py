"""Budget allocation metrics for task modeling selection.

This module implements four different metrics for computing budget allocation
ratios between edit and gen modes:
1. PPL Gap - Based on perplexity difference
2. Vote Consistency - Combines voting with PPL gap confidence
3. Size Adjusted - Adjusts ratio based on cluster size reliability
4. Hybrid - Weighted combination of all three signals
"""

from __future__ import annotations

import math
from abc import ABC, abstractmethod
from typing import Dict, List, Tuple


class BudgetMetric(ABC):
    """Abstract base class for budget allocation metrics."""
    
    def __init__(self):
        self.confidence = 0.0
    
    @abstractmethod
    def compute(
        self,
        cluster_size: int,
        representatives: List[Dict[str, any]],
        ppl_edit: Dict[str, float],
        ppl_gen: Dict[str, float]
    ) -> float:
        """Compute edit ratio [0, 1].
        
        Args:
            cluster_size: Total number of bugs in cluster.
            representatives: List of representative dicts.
            ppl_edit: Edit PPL scores by slug.
            ppl_gen: Gen PPL scores by slug.
            
        Returns:
            Edit ratio in [0, 1] range.
        """
        pass
    
    def get_confidence(self) -> float:
        """Get confidence score for the last computation."""
        return self.confidence


class PPLGapMetric(BudgetMetric):
    """Budget allocation based on PPL gap.
    
    Uses sigmoid function to convert PPL difference into a ratio.
    Larger gap means more confidence in the preferred mode.
    """
    
    def __init__(self, temperature: float = 1.0):
        """Initialize PPL Gap metric.
        
        Args:
            temperature: Temperature for sigmoid scaling (default 1.0).
        """
        super().__init__()
        self.temperature = temperature
    
    def compute(
        self,
        cluster_size: int,
        representatives: List[Dict[str, any]],
        ppl_edit: Dict[str, float],
        ppl_gen: Dict[str, float]
    ) -> float:
        """Compute edit ratio using PPL gap.
        
        Formula:
            avg_edit = mean(edit PPLs)
            avg_gen = mean(gen PPLs)
            gap = avg_edit - avg_gen
            ratio_edit = sigmoid(-gap / temperature)
        
        Returns:
            Edit ratio in [0, 1].
        """
        edit_ppls = []
        gen_ppls = []
        
        for rep in representatives:
            slug = rep.get("slug")
            if slug in ppl_edit and slug in ppl_gen:
                edit_ppls.append(ppl_edit[slug])
                gen_ppls.append(ppl_gen[slug])
        
        if not edit_ppls:
            self.confidence = 0.0
            return 0.5
        
        avg_edit = sum(edit_ppls) / len(edit_ppls)
        avg_gen = sum(gen_ppls) / len(gen_ppls)
        
        gap = avg_edit - avg_gen
        ratio_edit = self._sigmoid(-gap / self.temperature)
        
        # Confidence based on gap magnitude
        self.confidence = min(abs(gap) / 10.0, 1.0)
        
        return ratio_edit
    
    @staticmethod
    def _sigmoid(x: float) -> float:
        """Sigmoid function."""
        return 1.0 / (1.0 + math.exp(-x))


class VoteConsistencyMetric(BudgetMetric):
    """Budget allocation combining voting with PPL gap confidence.
    
    Uses discrete voting as base signal, modulated by continuous
    PPL gap confidence.
    """
    
    def __init__(self, confidence_threshold: float = 0.5):
        """Initialize Vote Consistency metric.
        
        Args:
            confidence_threshold: Threshold for PPL gap confidence.
        """
        super().__init__()
        self.confidence_threshold = confidence_threshold
    
    def compute(
        self,
        cluster_size: int,
        representatives: List[Dict[str, any]],
        ppl_edit: Dict[str, float],
        ppl_gen: Dict[str, float]
    ) -> float:
        """Compute edit ratio using vote consistency.
        
        Formula:
            edit_votes = count(edit_ppl < gen_ppl)
            base_ratio = edit_votes / total_reps
            avg_gap = mean(|edit_ppl - gen_ppl|)
            confidence = min(avg_gap / threshold, 1.0)
            ratio_edit = 0.5 + (base_ratio - 0.5) * confidence
        
        Returns:
            Edit ratio in [0, 1].
        """
        edit_votes = 0
        gaps = []
        
        for rep in representatives:
            slug = rep.get("slug")
            if slug in ppl_edit and slug in ppl_gen:
                edit_ppl = ppl_edit[slug]
                gen_ppl = ppl_gen[slug]
                
                if edit_ppl < gen_ppl:
                    edit_votes += 1
                
                gaps.append(abs(edit_ppl - gen_ppl))
        
        if not gaps:
            self.confidence = 0.0
            return 0.5
        
        # Base ratio from voting
        base_ratio = edit_votes / len(gaps)
        
        # Confidence from PPL gap magnitude
        avg_gap = sum(gaps) / len(gaps)
        confidence = min(avg_gap / self.confidence_threshold, 1.0)
        
        # Adjust ratio based on confidence
        # High confidence → ratio close to base_ratio
        # Low confidence → ratio close to 0.5
        ratio_edit = 0.5 + (base_ratio - 0.5) * confidence
        
        self.confidence = confidence
        return ratio_edit


class SizeAdjustedMetric(BudgetMetric):
    """Budget allocation adjusted for cluster size reliability.
    
    Larger clusters get more confident allocations, smaller clusters
    are pulled toward conservative 0.5 split.
    """
    
    def __init__(self, size_normalization_factor: int = 10):
        """Initialize Size Adjusted metric.
        
        Args:
            size_normalization_factor: Cluster size for full confidence.
        """
        super().__init__()
        self.size_norm = size_normalization_factor
    
    def compute(
        self,
        cluster_size: int,
        representatives: List[Dict[str, any]],
        ppl_edit: Dict[str, float],
        ppl_gen: Dict[str, float]
    ) -> float:
        """Compute edit ratio with size adjustment.
        
        Formula:
            edit_votes = count(edit_ppl < gen_ppl)
            vote_ratio = edit_votes / total_reps
            size_factor = min(cluster_size / size_norm, 1.0)
            ratio_edit = 0.5 + (vote_ratio - 0.5) * size_factor
        
        Returns:
            Edit ratio in [0, 1].
        """
        edit_votes = 0
        total = 0
        
        for rep in representatives:
            slug = rep.get("slug")
            if slug in ppl_edit and slug in ppl_gen:
                if ppl_edit[slug] < ppl_gen[slug]:
                    edit_votes += 1
                total += 1
        
        if total == 0:
            self.confidence = 0.0
            return 0.5
        
        vote_ratio = edit_votes / total
        
        # Size-based confidence
        size_factor = min(cluster_size / self.size_norm, 1.0)
        
        # Adjust ratio
        ratio_edit = 0.5 + (vote_ratio - 0.5) * size_factor
        
        self.confidence = size_factor
        return ratio_edit


class HybridMetric(BudgetMetric):
    """Hybrid budget allocation combining all three signals.
    
    Weighted combination of PPL gap, voting, and size adjustment.
    """
    
    def __init__(
        self,
        ppl_weight: float = 0.4,
        vote_weight: float = 0.4,
        size_weight: float = 0.2,
        temperature: float = 1.0,
        confidence_threshold: float = 0.5,
        size_normalization_factor: int = 10
    ):
        """Initialize Hybrid metric.
        
        Args:
            ppl_weight: Weight for PPL gap component.
            vote_weight: Weight for voting component.
            size_weight: Weight for size component.
            temperature: Temperature for PPL sigmoid.
            confidence_threshold: Threshold for vote confidence.
            size_normalization_factor: Cluster size for full confidence.
        """
        super().__init__()
        
        # Normalize weights
        total_weight = ppl_weight + vote_weight + size_weight
        self.ppl_weight = ppl_weight / total_weight
        self.vote_weight = vote_weight / total_weight
        self.size_weight = size_weight / total_weight
        
        # Component metrics
        self.ppl_metric = PPLGapMetric(temperature)
        self.vote_metric = VoteConsistencyMetric(confidence_threshold)
        self.size_metric = SizeAdjustedMetric(size_normalization_factor)
    
    def compute(
        self,
        cluster_size: int,
        representatives: List[Dict[str, any]],
        ppl_edit: Dict[str, float],
        ppl_gen: Dict[str, float]
    ) -> float:
        """Compute edit ratio using hybrid approach.
        
        Combines three components with weighted average:
        1. PPL gap ratio (Raw sigmoid)
        2. Vote ratio (Raw vote percentage)
        3. Size factor (Reliability)
        
        Returns:
            Edit ratio in [0, 1].
        """
        # 1. Collect Raw Data
        edit_votes = 0
        gaps = []
        edit_ppls = []
        gen_ppls = []
        total_reps = 0
        
        for rep in representatives:
            slug = rep.get("slug")
            if slug in ppl_edit and slug in ppl_gen:
                e_ppl = ppl_edit[slug]
                g_ppl = ppl_gen[slug]
                
                edit_ppls.append(e_ppl)
                gen_ppls.append(g_ppl)
                gaps.append(abs(e_ppl - g_ppl))
                
                if e_ppl < g_ppl:
                    edit_votes += 1
                total_reps += 1
        
        if total_reps == 0:
            self.confidence = 0.0
            return 0.5

        # 2. Compute Components
        
        # Component 1: PPL Gap
        avg_edit = sum(edit_ppls) / len(edit_ppls)
        avg_gen = sum(gen_ppls) / len(gen_ppls)
        gap = avg_edit - avg_gen
        ppl_ratio = self.ppl_metric._sigmoid(-gap / self.ppl_metric.temperature)
        
        # Component 2: Vote
        vote_ratio = edit_votes / total_reps
        
        # Component 3: Size
        size_factor = min(cluster_size / self.size_metric.size_norm, 1.0)
        
        # 3. Compute Confidences
        
        # PPL Confidence (adjusted scaling factor based on actual data distribution)
        # Data shows PPL gaps range from 0.0002 to 0.14, avg ~0.017
        # Using 0.15 as scaling factor to achieve reasonable confidence distribution
        ppl_conf = min(abs(gap) / 0.15, 1.0)
        
        # Vote Confidence
        avg_gap = sum(gaps) / len(gaps) if gaps else 0
        vote_conf = min(avg_gap / self.vote_metric.confidence_threshold, 1.0)
        
        # Size Confidence (is the factor itself)
        size_conf = size_factor
        
        # 4. Synthesize
        
        # Overall confidence (weighted average)
        overall_confidence = (
            ppl_conf * self.ppl_weight +
            vote_conf * self.vote_weight +
            size_conf * self.size_weight
        )
        
        # Weighted ratio (Note: size_weight is added to vote_ratio's weight 
        # because size itself doesn't provide a directional 'ratio', it trusts the vote)
        # We use vote_ratio for the size component direction as per design
        weighted_ratio = (
            ppl_ratio * self.ppl_weight +
            vote_ratio * (self.vote_weight + self.size_weight)
        )
        
        # 5. Final Adjustment
        final_ratio = 0.5 + (weighted_ratio - 0.5) * overall_confidence
        
        self.confidence = overall_confidence
        return final_ratio
