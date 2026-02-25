# Embedding Module

This module provides functionality to vectorize text files from the `prompt_list` directory using the bailian RemoteChat API, with optional GPU-accelerated vector storage using cuVS.

## Features

- Vectorize text files from `prompt_list` class folders
- Uses bailian LLM API through RemoteChat
- **GPU-accelerated vector storage with cuVS** (optional)
- Efficient similarity search for large-scale embeddings
- Batch processing with configurable parameters
- Automatic retry mechanism for failed requests
- Statistics tracking and logging
- Google-style Python code with comprehensive documentation

## Configuration

Edit `embedding/config.yaml` to configure:

- **API Settings**: API key, proxy, model name
- **Paths**: Input directory, output directory
- **Processing**: Batch size, retries, delays
- **Filters**: File extensions, target folders
- **Vector Store**: cuVS GPU-accelerated storage (optional)

## Usage

### Basic Usage

Process all folders in prompt_list:

```python
from embedding import TextEmbedder

embedder = TextEmbedder()
embedder.process_all_classes()
```

### Process Specific Folders

```python
embedder = TextEmbedder()
embedder.process_all_classes(target_folders=['Chart_1', 'Chart_2', 'Cli_11'])
```

### Process Single File

```python
from pathlib import Path

embedder = TextEmbedder()
result = embedder.process_file(
    file_path=Path('/path/to/file.txt'),
    class_name='Chart_1'
)
```

### Command Line

```bash
cd /home/base/APR/D4C/embedding
python embedder.py
```

### Batch Processing by Category

Process embeddings by project category:

```bash
# List all available categories
python batch_process.py --list

# Process all Chart folders
python batch_process.py --category Chart

# Process multiple categories
python batch_process.py --categories Chart Cli Closure

# Process a range (e.g., Chart_1 to Chart_10)
python batch_process.py --range Chart 1 10
```

## Clustering Visualization

If you have already generated `clustering_results.json` via `hierarchical_clustering.py`, you can render PNG images (headless-friendly) with:

```bash
cd /home/base/APR/D4C/embedding
python plot_clusters.py --level 0 --outdir cluster_plots
```

To render all levels and the parent/child hierarchy tree:

```bash
cd /home/base/APR/D4C/embedding
python plot_clusters.py --all-levels --tree --outdir cluster_plots
```

Notes:
- `--level` corresponds to `level_N` in `clustering_results.json` (default: deepest).
- `--all-levels` will output `scatter_level_N.png` and `cluster_sizes_level_N.png` for each level.
- `--tree` will output `hierarchy_tree.png` to show the hierarchical parent/child structure.
- The script reads embeddings from `embedding/vector_index/` (`vectors.npy` + `id_mapping.pkl`).

## Export Cluster Slugs

To export hierarchical clustering results into per-level JSON files that list the slugs (e.g. `Chart_1` -> `chart_1`) contained in each cluster:

```bash
cd /home/base/APR/D4C/embedding
python export_cluster_slugs.py --outdir cluster_exports
```

This will generate `cluster_exports/level_0.json`, `cluster_exports/level_1.json`, etc.

## Diversity Sampling (Greedy k-DPP)

If you want to select a *diverse* representative subset from `clustering_results.json`, you can use the greedy k-DPP sampler in `D4C/dpp/`:

```bash
python /home/base/APR/D4C/dpp/kdpp_sampling.py \
  --input /home/base/APR/D4C/embedding/clustering_results.json \
  --index-path /home/base/APR/D4C/embedding/vector_index \
  --level 1 \
  --k 32 \
  --seed 42 \
  --out /home/base/APR/D4C/dpp/out_level1_k32
```

See `D4C/dpp/README.md` for details (inputs/outputs/parameters).

## Output Structure

Embeddings are saved in JSON format:

```
embedding/vectors/
├── Chart_1_embeddings.json
├── Chart_2_embeddings.json
├── Cli_11_embeddings.json
└── statistics.json
```

Each embedding file contains:

```json
[
  {
    "file_path": "/path/to/file.txt",
    "class_name": "Chart_1",
    "file_name": "BUGGY_CODE.txt",
    "status": "success",
    "embedding": "...",
    "tokens": 1234,
    "timestamp": "2025-12-15T10:30:00",
    "content_length": 5678
  }
]
```

## Configuration Example

```yaml
embedding_config:
  api_key: sk-4d88933783f844ed99cc603b0ac4a70d
  proxy: bailian
  model: text-embedding-v3
  
  prompt_list_dir: /home/base/APR/D4C/prompt_list
  output_dir: /home/base/APR/D4C/embedding/vectors
  
  batch_size: 10
  max_retries: 3
  retry_delay: 2
  
  file_extensions:
    - .txt
    - .py
    - .json
  
  target_folders: []  # Empty to process all
  
  # GPU-accelerated vector storage (requires CUDA)
  use_vector_store: false  # Set to true to enable cuVS
  vector_store:
    index_path: /home/base/APR/D4C/embedding/vector_index
    index_type: ivf_flat  # Options: ivf_flat, ivf_pq, cagra
    metric: l2  # Options: l2, inner_product
    nlist: 100  # Number of clusters
    nprobe: 10  # Clusters to search
```

