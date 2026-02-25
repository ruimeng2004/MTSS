"""Experiment configuration management."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml


@dataclass
class ExperimentConfig:
    """Configuration for batch experiments.
    
    Attributes:
        name: Experiment name
        embeddings_path: Path to embeddings.jsonl
        ppl_paths: Mapping from strategy name to PPL scores file path
        views: List of views to experiment with
        clustering_algorithms: List of clustering algorithm names
        k_values: List of cluster counts to try
        sampling_methods: List of sampling method names
        reps_per_cluster_values: List of representative counts to try
        output_dir: Output directory for results
        seed: Random seed for reproducibility (used if seeds not specified)
        seeds: List of random seeds for multiple runs
        voting_strategies: List of voting strategies to try
        parallel: Whether to run experiments in parallel
        n_workers: Number of parallel workers
        skip_existing: Whether to skip already completed experiments
    """
    name: str
    embeddings_path: Path
    ppl_paths: dict[str, Path]
    views: list[str]
    clustering_algorithms: list[str]
    k_values: list[int]
    sampling_methods: list[str]
    reps_per_cluster_values: list[int]
    output_dir: Path
    seed: int = 42
    seeds: list[int] | None = None
    voting_strategies: list[str] | None = None
    parallel: bool = False
    n_workers: int = 4
    skip_existing: bool = True
    
    def __post_init__(self) -> None:
        """Validate and convert paths."""
        self.embeddings_path = Path(self.embeddings_path)
        self.output_dir = Path(self.output_dir)
        self.ppl_paths = {k: Path(v) for k, v in self.ppl_paths.items()}
        
        # Set defaults for new fields
        if self.seeds is None:
            self.seeds = [self.seed]
        if self.voting_strategies is None:
            self.voting_strategies = ["majority"]
        
        # Validate
        if not self.views:
            raise ValueError("views cannot be empty")
        if not self.clustering_algorithms:
            raise ValueError("clustering_algorithms cannot be empty")
        if not self.k_values:
            raise ValueError("k_values cannot be empty")
        if not self.sampling_methods:
            raise ValueError("sampling_methods cannot be empty")
        if not self.reps_per_cluster_values:
            raise ValueError("reps_per_cluster_values cannot be empty")
        if not self.ppl_paths:
            raise ValueError("ppl_paths cannot be empty")
    
    def total_combinations(self) -> int:
        """Return total number of experiment combinations."""
        return (
            len(self.views)
            * len(self.clustering_algorithms)
            * len(self.k_values)
            * len(self.sampling_methods)
            * len(self.reps_per_cluster_values)
            * len(self.seeds)
            * len(self.voting_strategies)
        )
    
    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "name": self.name,
            "embeddings_path": str(self.embeddings_path),
            "ppl_paths": {k: str(v) for k, v in self.ppl_paths.items()},
            "views": self.views,
            "clustering_algorithms": self.clustering_algorithms,
            "k_values": self.k_values,
            "sampling_methods": self.sampling_methods,
            "reps_per_cluster_values": self.reps_per_cluster_values,
            "output_dir": str(self.output_dir),
            "seed": self.seed,
            "seeds": self.seeds,
            "voting_strategies": self.voting_strategies,
            "parallel": self.parallel,
            "n_workers": self.n_workers,
            "skip_existing": self.skip_existing,
        }


def load_experiment_config(path: Path) -> ExperimentConfig:
    """Load experiment configuration from YAML file.
    
    Args:
        path: Path to YAML configuration file
        
    Returns:
        ExperimentConfig instance
        
    Raises:
        ValueError: If required fields are missing
    """
    with path.open("r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    
    if not isinstance(data, dict):
        raise ValueError(f"Invalid config file: expected dict, got {type(data)}")
    
    required_fields = [
        "name",
        "embeddings_path",
        "ppl_paths",
        "views",
        "clustering_algorithms",
        "k_values",
        "sampling_methods",
        "reps_per_cluster_values",
        "output_dir",
    ]
    
    missing = [f for f in required_fields if f not in data]
    if missing:
        raise ValueError(f"Missing required fields: {missing}")
    
    return ExperimentConfig(**data)


def save_experiment_config(config: ExperimentConfig, path: Path) -> None:
    """Save experiment configuration to YAML file.
    
    Args:
        config: ExperimentConfig instance
        path: Output path
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        yaml.dump(config.to_dict(), f, default_flow_style=False, allow_unicode=True)
