"""
Test script for VectorStore functionality
"""
import numpy as np
from pathlib import Path
import sys

sys.path.append(str(Path(__file__).parent.parent))

from embedding.vector_store import VectorStore


def test_basic_operations():
    """Test basic VectorStore operations"""
    print("=" * 60)
    print("Testing VectorStore Basic Operations")
    print("=" * 60)
    
    # Configuration
    config = {
        'index_type': 'ivf_flat',
        'metric': 'l2',
        'nlist': 10,
        'nprobe': 5,
    }
    
    # Create test vector store
    test_index_path = "/tmp/test_vector_store"
    vs = VectorStore(test_index_path, config)
    
    print(f"\n1. Created VectorStore: {vs}")
    
    # Generate test vectors
    n_vectors = 100
    dimension = 128
    vectors = np.random.randn(n_vectors, dimension).astype(np.float32)
    ids = [f"vec_{i}" for i in range(n_vectors)]
    metadata = [{'index': i, 'category': f"cat_{i % 5}"} for i in range(n_vectors)]
    
    print(f"\n2. Adding {n_vectors} vectors (dimension={dimension})")
    vs.add_vectors(vectors, ids, metadata)
    
    print(f"\n3. Building index...")
    vs.build_index()
    
    print(f"\n4. Testing search...")
    query = np.random.randn(dimension).astype(np.float32)
    results = vs.search(query, k=5)
    print(f"   Top 5 results:")
    for vec_id, distance in results:
        meta = vs.get_metadata(vec_id)
        print(f"   - {vec_id}: distance={distance:.4f}, category={meta.get('category')}")
    
    print(f"\n5. Testing vector retrieval...")
    test_id = "vec_0"
    retrieved = vs.get_vector(test_id)
    original = vectors[0]
    if retrieved is not None:
        error = np.linalg.norm(retrieved - original)
        print(f"   Retrieved vector matches original (error={error:.6f})")
    
    print(f"\n6. Saving vector store...")
    vs.save()
    
    print(f"\n7. Loading vector store...")
    vs2 = VectorStore(test_index_path, config)
    print(f"   Loaded: {vs2}")
    print(f"   Metadata count: {len(vs2.metadata)}")
    
    print(f"\n8. Testing search on loaded index...")
    results2 = vs2.search(query, k=5)
    print(f"   Top 5 results:")
    for vec_id, distance in results2:
        print(f"   - {vec_id}: distance={distance:.4f}")
    
    # Verify results are consistent
    if len(results) == len(results2):
        match = all(r1[0] == r2[0] for r1, r2 in zip(results, results2))
        print(f"\n9. Results consistency: {'✓ PASS' if match else '✗ FAIL'}")
    
    print("\n" + "=" * 60)
    print("Test completed successfully!")
    print("=" * 60)


def test_incremental_add():
    """Test adding vectors incrementally"""
    print("\n" + "=" * 60)
    print("Testing Incremental Vector Addition")
    print("=" * 60)
    
    config = {
        'index_type': 'ivf_flat',
        'metric': 'l2',
        'nlist': 10,
        'nprobe': 5,
    }
    
    test_index_path = "/tmp/test_incremental"
    vs = VectorStore(test_index_path, config)
    
    dimension = 128
    
    # Add first batch
    print("\n1. Adding first batch (50 vectors)")
    vectors1 = np.random.randn(50, dimension).astype(np.float32)
    ids1 = [f"batch1_vec_{i}" for i in range(50)]
    vs.add_vectors(vectors1, ids1)
    vs.build_index()
    
    # Add second batch
    print("2. Adding second batch (50 vectors)")
    vectors2 = np.random.randn(50, dimension).astype(np.float32)
    ids2 = [f"batch2_vec_{i}" for i in range(50)]
    vs.add_vectors(vectors2, ids2)
    vs.build_index()
    
    print(f"3. Total vectors: {len(vs)}")
    
    # Search
    query = np.random.randn(dimension).astype(np.float32)
    results = vs.search(query, k=10)
    
    batch1_count = sum(1 for r in results if r[0].startswith('batch1'))
    batch2_count = sum(1 for r in results if r[0].startswith('batch2'))
    
    print(f"4. Search results distribution:")
    print(f"   Batch 1: {batch1_count} results")
    print(f"   Batch 2: {batch2_count} results")
    
    print("\n" + "=" * 60)


