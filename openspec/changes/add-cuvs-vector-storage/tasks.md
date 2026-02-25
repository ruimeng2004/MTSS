## 1. Dependencies

- [ ] 1.1 Add `pylibraft` and `cuvs` to requirements.txt
- [ ] 1.2 Document CUDA requirements in embedding/README.md
- [ ] 1.3 Add GPU detection and fallback warning logic

## 2. Vector Store Implementation

- [ ] 2.1 Create `embedding/vector_store.py` with `VectorStore` class
- [ ] 2.2 Implement index building methods (IVF-Flat, IVF-PQ, CAGRA)
- [ ] 2.3 Implement vector insertion (single and batch)
- [ ] 2.4 Implement similarity search (k-nearest neighbors)
- [ ] 2.5 Implement index save/load from disk
- [ ] 2.6 Add metadata storage for vector IDs and source information

## 3. Embedder Integration

- [ ] 3.1 Add `use_vector_store` option to config.yaml
- [ ] 3.2 Add cuVS configuration section (index_type, metric, nlist, nprobe)
- [ ] 3.3 Modify `TextEmbedder.process_file()` to optionally store in cuVS
- [ ] 3.4 Modify `TextEmbedder.process_folders()` to build/update cuVS index
- [ ] 3.5 Maintain JSON export for backward compatibility

## 4. Data Migration Utilities

- [ ] 4.1 Create `embedding/migrate_to_cuvs.py` script
- [ ] 4.2 Implement JSON to cuVS index loader
- [ ] 4.3 Add progress tracking for large migrations
- [ ] 4.4 Add verification step to compare JSON vs cuVS results

## 5. Clustering Foundation

- [ ] 5.1 Create `embedding/clustering.py` module
- [ ] 5.2 Implement batch vector retrieval from cuVS
- [ ] 5.3 Add utility for computing pairwise distances
- [ ] 5.4 Add placeholder for hierarchical clustering integration (scipy/cuML)

## 6. Testing & Documentation

- [ ] 6.1 Add unit tests for `VectorStore` class
- [ ] 6.2 Add integration test for embedder with cuVS enabled
- [ ] 6.3 Update embedding/README.md with cuVS usage examples
- [ ] 6.4 Add configuration examples to embedding/config.yaml comments
- [ ] 6.5 Document performance benchmarks (JSON vs cuVS search)

## 7. Error Handling & Edge Cases

- [ ] 7.1 Handle missing CUDA gracefully with informative error
- [ ] 7.2 Handle cuVS initialization failures
- [ ] 7.3 Add validation for vector dimensionality consistency
- [ ] 7.4 Handle index corruption with rebuild capability
