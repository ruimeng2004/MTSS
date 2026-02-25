## Context

The embedding module currently generates text embeddings and stores them as JSON files. While sufficient for initial prototyping, this approach has limitations:

1. **Performance bottleneck:** Loading large JSON files and computing similarity search in Python/NumPy is slow for >10K vectors
2. **Memory inefficiency:** All vectors must be loaded into memory for similarity operations
3. **No indexing:** Linear search O(n) complexity for nearest-neighbor queries
4. **Clustering readiness:** Hierarchical clustering requires efficient distance matrix computation and incremental updates

cuVS (CUDA Vector Search) addresses these issues:
- GPU-accelerated approximate nearest neighbor (ANN) search
- Multiple index types (IVF-Flat, IVF-PQ, CAGRA) with different speed/accuracy tradeoffs
- Built on RAPIDS ecosystem (interoperable with cuML for GPU-accelerated clustering)
- Persistent disk storage for indices

**Stakeholders:**
- Researchers analyzing embedding similarity patterns
- Future clustering and visualization features
- Performance-sensitive batch processing workflows

## Goals / Non-Goals

### Goals
- Enable GPU-accelerated vector storage and retrieval using cuVS
- Provide seamless integration with existing `TextEmbedder` workflow
- Support multiple index types with configurable parameters
- Maintain backward compatibility (JSON export still available)
- Lay foundation for hierarchical clustering on cuVS-stored vectors
- Allow migration of existing JSON embeddings to cuVS

### Non-Goals
- Implementing complete hierarchical clustering algorithm (separate future change)
- Supporting distributed multi-GPU indexing (single-GPU only)
- Replacing JSON storage entirely (both can coexist)
- Building custom vector database from scratch
- Supporting non-CUDA accelerators (ROCm, Metal, CPU-only fallback)

## Decisions

### Decision: Use cuVS instead of FAISS
**Rationale:**
- cuVS is purpose-built for NVIDIA GPUs and integrates with RAPIDS/cuML
- Hierarchical clustering will benefit from GPU acceleration (cuML provides GPU-based linkage algorithms)
- FAISS requires CPU<->GPU transfers; cuVS keeps data on GPU
- Project already uses CUDA (PyTorch), so CUDA dependency is acceptable

**Alternatives considered:**
- FAISS: More mature but CPU-centric, requires manual GPU transfers
- Milvus/Qdrant: Over-engineered for research use case (need server, REST API)
- ChromaDB: Higher-level but adds unnecessary abstractions
- Plain NumPy: Already proven too slow for large datasets

### Decision: Support multiple index types (IVF-Flat, IVF-PQ, CAGRA)
**Rationale:**
- IVF-Flat: Good accuracy, moderate speed, suitable for medium datasets (<100K vectors)
- IVF-PQ: Compressed index, lower memory, fast search, slight accuracy loss
- CAGRA: State-of-the-art graph-based index, best for large datasets (>100K)
- Expose as config parameter so users can tune speed/accuracy tradeoff

**Default:** IVF-Flat (balanced option, easier to configure)

### Decision: Keep JSON export alongside cuVS
**Rationale:**
- Backward compatibility for existing analysis scripts
- Human-readable format useful for debugging
- Minimal overhead (parallel writes)
- Users can disable JSON if needed

### Decision: Store metadata (file names, folder names) with vectors
**Rationale:**
- Clustering results need traceability to source files
- cuVS doesn't natively support metadata; store as separate dict keyed by vector ID
- Serialize metadata to JSON alongside cuVS index

## Risks / Trade-offs

### Risk: CUDA dependency limits portability
- **Impact:** Cannot run on CPU-only machines or non-NVIDIA GPUs
- **Mitigation:** Keep JSON storage as fallback; document GPU requirements prominently; detect missing CUDA at startup

### Risk: cuVS API stability (early-stage library)
- **Impact:** Breaking changes in future cuVS versions
- **Mitigation:** Pin specific cuVS version in requirements.txt; test with each upgrade

### Risk: Index corruption or incompatibility
- **Impact:** Cannot load saved indices after cuVS update
- **Mitigation:** Store cuVS version metadata with index; add rebuild script from JSON backups

### Trade-off: Memory usage for large indices
- **Impact:** GPU memory limits on single-GPU systems (~24GB for A6000/4090)
- **Mitigation:** Use PQ compression for large datasets; document memory requirements per index type

### Trade-off: Build time for large indices
- **Impact:** Initial index build can take minutes for >100K vectors
- **Mitigation:** Incremental updates for new embeddings; cache built indices; show progress bar

## Migration Plan

### Phase 1: Add cuVS without disrupting existing workflows (this change)
1. Implement `VectorStore` as standalone class
2. Add opt-in flag `use_vector_store: false` in config (default disabled)
3. Keep all existing JSON workflows unchanged
4. Test on subset of data (Chart category only)

### Phase 2: Enable by default after validation
1. Change default to `use_vector_store: true`
2. Run migration script on existing JSON embeddings
3. Verify search results match NumPy-based similarity

### Phase 3: Clustering integration (future change)
1. Implement hierarchical clustering using cuVS + cuML
2. Add visualization utilities for dendrogram/clusters
3. Create analysis notebooks using clustered embeddings

### Rollback Plan
- If cuVS proves unstable: Disable via config, fall back to JSON
- If GPU memory insufficient: Use smaller batch sizes or PQ compression
- If build times too long: Pre-build indices offline, distribute as artifacts

## Implementation Notes

### Index Configuration Recommendations
```yaml
# Small datasets (<10K vectors)
index_type: ivf_flat
nlist: 100
nprobe: 10

# Medium datasets (10K-100K vectors)
index_type: ivf_flat
nlist: 1000
nprobe: 50

# Large datasets (>100K vectors)
index_type: cagra
graph_degree: 64
intermediate_graph_degree: 128
```

### Vector Store API Design
```python
class VectorStore:
    def __init__(self, index_path, config):
        """Initialize or load existing index"""
    
    def add_vectors(self, vectors, ids, metadata):
        """Add vectors with IDs and metadata"""
    
    def search(self, query_vector, k=10):
        """Return k nearest neighbors"""
    
    def batch_search(self, query_vectors, k=10):
        """Batch nearest neighbor search"""
    
    def get_all_vectors(self):
        """Retrieve all vectors (for clustering)"""
    
    def save(self):
        """Persist index to disk"""
```

## Open Questions

1. **Should we support incremental index updates or rebuild on each run?**
   - Proposal: Support both; incremental for small batches, rebuild for bulk operations

2. **What distance metric should be default?**
   - Proposal: L2 (Euclidean) to match typical embedding similarity semantics
   - Alternative: Inner product if embeddings are normalized

3. **Should we compress embeddings with PQ by default?**
   - Proposal: No compression by default (preserve full accuracy); add PQ option for large datasets

4. **How to handle vector dimensionality validation?**
   - Proposal: Store dimension in index metadata; raise error if mismatch on insertion
