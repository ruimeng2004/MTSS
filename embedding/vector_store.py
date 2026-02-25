"""
GPU-accelerated vector storage using cuVS (CUDA Vector Search)
Provides efficient indexing and similarity search for embeddings
"""
import os
import json
import pickle
import warnings
from pathlib import Path
from typing import List, Dict, Tuple, Optional, Any
import numpy as np


class VectorStore:
    """
    Wrapper for cuVS vector database operations
    Supports multiple index types: IVF-Flat, IVF-PQ, CAGRA
    """
    
    def __init__(self, index_path: str, config: Dict[str, Any]):
        """
        Initialize or load existing vector store
        
        Args:
            index_path: Path to store/load the index and metadata
            config: Configuration dictionary with index parameters
                - index_type: 'ivf_flat', 'ivf_pq', or 'cagra'
                - metric: 'l2' or 'inner_product'
                - dimension: Vector dimension (auto-detected from first batch)
                - nlist: Number of clusters for IVF indices
                - nprobe: Number of clusters to search
                - graph_degree: Degree for CAGRA index
        """
        self.index_path = Path(index_path)
        self.index_path.mkdir(parents=True, exist_ok=True)
        
        self.config = config
        self.index_type = config.get('index_type', 'ivf_flat')
        self.metric = config.get('metric', 'l2')
        self.dimension = config.get('dimension', None)
        
        # Check CUDA availability
        self._check_cuda()
        
        # Initialize cuVS components
        self.index = None
        self.vectors = []  # List to accumulate vectors before building index
        self.metadata = {}  # Dict mapping vector_id -> metadata
        self.id_to_idx = {}  # Dict mapping vector_id -> index position
        self.idx_to_id = {}  # Dict mapping index position -> vector_id
        
        # Load existing index if available
        self._load_if_exists()
    
    def _check_cuda(self):
        """Check if CUDA is available and cuVS can be imported"""
        try:
            import cupy as cp
            if not cp.cuda.is_available():
                raise RuntimeError("CUDA is not available")
            
            # Try importing cuVS
            import cuvs
            self.cuvs = cuvs
            self.cp = cp
            print(f"cuVS initialized successfully with CUDA")
        except (ImportError, RuntimeError) as e:
            import warnings
            warnings.warn(
                f"CUDA/cuVS initialization failed: {e}\n"
                "Falling back to CPU-based storage (NumPy only mode)"
            )
            self.cuvs = None
            self.cp = None
    
    def _load_if_exists(self):
        """Load existing index and metadata from disk"""
        index_file = self.index_path / "index.bin"
        metadata_file = self.index_path / "metadata.json"
        mapping_file = self.index_path / "id_mapping.pkl"
        vectors_file = self.index_path / "vectors.npy"
        
        if metadata_file.exists():
            try:
                # Load metadata
                with open(metadata_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.metadata = data['metadata']
                    self.dimension = data['dimension']
                    self.config['cuvs_version'] = data.get('cuvs_version', 'unknown')
                
                # Load ID mappings
                if mapping_file.exists():
                    with open(mapping_file, 'rb') as f:
                        mappings = pickle.load(f)
                        self.id_to_idx = mappings['id_to_idx']
                        self.idx_to_id = mappings['idx_to_id']
                
                # Load vectors from numpy backup
                if vectors_file.exists():
                    vectors_np = np.load(vectors_file)
                    self.vectors = [vec for vec in vectors_np]
                    print(f"Loaded {len(self.vectors)} vectors from numpy backup")
                
                # Load cuVS index if available
                if self.cuvs is not None and index_file.exists():
                    self.index = self._load_index(index_file)
                    print(f"Loaded existing cuVS index with {len(self.metadata)} vectors")
                else:
                    print(f"Loaded metadata for {len(self.metadata)} vectors (no cuVS index)")
            except Exception as e:
                warnings.warn(f"Failed to load existing index: {e}. Starting fresh.")
                self.index = None
                self.metadata = {}
                self.id_to_idx = {}
                self.idx_to_id = {}
                self.vectors = []
    
    def _load_index(self, index_file: Path):
        """Load cuVS index from file"""
        # Note: cuVS index loading depends on index type
        # This is a placeholder - actual implementation depends on cuVS API
        try:
            if self.index_type == 'ivf_flat':
                # Load IVF-Flat index
                import cuvs.neighbors.ivf_flat
                index = cuvs.neighbors.ivf_flat.deserialize(str(index_file))
            elif self.index_type == 'ivf_pq':
                # Load IVF-PQ index
                import cuvs.neighbors.ivf_pq
                index = cuvs.neighbors.ivf_pq.deserialize(str(index_file))
            elif self.index_type == 'cagra':
                # Load CAGRA index
                import cuvs.neighbors.cagra
                index = cuvs.neighbors.cagra.deserialize(str(index_file))
            else:
                raise ValueError(f"Unknown index type: {self.index_type}")
            return index
        except Exception as e:
            warnings.warn(f"Failed to deserialize index: {e}")
            return None
    
    def add_vectors(self, vectors: np.ndarray, ids: List[str], 
                   metadata: Optional[List[Dict]] = None):
        """
        Add vectors to the store with IDs and optional metadata
        
        Args:
            vectors: numpy array of shape (n, dimension)
            ids: List of unique identifiers for each vector
            metadata: Optional list of metadata dicts for each vector
        """
        if len(vectors) != len(ids):
            raise ValueError("Number of vectors must match number of IDs")
        
        if metadata and len(metadata) != len(vectors):
            raise ValueError("Number of metadata entries must match number of vectors")
        
        # Auto-detect dimension from first batch
        if self.dimension is None:
            self.dimension = vectors.shape[1]
        elif vectors.shape[1] != self.dimension:
            raise ValueError(
                f"Vector dimension {vectors.shape[1]} does not match "
                f"expected dimension {self.dimension}"
            )
        
        # Store vectors and metadata
        start_idx = len(self.vectors)
        for i, (vec, vec_id) in enumerate(zip(vectors, ids)):
            idx = start_idx + i
            self.vectors.append(vec)
            self.id_to_idx[vec_id] = idx
            self.idx_to_id[idx] = vec_id
            
            meta = metadata[i] if metadata else {}
            meta['id'] = vec_id
            self.metadata[vec_id] = meta
        
        print(f"Added {len(vectors)} vectors. Total: {len(self.vectors)}")
    
    def build_index(self):
        """Build cuVS index from accumulated vectors"""
        if not self.vectors:
            warnings.warn("No vectors to build index")
            return
        
        if self.cuvs is None:
            warnings.warn("cuVS not available, skipping index build")
            return
        
        print(f"Building {self.index_type} index for {len(self.vectors)} vectors...")
        
        # Convert to cupy array
        vectors_np = np.array(self.vectors, dtype=np.float32)
        vectors_cp = self.cp.array(vectors_np)
        
        try:
            if self.index_type == 'ivf_flat':
                self.index = self._build_ivf_flat(vectors_cp)
            elif self.index_type == 'ivf_pq':
                self.index = self._build_ivf_pq(vectors_cp)
            elif self.index_type == 'cagra':
                self.index = self._build_cagra(vectors_cp)
            else:
                raise ValueError(f"Unknown index type: {self.index_type}")
            
            print(f"Index built successfully")
        except Exception as e:
            warnings.warn(f"Index build failed: {e}")
            self.index = None
    
    def _build_ivf_flat(self, vectors):
        """Build IVF-Flat index"""
        import cuvs.neighbors.ivf_flat
        
        nlist = self.config.get('nlist', min(100, len(self.vectors) // 10))
        
        index_params = cuvs.neighbors.ivf_flat.IndexParams(
            n_lists=nlist,
            metric=self.metric,
        )
        
        index = cuvs.neighbors.ivf_flat.build(index_params, vectors)
        return index
    
    def _build_ivf_pq(self, vectors):
        """Build IVF-PQ index"""
        import cuvs.neighbors.ivf_pq
        
        nlist = self.config.get('nlist', min(100, len(self.vectors) // 10))
        pq_dim = self.config.get('pq_dim', min(64, self.dimension // 2))
        
        index_params = cuvs.neighbors.ivf_pq.IndexParams(
            n_lists=nlist,
            metric=self.metric,
            pq_dim=pq_dim,
        )
        
        index = cuvs.neighbors.ivf_pq.build(index_params, vectors)
        return index
    
    def _build_cagra(self, vectors):
        """Build CAGRA index"""
        import cuvs.neighbors.cagra
        
        graph_degree = self.config.get('graph_degree', 64)
        
        index_params = cuvs.neighbors.cagra.IndexParams(
            metric=self.metric,
            graph_degree=graph_degree,
        )
        
        index = cuvs.neighbors.cagra.build(index_params, vectors)
        return index
    
    def search(self, query_vector: np.ndarray, k: int = 10) -> List[Tuple[str, float]]:
        """
        Search for k nearest neighbors
        
        Args:
            query_vector: Query vector (1D numpy array)
            k: Number of nearest neighbors to return
            
        Returns:
            List of (vector_id, distance) tuples
        """
        if self.index is None:
            return self._search_fallback(query_vector, k)
        
        try:
            # Convert query to cupy array
            query_cp = self.cp.array(query_vector.reshape(1, -1), dtype=np.float32)
            
            # Search parameters
            nprobe = self.config.get('nprobe', 10)
            
            if self.index_type == 'ivf_flat':
                import cuvs.neighbors.ivf_flat
                search_params = cuvs.neighbors.ivf_flat.SearchParams(n_probes=nprobe)
                distances, indices = cuvs.neighbors.ivf_flat.search(
                    search_params, self.index, query_cp, k
                )
            elif self.index_type == 'ivf_pq':
                import cuvs.neighbors.ivf_pq
                search_params = cuvs.neighbors.ivf_pq.SearchParams(n_probes=nprobe)
                distances, indices = cuvs.neighbors.ivf_pq.search(
                    search_params, self.index, query_cp, k
                )
            elif self.index_type == 'cagra':
                import cuvs.neighbors.cagra
                search_params = cuvs.neighbors.cagra.SearchParams()
                distances, indices = cuvs.neighbors.cagra.search(
                    search_params, self.index, query_cp, k
                )
            else:
                raise ValueError(f"Unknown index type: {self.index_type}")
            
            # Convert results to CPU
            distances = self.cp.asnumpy(distances)[0]
            indices = self.cp.asnumpy(indices)[0]
            
            # Map indices to IDs
            results = []
            for idx, dist in zip(indices, distances):
                if idx in self.idx_to_id:
                    vec_id = self.idx_to_id[idx]
                    results.append((vec_id, float(dist)))
            
            return results
        except Exception as e:
            warnings.warn(f"cuVS search failed: {e}. Using fallback.")
            return self._search_fallback(query_vector, k)
    
    def _search_fallback(self, query_vector: np.ndarray, k: int) -> List[Tuple[str, float]]:
        """Fallback to NumPy-based linear search"""
        if not self.vectors:
            return []
        
        vectors_np = np.array(self.vectors, dtype=np.float32)
        
        if self.metric == 'l2':
            distances = np.linalg.norm(vectors_np - query_vector, axis=1)
        else:  # inner_product
            distances = -np.dot(vectors_np, query_vector)
        
        # Get top k (handle case where k > num_vectors)
        k = min(k, len(distances))
        if k >= len(distances):
            # Return all vectors sorted by distance
            sorted_indices = np.argsort(distances)
        else:
            top_indices = np.argpartition(distances, k)[:k]
            sorted_indices = top_indices[np.argsort(distances[top_indices])]
        
        results = []
        for idx in sorted_indices:
            vec_id = self.idx_to_id[idx]
            results.append((vec_id, float(distances[idx])))
        
        return results
    
    def batch_search(self, query_vectors: np.ndarray, k: int = 10) -> List[List[Tuple[str, float]]]:
        """
        Batch search for nearest neighbors
        
        Args:
            query_vectors: Query vectors (2D numpy array)
            k: Number of nearest neighbors to return per query
            
        Returns:
            List of result lists, one per query
        """
        return [self.search(qv, k) for qv in query_vectors]
    
    def get_vector(self, vector_id: str) -> Optional[np.ndarray]:
        """Retrieve a vector by ID"""
        idx = self.id_to_idx.get(vector_id)
        if idx is not None and idx < len(self.vectors):
            return self.vectors[idx]
        return None
    
    def get_metadata(self, vector_id: str) -> Optional[Dict]:
        """Retrieve metadata for a vector"""
        return self.metadata.get(vector_id)
    
    def get_all_vectors(self) -> np.ndarray:
        """Retrieve all vectors as numpy array (for clustering)"""
        if not self.vectors:
            return np.array([])
        return np.array(self.vectors, dtype=np.float32)
    
    def get_all_ids(self) -> List[str]:
        """Get all vector IDs"""
        return list(self.metadata.keys())
    
    def save(self):
        """Persist index and metadata to disk"""
        print(f"Saving vector store to {self.index_path}")
        
        # Save metadata
        metadata_file = self.index_path / "metadata.json"
        with open(metadata_file, 'w', encoding='utf-8') as f:
            json.dump({
                'metadata': self.metadata,
                'dimension': self.dimension,
                'index_type': self.index_type,
                'metric': self.metric,
                'cuvs_version': self._get_cuvs_version(),
                'num_vectors': len(self.vectors),
            }, f, indent=2, ensure_ascii=False)
        
        # Save ID mappings
        mapping_file = self.index_path / "id_mapping.pkl"
        with open(mapping_file, 'wb') as f:
            pickle.dump({
                'id_to_idx': self.id_to_idx,
                'idx_to_id': self.idx_to_id,
            }, f)
        
        # Save cuVS index
        if self.index is not None:
            index_file = self.index_path / "index.bin"
            try:
                if self.index_type == 'ivf_flat':
                    import cuvs.neighbors.ivf_flat
                    cuvs.neighbors.ivf_flat.serialize(str(index_file), self.index)
                elif self.index_type == 'ivf_pq':
                    import cuvs.neighbors.ivf_pq
                    cuvs.neighbors.ivf_pq.serialize(str(index_file), self.index)
                elif self.index_type == 'cagra':
                    import cuvs.neighbors.cagra
                    cuvs.neighbors.cagra.serialize(str(index_file), self.index)
                print(f"Index saved successfully")
            except Exception as e:
                warnings.warn(f"Failed to serialize index: {e}")
        
        # Also save vectors as numpy array for backup
        vectors_file = self.index_path / "vectors.npy"
        if self.vectors:
            np.save(vectors_file, np.array(self.vectors, dtype=np.float32))
        
        print(f"Vector store saved: {len(self.metadata)} vectors")
    
    def kmeans_clustering(self, n_clusters: int, max_iter: int = 300) -> Tuple[np.ndarray, np.ndarray]:
        """
        Perform GPU-accelerated k-means clustering on stored vectors
        
        Args:
            n_clusters: Number of clusters
            max_iter: Maximum iterations for k-means
            
        Returns:
            Tuple of (cluster_labels, cluster_centers)
            - cluster_labels: Array of cluster assignments for each vector
            - cluster_centers: Array of cluster centroids
        """
        if not self.vectors:
            raise ValueError("No vectors to cluster")
        
        vectors_np = np.array(self.vectors, dtype=np.float32)
        
        if self.cuvs is not None and self.cp is not None:
            try:
                # Use cuVS GPU-accelerated k-means
                import cuvs.cluster.kmeans
                
                vectors_cp = self.cp.array(vectors_np)
                
                # K-means parameters
                params = cuvs.cluster.kmeans.KMeansParams(
                    n_clusters=n_clusters,
                    max_iter=max_iter,
                    metric='euclidean' if self.metric == 'l2' else 'inner_product',
                )
                
                # Perform clustering
                centroids, labels, inertia = cuvs.cluster.kmeans.fit_predict(
                    params, vectors_cp
                )
                
                # Convert results back to numpy
                labels_np = self.cp.asnumpy(labels)
                centroids_np = self.cp.asnumpy(centroids)
                
                print(f"GPU k-means completed: {n_clusters} clusters, inertia={inertia:.4f}")
                return labels_np, centroids_np
                
            except Exception as e:
                warnings.warn(f"GPU k-means failed: {e}. Falling back to CPU.")
        
        # CPU fallback using scipy/sklearn-like implementation
        print("Using CPU k-means (slower)...")
        from numpy.random import RandomState
        
        rng = RandomState(42)
        # Simple k-means++ initialization
        n_samples = len(vectors_np)
        centers = np.zeros((n_clusters, self.dimension), dtype=np.float32)
        
        # Initialize first center randomly
        centers[0] = vectors_np[rng.randint(n_samples)]
        
        # K-means++ for remaining centers
        for i in range(1, n_clusters):
            # Compute distances to nearest center
            distances = np.min([np.linalg.norm(vectors_np - c, axis=1) ** 2 
                               for c in centers[:i]], axis=0)
            probs = distances / distances.sum()
            centers[i] = vectors_np[rng.choice(n_samples, p=probs)]
        
        # Lloyd's algorithm
        labels = np.zeros(n_samples, dtype=np.int32)
        for iteration in range(max_iter):
            # Assignment step
            old_labels = labels.copy()
            for i, vec in enumerate(vectors_np):
                distances = np.linalg.norm(centers - vec, axis=1)
                labels[i] = np.argmin(distances)
            
            # Update step
            for k in range(n_clusters):
                mask = labels == k
                if mask.any():
                    centers[k] = vectors_np[mask].mean(axis=0)
            
            # Check convergence
            if np.array_equal(labels, old_labels):
                print(f"CPU k-means converged at iteration {iteration}")
                break
        
        return labels, centers
    
    def get_cluster_members(self, labels: np.ndarray, cluster_id: int) -> List[str]:
        """
        Get vector IDs belonging to a specific cluster
        
        Args:
            labels: Cluster labels from kmeans_clustering()
            cluster_id: Target cluster ID
            
        Returns:
            List of vector IDs in the cluster
        """
        all_ids = self.get_all_ids()
        return [all_ids[i] for i, label in enumerate(labels) if label == cluster_id]
    
    def _get_cuvs_version(self) -> str:
        """Get cuVS version string"""
        try:
            if self.cuvs is not None:
                return getattr(self.cuvs, '__version__', 'unknown')
        except:
            pass
        return 'unknown'
    
    def __len__(self):
        """Return number of vectors in store"""
        return len(self.vectors)
    
    def __repr__(self):
        return (f"VectorStore(type={self.index_type}, vectors={len(self.vectors)}, "
                f"dimension={self.dimension}, metric={self.metric})")