## GPU-Accelerated Vector Storage (cuVS)

### Overview

The module supports optional GPU-accelerated vector storage using NVIDIA cuVS (CUDA Vector Search). This provides:

- **Fast similarity search**: GPU-accelerated nearest neighbor queries
- **Scalability**: Efficient indexing for 10K+ vectors
- **Multiple index types**: IVF-Flat, IVF-PQ, CAGRA with different speed/accuracy tradeoffs
- **Persistent storage**: Save and load indices from disk

### Requirements

**Hardware:**
- NVIDIA GPU with CUDA support (Compute Capability 7.0+)
- Sufficient GPU memory (depends on dataset size and index type)

**Software:**
```bash
pip install pylibraft-cu12 cuvs-cu12 rmm-cu12 cupy-cuda12x
```

**Note**: If CUDA is not available, the module gracefully falls back to CPU-based NumPy search.

### Enable Vector Storage

In `config.yaml`, set:
```yaml
use_vector_store: true
```

### Index Types

1. **IVF-Flat** (Default)
   - Good accuracy, moderate speed
   - Best for: Medium datasets (<100K vectors)
   - Memory: Full precision vectors
   
2. **IVF-PQ**
   - Compressed index, fast search
   - Best for: Large datasets with memory constraints
   - Memory: Reduced via product quantization
   
3. **CAGRA**
   - State-of-the-art graph-based index
   - Best for: Large datasets (>100K vectors) requiring best accuracy
   - Memory: Higher than IVF but better recall

### Usage Examples

**Generate embeddings with vector storage:**
```bash
# First, enable in config.yaml: use_vector_store: true
python embedder.py --range Chart 1 10
```

**Migrate existing JSON embeddings to cuVS:**
```bash
python migrate_to_cuvs.py /home/base/APR/D4C/embedding/vectors \
    --index-type ivf_flat \
    --verify
```

**Search for similar vectors:**
```python
from embedding.vector_store import VectorStore
import numpy as np

# Load existing vector store
config = {'index_type': 'ivf_flat', 'metric': 'l2', 'nprobe': 10}
vs = VectorStore('/path/to/index', config)

# Search for similar vectors
query_vector = np.random.randn(768).astype(np.float32)
results = vs.search(query_vector, k=10)

for vec_id, distance in results:
    metadata = vs.get_metadata(vec_id)
    print(f"{vec_id}: distance={distance:.4f}, folder={metadata['folder']}")
```

### Performance Tuning

**For small datasets (<10K vectors):**
```yaml
index_type: ivf_flat
nlist: 100
nprobe: 10
```

**For medium datasets (10K-100K vectors):**
```yaml
index_type: ivf_flat
nlist: 1000
nprobe: 50
```

**For large datasets (>100K vectors):**
```yaml
index_type: cagra
graph_degree: 64
```

**For memory-constrained systems:**
```yaml
index_type: ivf_pq
pq_dim: 64  # Compression ratio
```

## Requirements

- Python 3.7+
- PyYAML
- requests
- retry

**Optional (for GPU vector storage):**
- pylibraft-cu12
- cuvs-cu12
- rmm-cu12
- cupy-cuda12x

Install base dependencies:
```bash
pip install pyyaml requests retry
```

Install GPU dependencies (optional):
```bash
pip install pylibraft-cu12 cuvs-cu12 rmm-cu12 cupy-cuda12x
```

## API Support

The module supports two methods for generating embeddings:

1. **Dedicated Embedding API** (Recommended): Uses `/embeddings` endpoint for efficient vector generation
2. **Chat Completion Fallback**: Uses chat API when embedding endpoint is not available

The module automatically selects the appropriate method based on the configured proxy.

## Examples

See `example_usage.py` for detailed examples:

```bash
# Run example 1: Process all folders
python example_usage.py 1

# Run example 2: Process specific folders
python example_usage.py 2

# Run example 3: Process single file
python example_usage.py 3
```

## Logging

The module uses Python's logging module. Logs include:
- Processing progress
- Success/failure status
- Token usage
- Error messages

## Error Handling

- Automatic retry with exponential backoff
- Graceful handling of empty files
- Detailed error logging
- Statistics tracking for failed operations

## Output Format

The embedding output depends on the API used:
- **Embedding API**: Returns array of floats (e.g., [0.123, -0.456, ...])
- **Chat Fallback**: Returns string representation

Both formats are saved in the same JSON structure for consistency.
