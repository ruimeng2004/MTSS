"""Cached experiment runner with intermediate result reuse."""

from __future__ import annotations

import hashlib
import json
import logging
import pickle
from itertools import product
from pathlib import Path
from typing import Any

import numpy as np

from ..clustering.base import ClusteringConfig, ClusteringResult
from ..clustering.factory import ClustererFactory
from ..sampling.base import SamplingConfig, SamplingResult
from ..sampling.factory import SamplerFactory
from ..selection.selector import TaskModelSelector
from ..utils.io import iter_jsonl, write_jsonl
from .config import ExperimentConfig

logger = logging.getLogger(__name__)


class CachedExperimentRunner:
    """Experiment runner with intermediate result caching.
    
    Caches clustering and sampling results to avoid redundant computation.
    Supports multiple voting strategies and seeds efficiently.
    """
    
    # Deterministic algorithms (seed doesn't matter)
    DETERMINISTIC_CLUSTERING = {"hac_average", "hac_ward", "hac_complete", "hac_single"}
    DETERMINISTIC_SAMPLING = {"farthest_first"}
    
    def __init__(self, config: ExperimentConfig):
        """Initialize runner.
        
        Args:
            config: Experiment configuration
        """
        self.config = config
        self.results: list[dict[str, Any]] = []
        
        # Cache directories
        self.cache_dir = config.output_dir / "_cache"
        self.cluster_cache_dir = self.cache_dir / "clusters"
        self.sample_cache_dir = self.cache_dir / "samples"
        
        # In-memory caches
        self._vectors_cache: dict[str, tuple[np.ndarray, list[str], dict]] = {}
        self._ppl_cache: dict[str, dict[str, float]] | None = None
    
    def run(self) -> list[dict[str, Any]]:
        """Run all experiment combinations with caching.
        
        Returns:
            List of experiment results
        """
        # Create cache directories
        self.cluster_cache_dir.mkdir(parents=True, exist_ok=True)
        self.sample_cache_dir.mkdir(parents=True, exist_ok=True)
        
        # Generate all combinations
        combinations = self._generate_combinations()
        total = len(combinations)
        logger.info(f"Total experiment combinations: {total}")
        
        # Phase 1: Clustering (deduplicated)
        cluster_keys = self._get_unique_cluster_keys(combinations)
        logger.info(f"Phase 1: Running {len(cluster_keys)} unique clustering tasks")
        self._run_clustering_phase(cluster_keys)
        
        # Phase 2: Sampling (deduplicated)
        sample_keys = self._get_unique_sample_keys(combinations)
        logger.info(f"Phase 2: Running {len(sample_keys)} unique sampling tasks")
        self._run_sampling_phase(sample_keys)
        
        # Phase 3: Voting and metrics (all combinations)
        logger.info(f"Phase 3: Computing metrics for {total} combinations")
        self._run_voting_phase(combinations)
        
        return self.results
    
    def _generate_combinations(self) -> list[dict[str, Any]]:
        """Generate all parameter combinations."""
        seeds = getattr(self.config, 'seeds', [self.config.seed])
        voting_strategies = getattr(self.config, 'voting_strategies', ['majority'])
        
        combinations = []
        for view, algo, k, method, reps, seed, voting in product(
            self.config.views,
            self.config.clustering_algorithms,
            self.config.k_values,
            self.config.sampling_methods,
            self.config.reps_per_cluster_values,
            seeds,
            voting_strategies,
        ):
            combinations.append({
                "view": view,
                "clustering_algorithm": algo,
                "k": k,
                "sampling_method": method,
                "reps_per_cluster": reps,
                "seed": seed,
                "voting_strategy": voting,
            })
        return combinations
    
    def _get_cluster_key(self, params: dict[str, Any]) -> str:
        """Generate unique key for clustering result."""
        algo = params["clustering_algorithm"]
        # Deterministic algorithms don't depend on seed
        seed = 0 if algo in self.DETERMINISTIC_CLUSTERING else params["seed"]
        return f"{params['view']}_{algo}_k{params['k']}_s{seed}"
    
    def _get_sample_key(self, params: dict[str, Any]) -> str:
        """Generate unique key for sampling result."""
        cluster_key = self._get_cluster_key(params)
        method = params["sampling_method"]
        # Deterministic sampling doesn't depend on seed
        seed = 0 if method in self.DETERMINISTIC_SAMPLING else params["seed"]
        return f"{cluster_key}_{method}_r{params['reps_per_cluster']}_s{seed}"
    
    def _get_unique_cluster_keys(self, combinations: list[dict]) -> list[dict]:
        """Get unique clustering configurations."""
        seen = set()
        unique = []
        for params in combinations:
            key = self._get_cluster_key(params)
            if key not in seen:
                seen.add(key)
                unique.append({
                    "view": params["view"],
                    "clustering_algorithm": params["clustering_algorithm"],
                    "k": params["k"],
                    "seed": params["seed"],
                    "key": key,
                })
        return unique
    
    def _get_unique_sample_keys(self, combinations: list[dict]) -> list[dict]:
        """Get unique sampling configurations."""
        seen = set()
        unique = []
        for params in combinations:
            key = self._get_sample_key(params)
            if key not in seen:
                seen.add(key)
                unique.append({
                    **params,
                    "cluster_key": self._get_cluster_key(params),
                    "sample_key": key,
                })
        return unique
    
    def _run_clustering_phase(self, cluster_keys: list[dict]) -> None:
        """Run all unique clustering tasks."""
        for i, params in enumerate(cluster_keys, 1):
            key = params["key"]
            cache_file = self.cluster_cache_dir / f"{key}.pkl"
            
            if cache_file.exists():
                logger.debug(f"Cluster cache hit: {key}")
                continue
            
            logger.info(f"Clustering {i}/{len(cluster_keys)}: {key}")
            
            # Load vectors
            vectors, ids, meta = self._load_vectors(params["view"])
            n_samples = len(vectors)
            k = min(params["k"], n_samples)
            
            # Run clustering
            algo = params["clustering_algorithm"]
            seed = 0 if algo in self.DETERMINISTIC_CLUSTERING else params["seed"]
            
            cluster_config = ClusteringConfig(n_clusters=k, seed=seed)
            clusterer = ClustererFactory.create(algo, cluster_config)
            result = clusterer.fit(vectors)
            
            # Save to cache
            cache_data = {
                "labels": result.labels,
                "n_clusters": result.n_clusters,
                "ids": ids,
                "meta": meta,
            }
            with cache_file.open("wb") as f:
                pickle.dump(cache_data, f)
    
    def _run_sampling_phase(self, sample_keys: list[dict]) -> None:
        """Run all unique sampling tasks."""
        for i, params in enumerate(sample_keys, 1):
            sample_key = params["sample_key"]
            cache_file = self.sample_cache_dir / f"{sample_key}.pkl"
            
            if cache_file.exists():
                logger.debug(f"Sample cache hit: {sample_key}")
                continue
            
            logger.info(f"Sampling {i}/{len(sample_keys)}: {sample_key}")
            
            # Load clustering result
            cluster_key = params["cluster_key"]
            cluster_cache = self.cluster_cache_dir / f"{cluster_key}.pkl"
            with cluster_cache.open("rb") as f:
                cluster_data = pickle.load(f)
            
            # Load vectors
            vectors, _, _ = self._load_vectors(params["view"])
            
            # Build cluster indices
            cluster_indices = self._build_cluster_indices(cluster_data["labels"])
            
            # Run sampling
            method = params["sampling_method"]
            seed = 0 if method in self.DETERMINISTIC_SAMPLING else params["seed"]
            
            sample_config = SamplingConfig(
                reps_per_cluster=params["reps_per_cluster"],
                seed=seed,
            )
            sampler = SamplerFactory.create(method, sample_config)
            result = sampler.sample(vectors, cluster_indices)
            
            # Save to cache
            cache_data = {
                "representatives": result.representatives,
                "cluster_ids": cluster_data["ids"],
                "cluster_meta": cluster_data["meta"],
                "labels": cluster_data["labels"],
            }
            with cache_file.open("wb") as f:
                pickle.dump(cache_data, f)
    
    def _run_voting_phase(self, combinations: list[dict]) -> None:
        """Run voting and compute metrics for all combinations."""
        ppl_by_name = self._load_ppl_scores()
        
        for i, params in enumerate(combinations, 1):
            if i % 100 == 0:
                logger.info(f"Voting {i}/{len(combinations)}")
            
            try:
                result = self._compute_single_result(params, ppl_by_name)
                self.results.append(result)
            except Exception as e:
                logger.error(f"Failed: {params}, error: {e}")
                self.results.append({
                    "params": params,
                    "status": "failed",
                    "error": str(e),
                })
    
    def _compute_single_result(
        self, 
        params: dict[str, Any],
        ppl_by_name: dict[str, dict[str, float]]
    ) -> dict[str, Any]:
        """Compute result for a single parameter combination."""
        # Load sampling result from cache
        sample_key = self._get_sample_key(params)
        cache_file = self.sample_cache_dir / f"{sample_key}.pkl"
        with cache_file.open("rb") as f:
            sample_data = pickle.load(f)
        
        # Build representatives data
        representatives = []
        ids = sample_data["cluster_ids"]
        meta = sample_data["cluster_meta"]
        labels = sample_data["labels"]
        
        for cluster_id, rep_indices in sample_data["representatives"].items():
            for rank, idx in enumerate(rep_indices):
                item_id = ids[idx]
                slug = item_id.rsplit("__", 1)[0] if "__" in item_id else item_id
                representatives.append({
                    "cluster_id": cluster_id,
                    "rank": rank,
                    "item_id": item_id,
                    "slug": slug,
                })
        
        # Run voting
        voting_strategy = params.get("voting_strategy", "majority")
        selector = TaskModelSelector(voting_strategy=voting_strategy)
        cluster_choices = selector._compute_cluster_choices(representatives, ppl_by_name)
        
        # Build assignments mapping
        assignments = {}
        for idx, label in enumerate(labels):
            item_id = ids[idx]
            slug = item_id.rsplit("__", 1)[0] if "__" in item_id else item_id
            assignments[slug] = str(label)
        
        # Compute metrics
        metrics = self._compute_metrics(
            cluster_choices, assignments, ppl_by_name, labels
        )
        
        return {
            "params": params,
            "status": "completed",
            "metrics": metrics,
        }
    
    def _compute_metrics(
        self,
        cluster_choices: dict[str, dict],
        assignments: dict[str, str],
        ppl_by_name: dict[str, dict[str, float]],
        labels: np.ndarray,
    ) -> dict[str, Any]:
        """Compute comprehensive evaluation metrics."""
        strategy_names = list(ppl_by_name.keys())
        
        # Get all slugs
        all_slugs = set()
        for scores in ppl_by_name.values():
            all_slugs.update(scores.keys())
        
        # Metrics accumulators
        wins = 0
        total = 0
        ppl_regrets = []
        relative_regrets = []
        routed_ppls = []
        oracle_ppls = []
        
        # Per-cluster metrics
        cluster_correct = 0
        cluster_total = 0
        cluster_agreements = []
        
        # Compute per-cluster ground truth
        cluster_gt = {}  # cluster_id -> {"edit": count, "gen": count}
        for slug in all_slugs:
            cluster_id = assignments.get(slug)
            if cluster_id is None:
                continue
            
            scores = {name: ppl_by_name[name].get(slug) for name in strategy_names}
            scores = {k: v for k, v in scores.items() if v is not None}
            if len(scores) < 2:
                continue
            
            best = min(scores, key=lambda x: scores[x])
            if cluster_id not in cluster_gt:
                cluster_gt[cluster_id] = {name: 0 for name in strategy_names}
            cluster_gt[cluster_id][best] += 1
        
        # Compute cluster-level metrics
        for cluster_id, counts in cluster_gt.items():
            if cluster_id not in cluster_choices:
                continue
            
            chosen = cluster_choices[cluster_id]["chosen"]
            majority = max(counts, key=lambda x: counts[x])
            total_in_cluster = sum(counts.values())
            
            if chosen == majority:
                cluster_correct += 1
            cluster_total += 1
            
            # Agreement = max votes / total
            agreement = max(counts.values()) / total_in_cluster if total_in_cluster > 0 else 0
            cluster_agreements.append(agreement)
        
        # Compute per-slug metrics
        for slug in all_slugs:
            cluster_id = assignments.get(slug)
            if cluster_id is None or cluster_id not in cluster_choices:
                continue
            
            chosen = cluster_choices[cluster_id]["chosen"]
            
            scores = {name: ppl_by_name[name].get(slug) for name in strategy_names}
            scores = {k: v for k, v in scores.items() if v is not None}
            if len(scores) < 2:
                continue
            
            best = min(scores, key=lambda x: scores[x])
            chosen_ppl = scores.get(chosen)
            best_ppl = scores[best]
            
            if chosen_ppl is None:
                continue
            
            # Win rate
            if chosen == best:
                wins += 1
            total += 1
            
            # PPL metrics
            routed_ppls.append(chosen_ppl)
            oracle_ppls.append(best_ppl)
            
            regret = chosen_ppl - best_ppl
            ppl_regrets.append(regret)
            
            if best_ppl > 0:
                relative_regrets.append(regret / best_ppl)
        
        # Aggregate metrics
        win_rate = wins / total if total > 0 else 0.0
        cluster_accuracy = cluster_correct / cluster_total if cluster_total > 0 else 0.0
        mean_agreement = np.mean(cluster_agreements) if cluster_agreements else 0.0
        
        mean_ppl_regret = np.mean(ppl_regrets) if ppl_regrets else 0.0
        mean_relative_regret = np.mean(relative_regrets) if relative_regrets else 0.0
        
        oracle_gap = (np.mean(routed_ppls) - np.mean(oracle_ppls)) if oracle_ppls else 0.0
        
        return {
            "win_rate": win_rate,
            "wins": wins,
            "total": total,
            "n_clusters": len(cluster_choices),
            "ppl_regret": mean_ppl_regret,
            "relative_regret": mean_relative_regret,
            "oracle_gap": oracle_gap,
            "cluster_accuracy": cluster_accuracy,
            "cluster_agreement": mean_agreement,
        }
    
    def _load_vectors(self, view: str) -> tuple[np.ndarray, list[str], dict]:
        """Load vectors with caching."""
        if view in self._vectors_cache:
            return self._vectors_cache[view]
        
        vectors_list = []
        ids = []
        meta = {}
        
        for obj in iter_jsonl(self.config.embeddings_path):
            if obj.get("view") == view:
                item_id = obj["item_id"]
                ids.append(item_id)
                vectors_list.append(obj["embedding"])
                meta[item_id] = {
                    "slug": obj.get("slug"),
                    "view": obj.get("view"),
                }
        
        if not vectors_list:
            raise ValueError(f"No embeddings found for view: {view}")
        
        result = (np.array(vectors_list), ids, meta)
        self._vectors_cache[view] = result
        return result
    
    def _load_ppl_scores(self) -> dict[str, dict[str, float]]:
        """Load PPL scores with caching."""
        if self._ppl_cache is not None:
            return self._ppl_cache
        
        ppl_by_name = {}
        for name, path in self.config.ppl_paths.items():
            scores = {}
            for obj in iter_jsonl(path):
                slug = obj.get("slug")
                value = obj.get("value")
                if slug is not None and value is not None:
                    scores[slug] = float(value)
            ppl_by_name[name] = scores
        
        self._ppl_cache = ppl_by_name
        return ppl_by_name
    
    def _build_cluster_indices(self, labels: np.ndarray) -> dict[int, np.ndarray]:
        """Build cluster index mapping."""
        cluster_indices = {}
        for idx, label in enumerate(labels):
            label = int(label)
            if label not in cluster_indices:
                cluster_indices[label] = []
            cluster_indices[label].append(idx)
        return {k: np.array(v) for k, v in cluster_indices.items()}