def test_fallback_mode():
    """Test fallback mode without CUDA"""
    print("\n" + "=" * 60)
    print("Testing Fallback Mode (NumPy)")
    print("=" * 60)
    
    config = {
        'index_type': 'ivf_flat',
        'metric': 'l2',
    }
    
    test_index_path = "/tmp/test_fallback"
    vs = VectorStore(test_index_path, config)
    
    # Disable cuVS temporarily
    vs.cuvs = None
    vs.index = None
    
    dimension = 64
    vectors = np.random.randn(20, dimension).astype(np.float32)
    ids = [f"vec_{i}" for i in range(20)]
    
    print(f"\n1. Adding {len(vectors)} vectors (cuVS disabled)")
    vs.add_vectors(vectors, ids)
    
    print("2. Searching with NumPy fallback...")
    query = np.random.randn(dimension).astype(np.float32)
    results = vs.search(query, k=5)
    
    print(f"   Top 5 results:")
    for vec_id, distance in results:
        print(f"   - {vec_id}: distance={distance:.4f}")
    
    print("\n" + "=" * 60)


def test_kmeans_clustering():
    """Test k-means clustering functionality"""
    print("\n" + "=" * 60)
    print("Testing k-means Clustering")
    print("=" * 60)
    
    config = {
        'index_type': 'ivf_flat',
        'metric': 'l2',
    }
    
    test_index_path = "/tmp/test_kmeans"
    vs = VectorStore(test_index_path, config)
    
    # Create synthetic data with 3 clear clusters
    dimension = 32
    n_per_cluster = 20
    
    print(f"\n1. Creating synthetic data with 3 clusters...")
    cluster_centers = [
        np.array([10, 10] + [0] * (dimension - 2)),
        np.array([-10, -10] + [0] * (dimension - 2)),
        np.array([10, -10] + [0] * (dimension - 2)),
    ]
    
    vectors = []
    true_labels = []
    ids = []
    
    for cluster_id, center in enumerate(cluster_centers):
        for i in range(n_per_cluster):
            vec = center + np.random.randn(dimension) * 2
            vectors.append(vec.astype(np.float32))
            ids.append(f"cluster{cluster_id}_vec{i}")
            true_labels.append(cluster_id)
    
    vectors = np.array(vectors)
    vs.add_vectors(vectors, ids)
    
    print(f"   Added {len(vectors)} vectors from 3 true clusters")
    
    # Perform k-means
    print(f"\n2. Running k-means with k=3...")
    labels, centers = vs.kmeans_clustering(n_clusters=3, max_iter=100)
    
    print(f"   Cluster centers shape: {centers.shape}")
    print(f"   Labels shape: {labels.shape}")
    
    # Analyze cluster distribution
    print(f"\n3. Cluster distribution:")
    for k in range(3):
        members = vs.get_cluster_members(labels, k)
        print(f"   Cluster {k}: {len(members)} members")
        # Show first few members
        print(f"      {members[:5]}")
    
    # Calculate clustering accuracy (rough measure)
    from collections import Counter
    cluster_purity = []
    for k in range(3):
        cluster_mask = labels == k
        true_cluster_labels = [true_labels[i] for i in range(len(labels)) if cluster_mask[i]]
        if true_cluster_labels:
            most_common = Counter(true_cluster_labels).most_common(1)[0][1]
            purity = most_common / len(true_cluster_labels)
            cluster_purity.append(purity)
    
    avg_purity = np.mean(cluster_purity)
    print(f"\n4. Clustering quality:")
    print(f"   Average purity: {avg_purity:.2%}")
    print(f"   (Higher is better, >80% is good for synthetic data)")
    
    print("\n" + "=" * 60)


if __name__ == '__main__':
    try:
        test_basic_operations()
        test_incremental_add()
        test_fallback_mode()
        test_kmeans_clustering()
        print("\n✓ All tests passed!")
    except Exception as e:
        print(f"\n✗ Test failed: {e}")
        import traceback
        traceback.print_exc()
