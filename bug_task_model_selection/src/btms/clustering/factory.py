"""Factory for creating clustering algorithms."""

from __future__ import annotations

from typing import Type

from .base import BaseClusterer, ClusteringConfig
from .bisecting import BisectingKMeansClusterer
from .hac import HACClusterer
from .kmeans import KMeansClusterer


class ClustererFactory:
    """Factory for creating clustering algorithm instances.
    
    Supports registration of new algorithms and creation by name.
    """
    
    _registry: dict[str, Type[BaseClusterer]] = {
        "kmeans": KMeansClusterer,
        "hac_average": HACClusterer,
        "hac_ward": HACClusterer,
        "hac_complete": HACClusterer,
        "hac_single": HACClusterer,
        "bisecting_kmeans": BisectingKMeansClusterer,
    }
    
    @classmethod
    def available_algorithms(cls) -> list[str]:
        """Return list of available algorithm names."""
        return sorted(cls._registry.keys())
    
    @classmethod
    def create(cls, algorithm: str, config: ClusteringConfig) -> BaseClusterer:
        """Create a clusterer instance.
        
        Args:
            algorithm: Algorithm name (e.g., 'kmeans', 'hac_average', 'hac_ward')
            config: Clustering configuration
            
        Returns:
            Clusterer instance
            
        Raises:
            ValueError: If algorithm is not registered
        """
        if algorithm not in cls._registry:
            raise ValueError(
                f"Unknown algorithm: {algorithm}. "
                f"Available: {cls.available_algorithms()}"
            )
        
        # For HAC algorithms, extract linkage from algorithm name
        if algorithm.startswith("hac_"):
            linkage = algorithm.split("_", 1)[1]
            config.extra_params = config.extra_params or {}
            config.extra_params["linkage"] = linkage
        
        clusterer_class = cls._registry[algorithm]
        return clusterer_class(config)
    
    @classmethod
    def register(cls, name: str, clusterer_class: Type[BaseClusterer]) -> None:
        """Register a new clustering algorithm.
        
        Args:
            name: Algorithm name
            clusterer_class: Clusterer class (must inherit from BaseClusterer)
        """
        if not issubclass(clusterer_class, BaseClusterer):
            raise TypeError(
                f"clusterer_class must be a subclass of BaseClusterer, "
                f"got {clusterer_class}"
            )
        cls._registry[name] = clusterer_class
    
    @classmethod
    def unregister(cls, name: str) -> None:
        """Unregister a clustering algorithm.
        
        Args:
            name: Algorithm name to remove
        """
        if name in cls._registry:
            del cls._registry[name]
