"""BTMS - Bug Task Model Selection Pipeline.

A modular pipeline for predicting whether bug fixes should use
edit (editing) or gen (generation) task modeling.
"""

__version__ = "0.1.0"

# Clustering
from .clustering import (
    BaseClusterer,
    ClusteringConfig,
    ClusteringResult,
    ClustererFactory,
    KMeansClusterer,
    HACClusterer,
    BisectingKMeansClusterer,
)

# Sampling
from .sampling import (
    BaseSampler,
    SamplingConfig,
    SamplingResult,
    SamplerFactory,
    FarthestFirstSampler,
    KDPPSampler,
)

# Selection
from .selection import (
    VotingMechanism,
    VoteResult,
    TaskModelSelector,
)

# Experiment
from .experiment import (
    ExperimentConfig,
    ExperimentRunner,
    ReportGenerator,
    load_experiment_config,
    save_experiment_config,
    generate_report,
)

__all__ = [
    # Version
    "__version__",
    # Clustering
    "BaseClusterer",
    "ClusteringConfig",
    "ClusteringResult",
    "ClustererFactory",
    "KMeansClusterer",
    "HACClusterer",
    "BisectingKMeansClusterer",
    # Sampling
    "BaseSampler",
    "SamplingConfig",
    "SamplingResult",
    "SamplerFactory",
    "FarthestFirstSampler",
    "KDPPSampler",
    # Selection
    "VotingMechanism",
    "VoteResult",
    "TaskModelSelector",
    # Experiment
    "ExperimentConfig",
    "ExperimentRunner",
    "ReportGenerator",
    "load_experiment_config",
    "save_experiment_config",
    "generate_report",
]
