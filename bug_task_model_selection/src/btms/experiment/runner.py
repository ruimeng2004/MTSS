"""Experiment runner for batch experiments."""

from __future__ import annotations

import json
import logging
from concurrent.futures import ProcessPoolExecutor, as_completed
from itertools import product
from pathlib import Path
from typing import Any

import numpy as np

from ..clustering.base import ClusteringConfig
from ..clustering.factory import ClustererFactory
from ..sampling.base import SamplingConfig
from ..sampling.factory import SamplerFactory
from ..selection.selector import TaskModelSelector
from ..utils.io import iter_jsonl
from .config import ExperimentConfig

logger = logging.getLogger(__name__)


class ExperimentRunner:
    """Runner for batch experiments with parameter grid search.
    
    Supports sequential and parallel execution, incremental runs,
    and comprehensive result tracking.
    """
    
    def __init__(self, config: ExperimentConfig):
        """Initialize runner.
        
        Args:
            config: Experiment configuration
        """
        self.config = config
        self.results: list[dict[str, Any]] = []
    
    def run(self) -> list[dict[str, Any]]:
        """Run all experiment combinations.
        
        Returns:
            List of experiment results
        """
        combinations = self._generate_combinations()
        total = len(combinations)
        logger.info(f"Running {total} experiment combinations")
        
        if self.config.parallel and self.config.n_workers > 1:
            self._run_parallel(combinations)
        else:
            self._run_sequential(combinations)
        
        return self.results
    
    def _generate_combinations(self) -> list[dict[str, Any]]:
        """Generate all parameter combinations.
        
        Returns:
            List of parameter dictionaries
        """
        combinations = []
        for view, algo, k, method, reps in product(
            self.config.views,
            self.config.clustering_algorithms,
            self.config.k_values,
            self.config.sampling_methods,
            self.config.reps_per_cluster_values,
        ):
            combinations.append({
                "view": view,
                "clustering_algorithm": algo,
                "k": k,
                "sampling_method": method,
                "reps_per_cluster": reps,
            })
        return combinations
    
    def _run_sequential(self, combinations: list[dict[str, Any]]) -> None:
        """Run experiments sequentially."""
        for i, params in enumerate(combinations, 1):
            logger.info(f"Running experiment {i}/{len(combinations)}: {params}")
            try:
                result = self._run_single(params)
                self.results.append(result)
            except Exception as e:
                logger.error(f"Experiment failed: {params}, error: {e}")
                self.results.append({
                    "params": params,
                    "status": "failed",
                    "error": str(e),
                })
    
    def _run_parallel(self, combinations: list[dict[str, Any]]) -> None:
        """Run experiments in parallel."""
        with ProcessPoolExecutor(max_workers=self.config.n_workers) as executor:
            future_to_params = {
                executor.submit(self._run_single, params): params
                for params in combinations
            }
            
            for future in as_completed(future_to_params):
                params = future_to_params[future]
                try:
                    result = future.result()
                    self.results.append(result)
                except Exception as e:
                    logger.error(f"Experiment failed: {params}, error: {e}")
                    self.results.append({
                        "params": params,
                        "status": "failed",
                        "error": str(e),
                    })

    
    def _run_single(self, params: dict[str, Any]) -> dict[str, Any]:
        """Run a single experiment.
        
        Args:
            params: Experiment parameters
            
        Returns:
            Result dictionary with params, status, and metrics
        """
        out_dir = self._get_output_dir(params)
        
        # Check if already completed
        metrics_file = out_dir / "overall_metrics.json"
        if self.config.skip_existing and metrics_file.exists():
            logger.info(f"Skipping existing: {out_dir.name}")
            return self._load_existing_result(out_dir, params)
        
        # Create output directory
        out_dir.mkdir(parents=True, exist_ok=True)
        
        # Save params
        with (out_dir / "params.json").open("w", encoding="utf-8") as f:
            json.dump(params, f, indent=2)
        
        # 1. Load vectors for the specified view
        vectors, ids, meta = self._load_vectors(params["view"])
        n_samples = len(vectors)
        
        # Adjust k if needed
        k = min(params["k"], n_samples)
        if k != params["k"]:
            logger.warning(f"Adjusted k from {params['k']} to {k} (n_samples={n_samples})")
        
        # 2. Clustering
        cluster_config = ClusteringConfig(
            n_clusters=k,
            seed=self.config.seed,
        )
        clusterer = ClustererFactory.create(params["clustering_algorithm"], cluster_config)
        cluster_result = clusterer.fit(vectors)
        
        # Export assignments
        clusterer.export_assignments(cluster_result, ids, out_dir / "assignments.jsonl")
        
        # 3. Sampling
        sample_config = SamplingConfig(
            reps_per_cluster=params["reps_per_cluster"],
            seed=self.config.seed,
        )
        sampler = SamplerFactory.create(params["sampling_method"], sample_config)
        
        # Build cluster indices
        cluster_indices = self._build_cluster_indices(cluster_result.labels)
        sample_result = sampler.sample(vectors, cluster_indices)
        
        # Export representatives
        sampler.export_representatives(sample_result, ids, meta, out_dir / "representatives.jsonl")
        
        # 4. Selection with voting
        ppl_by_name = self._load_ppl_scores()
        selector = TaskModelSelector(voting_strategy="majority")
        selector.select(
            representatives_path=out_dir / "representatives.jsonl",
            ppl_by_name=ppl_by_name,
            out_dir=out_dir,
        )
        
        # 5. Compute metrics
        metrics = self._compute_metrics(out_dir, ppl_by_name)
        
        # Save metrics
        with metrics_file.open("w", encoding="utf-8") as f:
            json.dump(metrics, f, indent=2)
        
        return {
            "params": params,
            "status": "completed",
            "metrics": metrics,
            "output_dir": str(out_dir),
        }
    
    def _get_output_dir(self, params: dict[str, Any]) -> Path:
        """Generate consistent output directory name.
        
        Args:
            params: Experiment parameters
            
        Returns:
            Output directory path
        """
        name = (
            f"{params['view']}_"
            f"{params['clustering_algorithm']}_"
            f"k{params['k']}_"
            f"{params['sampling_method']}_"
            f"r{params['reps_per_cluster']}"
        )
        return self.config.output_dir / name
    
    def _load_vectors(self, view: str) -> tuple[np.ndarray, list[str], dict[str, dict]]:
        """Load vectors for a specific view.
        
        Args:
            view: View name to filter by
            
        Returns:
            Tuple of (vectors array, item IDs, metadata dict)
        """
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
        
        return np.array(vectors_list), ids, meta
    
    def _build_cluster_indices(self, labels: np.ndarray) -> dict[int, np.ndarray]:
        """Build cluster index mapping.
        
        Args:
            labels: Cluster labels array
            
        Returns:
            Dict mapping cluster_id to array of indices
        """
        cluster_indices = {}
        for idx, label in enumerate(labels):
            label = int(label)
            if label not in cluster_indices:
                cluster_indices[label] = []
            cluster_indices[label].append(idx)
        
        return {k: np.array(v) for k, v in cluster_indices.items()}
    
    def _load_ppl_scores(self) -> dict[str, dict[str, float]]:
        """Load PPL scores for all strategies.
        
        Returns:
            Dict mapping strategy name to {slug: score} dict
        """
        ppl_by_name = {}
        for name, path in self.config.ppl_paths.items():
            scores = {}
            for obj in iter_jsonl(path):
                slug = obj.get("slug")
                value = obj.get("value")
                if slug is not None and value is not None:
                    scores[slug] = float(value)
            ppl_by_name[name] = scores
        return ppl_by_name
    
    def _compute_metrics(
        self, 
        out_dir: Path, 
        ppl_by_name: dict[str, dict[str, float]]
    ) -> dict[str, Any]:
        """Compute evaluation metrics.
        
        Args:
            out_dir: Output directory with results
            ppl_by_name: PPL scores by strategy
            
        Returns:
            Metrics dictionary
        """
        # Load cluster choices
        choices_file = out_dir / "cluster_choices.json"
        if not choices_file.exists():
            return {"error": "cluster_choices.json not found"}
        
        with choices_file.open("r", encoding="utf-8") as f:
            cluster_choices = json.load(f)
        
        # Load assignments to map items to clusters
        assignments = {}
        for obj in iter_jsonl(out_dir / "assignments.jsonl"):
            item_id = obj["item_id"]
            cluster_id = str(obj["cluster_id"])
            # Extract slug from item_id (format: slug__view)
            slug = item_id.rsplit("__", 1)[0] if "__" in item_id else item_id
            assignments[slug] = cluster_id
        
        # Compute win rate
        strategy_names = list(ppl_by_name.keys())
        if len(strategy_names) < 2:
            return {"error": "Need at least 2 strategies"}
        
        wins = 0
        total = 0
        
        # For each item, check if the chosen strategy is better
        all_slugs = set()
        for scores in ppl_by_name.values():
            all_slugs.update(scores.keys())
        
        for slug in all_slugs:
            cluster_id = assignments.get(slug)
            if cluster_id is None or cluster_id not in cluster_choices:
                continue
            
            chosen = cluster_choices[cluster_id]["chosen"]
            
            # Get scores for this item
            scores = {name: ppl_by_name[name].get(slug) for name in strategy_names}
            scores = {k: v for k, v in scores.items() if v is not None}
            
            if len(scores) < 2:
                continue
            
            # Check if chosen is the best
            best = min(scores, key=lambda x: scores[x])
            if chosen == best:
                wins += 1
            total += 1
        
        win_rate = wins / total if total > 0 else 0.0
        
        return {
            "win_rate": win_rate,
            "wins": wins,
            "total": total,
            "n_clusters": len(cluster_choices),
        }
    
    def _load_existing_result(
        self, 
        out_dir: Path, 
        params: dict[str, Any]
    ) -> dict[str, Any]:
        """Load existing experiment result.
        
        Args:
            out_dir: Output directory
            params: Experiment parameters
            
        Returns:
            Result dictionary
        """
        metrics_file = out_dir / "overall_metrics.json"
        with metrics_file.open("r", encoding="utf-8") as f:
            metrics = json.load(f)
        
        return {
            "params": params,
            "status": "skipped",
            "metrics": metrics,
            "output_dir": str(out_dir),
        }
