"""Factory for creating sampling algorithms."""

from __future__ import annotations

from typing import Type

from .base import BaseSampler, SamplingConfig
from .farthest_first import FarthestFirstSampler
from .kdpp import KDPPSampler


class SamplerFactory:
    """Factory for creating sampling algorithm instances.
    
    Supports registration of new algorithms and creation by name.
    """
    
    _registry: dict[str, Type[BaseSampler]] = {
        "farthest_first": FarthestFirstSampler,
        "kdpp": KDPPSampler,
    }
    
    @classmethod
    def available_methods(cls) -> list[str]:
        """Return list of available method names."""
        return sorted(cls._registry.keys())
    
    @classmethod
    def create(cls, method: str, config: SamplingConfig) -> BaseSampler:
        """Create a sampler instance.
        
        Args:
            method: Method name (e.g., 'farthest_first', 'kdpp')
            config: Sampling configuration
            
        Returns:
            Sampler instance
            
        Raises:
            ValueError: If method is not registered
        """
        if method not in cls._registry:
            raise ValueError(
                f"Unknown method: {method}. "
                f"Available: {cls.available_methods()}"
            )
        
        sampler_class = cls._registry[method]
        return sampler_class(config)
    
    @classmethod
    def register(cls, name: str, sampler_class: Type[BaseSampler]) -> None:
        """Register a new sampling algorithm.
        
        Args:
            name: Method name
            sampler_class: Sampler class (must inherit from BaseSampler)
        """
        if not issubclass(sampler_class, BaseSampler):
            raise TypeError(
                f"sampler_class must be a subclass of BaseSampler, "
                f"got {sampler_class}"
            )
        cls._registry[name] = sampler_class
    
    @classmethod
    def unregister(cls, name: str) -> None:
        """Unregister a sampling algorithm.
        
        Args:
            name: Method name to remove
        """
        if name in cls._registry:
            del cls._registry[name]
