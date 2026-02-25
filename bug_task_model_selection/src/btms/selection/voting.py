"""Voting mechanism for multi-representative selection."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import numpy as np


@dataclass
class VoteResult:
    """Result of a voting operation.
    
    Attributes:
        chosen: The winning strategy name
        votes: Vote counts for each strategy
        mean_scores: Mean PPL scores for each strategy
        n_reps_used: Number of representatives that participated in voting
        vote_details: Detailed voting information for each representative
    """
    chosen: str
    votes: dict[str, int]
    mean_scores: dict[str, float | None]
    n_reps_used: int
    vote_details: list[dict[str, Any]] = field(default_factory=list)


class VotingMechanism:
    """Multi-representative voting mechanism.
    
    Supports multiple voting strategies:
    - majority: Majority voting with mean PPL tie-breaker
    - mean_ppl: Direct selection based on mean PPL scores
    """
    
    SUPPORTED_STRATEGIES = {"majority", "mean_ppl"}
    
    def __init__(self, strategy: str = "majority") -> None:
        """Initialize voting mechanism.
        
        Args:
            strategy: Voting strategy
                - "majority": Majority voting, ties broken by mean PPL
                - "mean_ppl": Direct selection by lowest mean PPL
                
        Raises:
            ValueError: If strategy is not supported
        """
        if strategy not in self.SUPPORTED_STRATEGIES:
            raise ValueError(
                f"Unknown strategy: {strategy}. "
                f"Available: {self.SUPPORTED_STRATEGIES}"
            )
        self.strategy = strategy
    
    def vote(
        self,
        rep_scores: list[dict[str, float | None]],
        names: list[str],
        default_choice: str | None = None,
    ) -> VoteResult:
        """Execute voting among representatives.
        
        Args:
            rep_scores: PPL scores for each representative
                Each dict maps strategy name to PPL score (or None if missing)
            names: List of strategy names to consider
            default_choice: Default strategy if all scores are missing
            
        Returns:
            VoteResult containing the winning strategy and voting details
        """
        if not names:
            raise ValueError("names cannot be empty")
        
        votes: dict[str, int] = {n: 0 for n in names}
        score_lists: dict[str, list[float]] = {n: [] for n in names}
        vote_details: list[dict[str, Any]] = []
        
        for rep_score in rep_scores:
            best_name: str | None = None
            best_score: float | None = None
            
            for n in names:
                v = rep_score.get(n)
                if v is not None:
                    score_lists[n].append(float(v))
                    # Lower PPL is better
                    if best_score is None or float(v) < best_score:
                        best_score = float(v)
                        best_name = n
            
            if best_name is not None:
                votes[best_name] += 1
            
            vote_details.append({
                "scores": {n: rep_score.get(n) for n in names},
                "chosen": best_name,
            })
        
        # Compute mean scores
        mean_scores: dict[str, float | None] = {}
        for n in names:
            if score_lists[n]:
                mean_scores[n] = float(np.mean(score_lists[n]))
            else:
                mean_scores[n] = None
        
        # Decide winner
        chosen = self._decide(votes, mean_scores, names, default_choice)
        
        return VoteResult(
            chosen=chosen,
            votes=votes,
            mean_scores=mean_scores,
            n_reps_used=len(rep_scores),
            vote_details=vote_details,
        )
    
    def _decide(
        self,
        votes: dict[str, int],
        mean_scores: dict[str, float | None],
        names: list[str],
        default_choice: str | None,
    ) -> str:
        """Decide the winning strategy based on voting strategy.
        
        Args:
            votes: Vote counts for each strategy
            mean_scores: Mean PPL scores for each strategy
            names: List of strategy names
            default_choice: Default if no valid scores
            
        Returns:
            Winning strategy name
        """
        if self.strategy == "majority":
            return self._decide_majority(votes, mean_scores, names, default_choice)
        elif self.strategy == "mean_ppl":
            return self._decide_mean_ppl(mean_scores, names, default_choice)
        else:
            # Should not reach here due to __init__ validation
            raise ValueError(f"Unknown strategy: {self.strategy}")
    
    def _decide_majority(
        self,
        votes: dict[str, int],
        mean_scores: dict[str, float | None],
        names: list[str],
        default_choice: str | None,
    ) -> str:
        """Majority voting with mean PPL tie-breaker."""
        max_votes = max(votes.values()) if votes else 0
        candidates = [n for n, c in votes.items() if c == max_votes]
        
        if len(candidates) == 1:
            return candidates[0]
        
        # Tie-break by mean PPL (lower is better)
        scored = [(n, mean_scores.get(n)) for n in candidates]
        scored_present = [(n, v) for n, v in scored if v is not None]
        
        if scored_present:
            return min(scored_present, key=lambda x: x[1])[0]
        
        # Fall back to default or alphabetically first
        if default_choice is not None and default_choice in names:
            return default_choice
        return sorted(names)[0]
    
    def _decide_mean_ppl(
        self,
        mean_scores: dict[str, float | None],
        names: list[str],
        default_choice: str | None,
    ) -> str:
        """Direct selection by lowest mean PPL."""
        scored = [(n, v) for n, v in mean_scores.items() if v is not None]
        
        if scored:
            return min(scored, key=lambda x: x[1])[0]
        
        # Fall back to default or alphabetically first
        if default_choice is not None and default_choice in names:
            return default_choice
        return sorted(names)[0]
