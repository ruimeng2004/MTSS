"""
Example usage of VectorStore with embedder
Demonstrates end-to-end workflow from embedding generation to similarity search
"""
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent))

from embedding.vector_store import VectorStore
import numpy as np


def example_search():
    """Example: Search for similar vectors in an existing store"""
    print("=" * 60)
    print("Example: Vector Similarity Search")
    print("=" * 60)
    
    # Configuration
    config = {
        'index_type': 'ivf_flat',
        'metric': 'l2',
        'nprobe': 10,
    }
    
    # Path to existing vector store (created by embedder or migration)
    index_path = "/home/base/APR/D4C/embedding/vector_index"
    
    # Check if index exists
    if not Path(index_path).exists():
        print(f"\nVector store not found at: {index_path}")
        print("Please run embedder with use_vector_store=true first, or use migrate_to_cuvs.py")
        return
    
    # Load vector store
    print(f"\nLoading vector store from: {index_path}")
    vs = VectorStore(index_path, config)
    
    if len(vs) == 0:
        print("Vector store is empty!")
        return
    
    print(f"Loaded: {vs}")
    print(f"Total vectors: {len(vs)}")
    
    # Get a random vector as query
    all_ids = vs.get_all_ids()
    if not all_ids:
        print("No vectors in store")
        return
    
    # Use the first vector as a query
    query_id = all_ids[0]
    query_vector = vs.get_vector(query_id)
    query_meta = vs.get_metadata(query_id)
    
    print(f"\nQuery vector: {query_id}")
    print(f"  Folder: {query_meta.get('folder')}")
    print(f"  File: {query_meta.get('file_name')}")
    
    # Search for similar vectors
    print(f"\nSearching for top 10 similar vectors...")
    results = vs.search(query_vector, k=10)
    
    print(f"\nTop 10 most similar vectors:")
    print(f"{'Rank':<6} {'Vector ID':<30} {'Distance':<12} {'Folder':<15} {'File'}")
    print("-" * 100)
    
    for i, (vec_id, distance) in enumerate(results, 1):
        meta = vs.get_metadata(vec_id)
        folder = meta.get('folder', 'N/A')
        file_name = meta.get('file_name', 'N/A')
        print(f"{i:<6} {vec_id:<30} {distance:<12.4f} {folder:<15} {file_name}")
    
    # Analyze results by folder
    print(f"\nDistribution by folder:")
    folder_counts = {}
    for vec_id, _ in results:
        meta = vs.get_metadata(vec_id)
        folder = meta.get('folder', 'Unknown')
        folder_counts[folder] = folder_counts.get(folder, 0) + 1
    
    for folder, count in sorted(folder_counts.items(), key=lambda x: -x[1]):
        print(f"  {folder}: {count} vectors")
    
    print("\n" + "=" * 60)


def example_batch_search():
    """Example: Batch search for multiple queries"""
    print("\n" + "=" * 60)
    print("Example: Batch Vector Search")
    print("=" * 60)
    
    config = {
        'index_type': 'ivf_flat',
        'metric': 'l2',
        'nprobe': 10,
    }
    
    index_path = "/home/base/APR/D4C/embedding/vector_index"
    
    if not Path(index_path).exists():
        print(f"\nVector store not found at: {index_path}")
        return
    
    vs = VectorStore(index_path, config)
    
    if len(vs) < 5:
        print("Not enough vectors for batch search")
        return
    
    # Get 5 random vectors as queries
    all_ids = vs.get_all_ids()
    query_ids = all_ids[:5]
    query_vectors = np.array([vs.get_vector(vid) for vid in query_ids])
    
    print(f"\nPerforming batch search for {len(query_ids)} queries...")
    results = vs.batch_search(query_vectors, k=5)
    
    for i, (query_id, query_results) in enumerate(zip(query_ids, results), 1):
        print(f"\nQuery {i}: {query_id}")
        print(f"  Top 5 results:")
        for vec_id, distance in query_results[:5]:
            meta = vs.get_metadata(vec_id)
            print(f"    - {vec_id} (distance={distance:.4f})")
    
    print("\n" + "=" * 60)


def example_retrieve_vectors():
    """Example: Retrieve all vectors for clustering"""
    print("\n" + "=" * 60)
    print("Example: Retrieve Vectors for Clustering")
    print("=" * 60)
    
    config = {
        'index_type': 'ivf_flat',
        'metric': 'l2',
    }
    
    index_path = "/home/base/APR/D4C/embedding/vector_index"
    
    if not Path(index_path).exists():
        print(f"\nVector store not found at: {index_path}")
        return
    
    vs = VectorStore(index_path, config)
    
    if len(vs) == 0:
        print("Vector store is empty!")
        return
    
    # Get all vectors
    print(f"\nRetrieving all {len(vs)} vectors...")
    all_vectors = vs.get_all_vectors()
    all_ids = vs.get_all_ids()
    
    print(f"Retrieved array shape: {all_vectors.shape}")
    print(f"Vector dimension: {all_vectors.shape[1]}")
    
    # Example: Compute pairwise distances (for small datasets)
    if len(all_vectors) <= 100:
        print(f"\nComputing pairwise distances...")
        # Compute pairwise Euclidean distances using numpy
        from numpy.linalg import norm
        sample = all_vectors[:10]
        distances = np.zeros((len(sample), len(sample)))
        for i in range(len(sample)):
            for j in range(len(sample)):
                distances[i, j] = norm(sample[i] - sample[j])
        print(f"Distance matrix shape: {distances.shape}")
        print(f"Sample distances:\n{distances[:5, :5]}")
    else:
        print(f"\nDataset too large for full pairwise distance computation")
        print(f"Consider using hierarchical clustering with sampling")
    
    print("\n" + "=" * 60)


if __name__ == '__main__':
    try:
        example_search()
        example_batch_search()
        example_retrieve_vectors()
        print("\n✓ All examples completed!")
    except Exception as e:
        print(f"\n✗ Example failed: {e}")
        import traceback
        traceback.print_exc()
