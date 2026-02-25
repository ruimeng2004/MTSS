"""Embedding module for D4C project.

This module provides functionality to vectorize text files from prompt_list
using the bailian RemoteChat API.
"""

from .embedder import TextEmbedder

__all__ = ['TextEmbedder']
__version__ = '1.0.0'
