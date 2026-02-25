"""Task model selector with multi-representative voting support."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from ..utils.io import iter_jsonl, write_json
from .voting import VotingMechanism, VoteResult


class TaskModelSelector:
    """Task model selector with multi-representative voting support.
    
    Reads representatives from each cluster and uses voting to decide
    which task modeling strategy (edit/gen) to use for each cluster.
    """
    
    def __init__(
        self,
        voting_strategy: str = "majority",
        default_choice: str | None = None,
    ) -> None:
        """Initialize task model selector.
        
        Args:
            voting_strategy: Voting strategy ('majority' or 'mean_ppl')
            default_choice: Default strategy if all scores are missing
        """
        self.voting = VotingMechanism(strategy=voting_strategy)
        self.default_choice = default_choice
    
    def select(
        self,
        representatives_path: Path,
        ppl_by_name: dict[str, dict[str, float]],
        out_dir: Path,
    ) -> dict[str, dict[str, Any]]:
        """Execute selection for all clusters.
        
        Args:
            representatives_path: Path to representatives.jsonl
            ppl_by_name: PPL scores by strategy name
                {strategy_name: {slug: ppl_score}}
            out_dir: Output directory
            
        Returns:
            Cluster choices dictionary
        """
        clusters = self._load_representatives(representatives_path)
        cluster_choices, item_choices = self._compute_cluster_choices_from_clusters(
            clusters, ppl_by_name
        )
        
        # Save outputs
        out_dir.mkdir(parents=True, exist_ok=True)
        
        # Cluster choices
        write_json(out_dir / "cluster_choices.json", cluster_choices)
        
        # Item choices (for debugging/analysis)
        with (out_dir / "rep_item_choices.jsonl").open("w", encoding="utf-8") as f:
            for item in item_choices:
                f.write(json.dumps(item, ensure_ascii=False) + "\n")
        
        return cluster_choices
    
    def _compute_cluster_choices(
        self,
        representatives: list[dict[str, Any]],
        ppl_by_name: dict[str, dict[str, float]],
    ) -> dict[str, dict[str, Any]]:
        """Compute cluster choices from representative list.
        
        Args:
            representatives: List of representative dicts with cluster_id, slug, rank
            ppl_by_name: PPL scores by strategy name
            
        Returns:
            Cluster choices dictionary
        """
        # Group by cluster
        clusters: dict[int, list[dict[str, Any]]] = {}
        for rep in representatives:
            cid = rep.get("cluster_id")
            if cid is not None:
                clusters.setdefault(int(cid), []).append(rep)
        
        # Sort by rank
        for cid in clusters:
            clusters[cid].sort(key=lambda x: x.get("rank", 0))
        
        cluster_choices, _ = self._compute_cluster_choices_from_clusters(
            clusters, ppl_by_name
        )
        return cluster_choices
    
    def _compute_cluster_choices_from_clusters(
        self,
        clusters: dict[int, list[dict[str, Any]]],
        ppl_by_name: dict[str, dict[str, float]],
    ) -> tuple[dict[str, dict[str, Any]], list[dict[str, Any]]]:
        """Compute cluster choices from grouped clusters.
        
        Args:
            clusters: Mapping from cluster_id to list of representative dicts
            ppl_by_name: PPL scores by strategy name
            
        Returns:
            Tuple of (cluster_choices, item_choices)
        """
        names = list(ppl_by_name.keys())
        
        if not names:
            raise ValueError("ppl_by_name cannot be empty")
        
        cluster_choices: dict[str, dict[str, Any]] = {}
        item_choices: list[dict[str, Any]] = []
        
        for cid in sorted(clusters.keys()):
            reps = clusters[cid]
            
            # Collect PPL scores for all representatives
            rep_scores: list[dict[str, float | None]] = []
            for rep in reps:
                slug = rep.get("slug")
                if not slug:
                    continue
                scores = {n: ppl_by_name[n].get(slug) for n in names}
                rep_scores.append(scores)
                
                # Record individual item choice
                item_choices.append({
                    "cluster_id": cid,
                    "item_id": rep.get("item_id"),
                    "slug": slug,
                    "rank": rep.get("rank"),
                    "scores": scores,
                })
            
            # Vote
            if rep_scores:
                result = self.voting.vote(
                    rep_scores, names, self.default_choice
                )
            else:
                # No valid representatives
                result = VoteResult(
                    chosen=self.default_choice or sorted(names)[0],
                    votes={n: 0 for n in names},
                    mean_scores={n: None for n in names},
                    n_reps_used=0,
                    vote_details=[],
                )
            
            cluster_choices[str(cid)] = {
                "cluster_id": cid,
                "chosen": result.chosen,
                "votes": result.votes,
                "mean_scores": {
                    k: v for k, v in result.mean_scores.items()
                },
                "n_reps_used": result.n_reps_used,
                "vote_details": result.vote_details,
            }
        
        return cluster_choices, item_choices
    
    def _load_representatives(
        self,
        path: Path,
    ) -> dict[int, list[dict[str, Any]]]:
        """Load all representatives from JSONL file.
        
        Args:
            path: Path to representatives.jsonl
            
        Returns:
            Mapping from cluster_id to list of representative dicts
        """
        clusters: dict[int, list[dict[str, Any]]] = {}
        
        for obj in iter_jsonl(path):
            cid = obj.get("cluster_id")
            if cid is not None:
                clusters.setdefault(int(cid), []).append(obj)
        
        # Sort representatives by rank within each cluster
        for cid in clusters:
            clusters[cid].sort(key=lambda x: x.get("rank", 0))
        
        return clusters


def load_ppl_scores(path: Path) -> dict[str, float]:
    """Load PPL scores from JSONL file.
    
    Args:
        path: Path to PPL scores file
        
    Returns:
        Mapping from slug to PPL score
    """
    scores: dict[str, float] = {}
    for obj in iter_jsonl(path):
        slug = obj.get("slug")
        value = obj.get("value")
        if isinstance(slug, str) and value is not None:
            try:
                scores[slug] = float(value)
            except (TypeError, ValueError):
                continue
    return scores
