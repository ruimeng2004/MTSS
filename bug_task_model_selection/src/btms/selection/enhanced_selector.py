"""Enhanced task model selector with budget allocation support.

This module extends the original TaskModelSelector to support both
binary selection (edit/gen) and budget allocation (ratio-based).
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

from ..utils.io import iter_jsonl, write_json
from .base_selector import BaseSelector, SelectionResult
from .budget_allocator import BudgetAllocator
from .voting import VotingMechanism, VoteResult

logger = logging.getLogger(__name__)


class BinarySelector(BaseSelector):
    """Binary selector using voting mechanism (edit or gen)."""
    
    def __init__(
        self,
        voting_strategy: str = "majority",
        default_choice: str | None = None
    ):
        """Initialize binary selector.
        
        Args:
            voting_strategy: Voting strategy ('majority' or 'mean_ppl').
            default_choice: Default choice if all scores missing.
        """
        self.voting = VotingMechanism(strategy=voting_strategy)
        self.default_choice = default_choice
    
    def select(
        self,
        cluster_id: int,
        cluster_size: int,
        representatives: List[Dict[str, Any]],
        ppl_edit: Dict[str, float],
        ppl_gen: Dict[str, float]
    ) -> SelectionResult:
        """Select using voting mechanism.
        
        Args:
            cluster_id: Cluster identifier.
            cluster_size: Total number of bugs in cluster.
            representatives: List of representative dicts.
            ppl_edit: PPL scores for edit mode.
            ppl_gen: PPL scores for gen mode.
            
        Returns:
            SelectionResult with binary decision.
        """
        # Collect scores
        rep_scores: List[Dict[str, float | None]] = []
        for rep in representatives:
            slug = rep.get("slug")
            if slug:
                scores = {
                    "edit": ppl_edit.get(slug),
                    "gen": ppl_gen.get(slug)
                }
                rep_scores.append(scores)
        
        # Vote
        if rep_scores:
            result = self.voting.vote(
                rep_scores, ["edit", "gen"], self.default_choice
            )
        else:
            result = VoteResult(
                chosen=self.default_choice or "edit",
                votes={"edit": 0, "gen": 0},
                mean_scores={"edit": None, "gen": None},
                n_reps_used=0,
                vote_details=[]
            )
        
        # Compute confidence based on vote margin
        if result.n_reps_used > 0:
            total_votes = sum(result.votes.values())
            if total_votes > 0:
                winner_votes = result.votes.get(result.chosen, 0)
                confidence = winner_votes / total_votes
            else:
                confidence = 0.0
        else:
            confidence = 0.0
        
        return SelectionResult(
            cluster_id=cluster_id,
            decision=result.chosen,
            ratio=None,
            confidence=confidence,
            metadata={
                "votes": result.votes,
                "mean_scores": result.mean_scores,
                "n_reps_used": result.n_reps_used
            }
        )


class EnhancedTaskModelSelector:
    """Enhanced task model selector with budget allocation support.
    
    Supports both binary selection (edit/gen) and budget allocation
    (ratio-based) strategies.
    """
    
    def __init__(
        self,
        selector_type: str = "binary",
        selector_config: Optional[Dict[str, Any]] = None
    ):
        """Initialize enhanced selector.
        
        Args:
            selector_type: Type of selector ("binary" or "budget_allocator").
            selector_config: Configuration for the selector.
        """
        self.selector_type = selector_type
        self.selector_config = selector_config or {}
        
        # Initialize selector
        self.selector = self._create_selector()
        
        logger.info(f"Initialized EnhancedTaskModelSelector: {selector_type}")
    
    def _create_selector(self) -> BaseSelector:
        """Create the appropriate selector instance."""
        if self.selector_type == "binary":
            voting_strategy = self.selector_config.get("voting_strategy", "majority")
            default_choice = self.selector_config.get("default_choice")
            return BinarySelector(
                voting_strategy=voting_strategy,
                default_choice=default_choice
            )
        
        elif self.selector_type == "budget_allocator":
            metric = self.selector_config.get("metric", "vote_consistency")
            min_ratio = self.selector_config.get("min_ratio", 0.2)
            max_ratio = self.selector_config.get("max_ratio", 0.8)
            metric_params = self.selector_config.get("metric_params", {})
            
            return BudgetAllocator(
                metric=metric,
                min_ratio=min_ratio,
                max_ratio=max_ratio,
                metric_params=metric_params
            )
        
        else:
            raise ValueError(f"Unknown selector type: {self.selector_type}")
    
    def select(
        self,
        representatives_path: Path,
        ppl_edit_path: Path,
        ppl_gen_path: Path,
        assignments_path: Path,
        out_dir: Path
    ) -> Dict[str, Dict[str, Any]]:
        """Execute selection for all clusters.
        
        Args:
            representatives_path: Path to representatives.jsonl.
            ppl_edit_path: Path to edit PPL scores.
            ppl_gen_path: Path to gen PPL scores.
            assignments_path: Path to cluster assignments.
            out_dir: Output directory.
            
        Returns:
            Cluster choices dictionary.
        """
        # Load data
        logger.info("Loading representatives...")
        clusters = self._load_representatives(representatives_path)
        
        logger.info("Loading PPL scores...")
        ppl_edit = self._load_ppl_scores(ppl_edit_path)
        ppl_gen = self._load_ppl_scores(ppl_gen_path)
        
        logger.info("Loading cluster sizes...")
        cluster_sizes = self._load_cluster_sizes(assignments_path)
        
        # Process each cluster
        logger.info(f"Processing {len(clusters)} clusters...")
        cluster_choices: Dict[str, Dict[str, Any]] = {}
        
        for cid in sorted(clusters.keys()):
            reps = clusters[cid]
            cluster_size = cluster_sizes.get(cid, len(reps))
            
            result = self.selector.select(
                cluster_id=cid,
                cluster_size=cluster_size,
                representatives=reps,
                ppl_edit=ppl_edit,
                ppl_gen=ppl_gen
            )
            
            cluster_choices[str(cid)] = result.to_dict()
        
        # Save outputs
        out_dir.mkdir(parents=True, exist_ok=True)
        
        output_path = out_dir / "cluster_choices.json"
        write_json(output_path, cluster_choices)
        logger.info(f"Saved cluster choices to {output_path}")
        
        # Save summary statistics
        self._save_statistics(cluster_choices, out_dir)
        
        return cluster_choices
    
    def _load_representatives(
        self,
        path: Path
    ) -> Dict[int, List[Dict[str, Any]]]:
        """Load representatives grouped by cluster."""
        clusters: Dict[int, List[Dict[str, Any]]] = {}
        
        for obj in iter_jsonl(path):
            cid = obj.get("cluster_id")
            if cid is not None:
                clusters.setdefault(int(cid), []).append(obj)
        
        # Sort by rank within each cluster
        for cid in clusters:
            clusters[cid].sort(key=lambda x: x.get("rank", 0))
        
        return clusters
    
    def _load_ppl_scores(self, path: Path) -> Dict[str, float]:
        """Load PPL scores from JSONL file."""
        scores: Dict[str, float] = {}
        for obj in iter_jsonl(path):
            slug = obj.get("slug")
            value = obj.get("value")
            if isinstance(slug, str) and value is not None:
                try:
                    scores[slug] = float(value)
                except (TypeError, ValueError):
                    continue
        return scores
    
    def _load_cluster_sizes(self, path: Path) -> Dict[int, int]:
        """Load cluster sizes from assignments file."""
        cluster_sizes: Dict[int, int] = {}
        
        for obj in iter_jsonl(path):
            cid = obj.get("cluster_id")
            if cid is not None:
                cid = int(cid)
                cluster_sizes[cid] = cluster_sizes.get(cid, 0) + 1
        
        return cluster_sizes
    
    def _save_statistics(
        self,
        cluster_choices: Dict[str, Dict[str, Any]],
        out_dir: Path
    ):
        """Save summary statistics."""
        stats = {
            "total_clusters": len(cluster_choices),
            "selector_type": self.selector_type,
            "decision_counts": {},
            "average_confidence": 0.0
        }
        
        confidences = []
        
        for choice in cluster_choices.values():
            decision = choice.get("decision", "unknown")
            stats["decision_counts"][decision] = \
                stats["decision_counts"].get(decision, 0) + 1
            
            conf = choice.get("confidence")
            if conf is not None:
                confidences.append(conf)
        
        if confidences:
            stats["average_confidence"] = sum(confidences) / len(confidences)
        
        # Add ratio statistics for budget allocator
        if self.selector_type == "budget_allocator":
            edit_ratios = []
            for choice in cluster_choices.values():
                ratio = choice.get("ratio", {})
                if "edit" in ratio:
                    edit_ratios.append(ratio["edit"])
            
            if edit_ratios:
                stats["edit_ratio"] = {
                    "mean": sum(edit_ratios) / len(edit_ratios),
                    "min": min(edit_ratios),
                    "max": max(edit_ratios)
                }
        
        stats_path = out_dir / "selection_statistics.json"
        write_json(stats_path, stats)
        logger.info(f"Saved statistics to {stats_path}")
