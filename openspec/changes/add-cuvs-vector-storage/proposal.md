# Change: Integrate cuVS Vector Database for Hierarchical Clustering

## Why

The current embedding module stores vectors as JSON files, which is inefficient for downstream similarity search and clustering operations. To enable hierarchical clustering analysis on embedded prompts/code snippets, we need a GPU-accelerated vector database that supports efficient nearest-neighbor search and batch operations. cuVS (CUDA Vector Search) provides GPU-accelerated indexing and search capabilities optimized for large-scale vector datasets.

## What Changes

- Add cuVS as a dependency for GPU-accelerated vector storage and retrieval
- Implement a `VectorStore` class that wraps cuVS operations (index building, search, batch retrieval)
- Modify `TextEmbedder` to optionally persist embeddings to cuVS index instead of/in addition to JSON
- Add configuration options for cuVS index parameters (index type, distance metric)
- Add utilities for loading existing JSON embeddings into cuVS index
- Create foundation for hierarchical clustering operations on stored vectors
- Maintain backward compatibility with existing JSON-based storage

## Impact

- **Affected specs:** `embedding` (new capability)
- **Affected code:**
  - `embedding/embedder.py` - Add cuVS storage option
  - `embedding/config.yaml` - Add cuVS configuration section
  - `embedding/vector_store.py` - New file for cuVS wrapper
  - `embedding/clustering.py` - New file for clustering utilities (future)
  - `requirements.txt` - Add pylibraft and cuvs dependencies
- **Breaking changes:** None (cuVS storage is opt-in via configuration)
- **Dependencies:** Requires CUDA-enabled GPU, pylibraft, cuvs packages
- **Performance:** Significantly faster similarity search for large datasets (>10K vectors)
