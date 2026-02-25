"""Selection engine for BTMS pipeline."""

from .selector import TaskModelSelector, load_ppl_scores
from .voting import VoteResult, VotingMechanism
from .base_selector import BaseSelector, SelectionResult
from .budget_allocator import BudgetAllocator
from .budget_metrics import (
    BudgetMetric,
    PPLGapMetric,
    VoteConsistencyMetric,
    SizeAdjustedMetric,
    HybridMetric
)
from .enhanced_selector import EnhancedTaskModelSelector, BinarySelector

__all__ = [
    # Original classes
    "TaskModelSelector",
    "load_ppl_scores",
    "VoteResult",
    "VotingMechanism",
    # New budget allocation classes
    "BaseSelector",
    "SelectionResult",
    "BudgetAllocator",
    "BudgetMetric",
    "PPLGapMetric",
    "VoteConsistencyMetric",
    "SizeAdjustedMetric",
    "HybridMetric",
    "EnhancedTaskModelSelector",
    "BinarySelector",
]

