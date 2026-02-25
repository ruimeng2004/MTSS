## ADDED Requirements

### Requirement: Vector Store Initialization
The embedding module SHALL support initializing a cuVS-backed vector store for GPU-accelerated vector operations.

#### Scenario: Initialize new vector store
- **WHEN** `use_vector_store: true` is set in configuration
- **THEN** a cuVS index SHALL be created with configured parameters (index type, distance metric)
- **AND** the index path SHALL be created if it does not exist

#### Scenario: Load existing vector store
- **WHEN** an existing cuVS index is found at the configured path
- **THEN** the index SHALL be loaded into GPU memory
- **AND** metadata SHALL be restored from accompanying JSON file

#### Scenario: GPU not available
- **WHEN** CUDA-capable GPU is not detected
- **THEN** initialization SHALL fail with informative error message
- **AND** error message SHALL suggest disabling `use_vector_store` option

### Requirement: Vector Insertion
The embedding module SHALL support inserting embeddings into the vector store with associated metadata.

#### Scenario: Insert single embedding
- **WHEN** a text file is embedded successfully
- **THEN** the embedding vector SHALL be added to cuVS index
- **AND** metadata (file name, class folder, timestamp) SHALL be stored
- **AND** a unique vector ID SHALL be assigned

#### Scenario: Batch insert embeddings
- **WHEN** multiple files in a folder are embedded
- **THEN** all embeddings SHALL be inserted in a single batch operation
- **AND** the cuVS index SHALL be optimized after batch insertion

#### Scenario: Duplicate vector ID
- **WHEN** an embedding with an existing ID is inserted
- **THEN** the old vector SHALL be replaced with the new vector
- **AND** metadata SHALL be updated accordingly

### Requirement: Vector Similarity Search
The embedding module SHALL support GPU-accelerated k-nearest neighbor search on stored vectors.

#### Scenario: Find similar vectors
- **WHEN** a query vector is provided
- **THEN** the k most similar vectors SHALL be retrieved from cuVS index
- **AND** results SHALL include vector IDs, distances, and metadata
- **AND** search SHALL complete in sub-second time for indices <100K vectors

#### Scenario: Batch similarity search
- **WHEN** multiple query vectors are provided
- **THEN** all queries SHALL be processed in parallel on GPU
- **AND** results SHALL be returned as a batch with consistent ordering

### Requirement: Index Persistence
The embedding module SHALL support saving and loading cuVS indices to/from disk.

#### Scenario: Save index after updates
- **WHEN** new embeddings are added to the vector store
- **THEN** the cuVS index SHALL be saved to the configured path
- **AND** metadata SHALL be saved as JSON alongside the index
- **AND** cuVS version information SHALL be stored for compatibility checking

#### Scenario: Load persisted index
- **WHEN** the embedder is initialized with an existing index path
- **THEN** the cuVS index SHALL be loaded without rebuilding
- **AND** vector count SHALL be verified against metadata

### Requirement: Index Configuration
The embedding module SHALL support configurable cuVS index parameters for performance tuning.

#### Scenario: Configure index type
- **WHEN** `index_type: ivf_flat` is specified in configuration
- **THEN** an IVF-Flat index SHALL be created with specified `nlist` and `nprobe` parameters
- **AND** the same applies for `ivf_pq` and `cagra` index types

#### Scenario: Configure distance metric
- **WHEN** `distance_metric: l2` is specified
- **THEN** L2 (Euclidean) distance SHALL be used for similarity computation
- **AND** supported metrics SHALL include: l2, inner_product, cosine

#### Scenario: Invalid configuration
- **WHEN** invalid index parameters are provided
- **THEN** initialization SHALL fail with descriptive validation error
- **AND** error message SHALL list valid options

### Requirement: JSON Backward Compatibility
The embedding module SHALL maintain JSON export functionality when vector store is enabled.

#### Scenario: Dual output mode
- **WHEN** `use_vector_store: true` and `export_json: true`
- **THEN** embeddings SHALL be saved to both cuVS index AND JSON files
- **AND** JSON format SHALL remain unchanged from current implementation

#### Scenario: JSON-only fallback
- **WHEN** `use_vector_store: false` in configuration
- **THEN** embeddings SHALL be saved only to JSON files
- **AND** no cuVS operations SHALL be attempted

### Requirement: Data Migration from JSON
The embedding module SHALL provide utilities to migrate existing JSON embeddings to cuVS indices.

#### Scenario: Migrate folder embeddings
- **WHEN** migration script is run on a folder with JSON embedding files
- **THEN** all embeddings SHALL be loaded from JSON
- **AND** a cuVS index SHALL be built from the loaded vectors
- **AND** metadata SHALL be extracted from file names and folder structure

#### Scenario: Migration progress tracking
- **WHEN** migrating large datasets (>10K vectors)
- **THEN** progress SHALL be displayed with a progress bar
- **AND** estimated time remaining SHALL be shown

#### Scenario: Migration verification
- **WHEN** migration completes
- **THEN** vector count in cuVS index SHALL match JSON file count
- **AND** a sample of vectors SHALL be compared for correctness

### Requirement: Batch Vector Retrieval for Clustering
The embedding module SHALL support retrieving all stored vectors for downstream clustering operations.

#### Scenario: Retrieve all vectors
- **WHEN** clustering analysis is initiated
- **THEN** all vectors SHALL be retrieved from cuVS index in batches
- **AND** metadata SHALL be retrieved in synchronized order
- **AND** vectors SHALL be returned as GPU tensors or NumPy arrays (configurable)

#### Scenario: Memory-efficient retrieval
- **WHEN** retrieving vectors larger than available GPU memory
- **THEN** vectors SHALL be streamed in configurable batch sizes
- **AND** out-of-memory errors SHALL be prevented

### Requirement: Error Handling and Diagnostics
The embedding module SHALL provide robust error handling for vector store operations.

#### Scenario: Index corruption detection
- **WHEN** a corrupted cuVS index is detected on load
- **THEN** a clear error message SHALL be displayed
- **AND** instructions to rebuild from JSON backup SHALL be provided

#### Scenario: Dimensionality mismatch
- **WHEN** an embedding with wrong dimensionality is inserted
- **THEN** insertion SHALL fail with validation error
- **AND** expected vs actual dimensions SHALL be reported

#### Scenario: GPU out of memory
- **WHEN** cuVS operations exceed available GPU memory
- **THEN** a clear error message SHALL be displayed
- **AND** suggestions for mitigation (PQ compression, smaller batches) SHALL be provided
