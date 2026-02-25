"""Core modules for the D4J Fix Evaluation System.

This package contains the main evaluation logic and core components:
- InputHandler: Handles reading and parsing fix result folders
- ConfigLoader: Loads and validates configuration from YAML files
- OutputParser: Parses model output to extract fix patches
- PatchNormalizer: Normalizes patches to unified diff format
- NormalizationReporter: Tracks and reports normalization results
- EnvironmentManager: Manages D4J environment and bug checkouts
- PatchApplicator: Applies normalized patches to repositories
- TestExecutor: Runs D4J tests and collects results
- ResultGenerator: Aggregates evaluation results and generates statistics
- StorageManager: Manages storage of results and intermediate data
- Data structures: Core data structures for the evaluation system
"""

# Only import modules that have been implemented
try:
    from evaluation.core.input_handler import InputHandler
    from evaluation.core.config_loader import ConfigLoader, load_config
    from evaluation.core.output_parser import OutputParser
    from evaluation.core.patch_normalizer import PatchNormalizer
    from evaluation.core.reporter import NormalizationReporter
    from evaluation.core.environment_manager import EnvironmentManager
    from evaluation.core.patch_applicator import PatchApplicator
    from evaluation.core.test_executor import TestExecutor
    from evaluation.core.result_generator import ResultGenerator
    from evaluation.core.storage_manager import StorageManager
    from evaluation.core.evaluator import D4JFixEvaluator
    
    __all__ = [
        "InputHandler",
        "ConfigLoader",
        "load_config",
        "OutputParser",
        "PatchNormalizer",
        "NormalizationReporter",
        "EnvironmentManager",
        "PatchApplicator",
        "TestExecutor",
        "ResultGenerator",
        "StorageManager",
        "D4JFixEvaluator",
    ]
except ImportError:
    __all__ = []
