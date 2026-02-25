"""
使用 cuVS 原生聚类功能进行分层聚类分析
支持 GPU 加速的层次聚类和 K-means 聚类
"""
import json
import yaml
import numpy as np
from pathlib import Path
from collections import defaultdict
import argparse

try:
    import cupy as cp
    import cuvs.cluster  # type: ignore
    CUVS_AVAILABLE = True
except ImportError:
    CUVS_AVAILABLE = False
    print("⚠ 警告: cuVS 不可用，将使用 CPU 版本的聚类")
    cp = None

from vector_store import VectorStore


class HierarchicalClusterer:
    """分层聚类分析器"""
    
    def __init__(self, vector_store: VectorStore, use_gpu=True):
        self.vs = vector_store
        self.use_gpu = use_gpu and CUVS_AVAILABLE
        
        # 获取所有向量
        all_ids = self.vs.get_all_ids()
        self.vectors = np.array([self.vs.get_vector(vid) for vid in all_ids], dtype=np.float32)
        self.vector_ids = all_ids
        self.metadata = [self.vs.get_metadata(vid) for vid in all_ids]
        
        print(f"加载了 {len(self.vectors)} 个向量，维度 {self.vectors.shape[1]}")
        print(f"使用 {'GPU (cuVS)' if self.use_gpu else 'CPU (NumPy)'} 进行聚类")

    def _kmeans_numpy(self, X: np.ndarray, n_clusters: int, *, max_iter: int = 300, seed: int = 42):
        """纯 NumPy K-means（k-means++ 初始化）。

        Returns:
            labels: shape (n,)
            centers: shape (k, d)
        """
        X = np.asarray(X, dtype=np.float32)
        if X.ndim != 2:
            raise ValueError(f"X must be 2D, got {X.shape}")
        n, d = X.shape
        k = int(min(max(1, int(n_clusters)), n))

        rng = np.random.default_rng(seed)

        # k-means++ init
        centers = np.empty((k, d), dtype=np.float32)
        first = int(rng.integers(low=0, high=n))
        centers[0] = X[first]

        closest_dist2 = np.sum((X - centers[0]) ** 2, axis=1).astype(np.float64)
        for i in range(1, k):
            total = float(np.sum(closest_dist2))
            if not np.isfinite(total) or total <= 1e-12:
                centers[i] = X[int(rng.integers(low=0, high=n))]
                continue
            probs = closest_dist2 / total
            idx = int(rng.choice(n, p=probs))
            centers[i] = X[idx]
            dist2 = np.sum((X - centers[i]) ** 2, axis=1).astype(np.float64)
            closest_dist2 = np.minimum(closest_dist2, dist2)

        labels = np.zeros(n, dtype=np.int32)
        for _ in range(int(max_iter)):
            # assign
            # distances: (n, k)
            dists = np.sum((X[:, None, :] - centers[None, :, :]) ** 2, axis=2)
            new_labels = np.argmin(dists, axis=1).astype(np.int32)
            if np.array_equal(new_labels, labels):
                break
            labels = new_labels

            # update centers
            for j in range(k):
                mask = labels == j
                if not np.any(mask):
                    centers[j] = X[int(rng.integers(low=0, high=n))]
                else:
                    centers[j] = np.mean(X[mask], axis=0)

        return labels, centers
    
    def kmeans_clustering(self, n_clusters, max_iter=300):
        """
        K-means 聚类
        
        Args:
            n_clusters: 聚类数量
            max_iter: 最大迭代次数
        
        Returns:
            labels: 聚类标签数组
            centers: 聚类中心
        """
        print(f"\n{'='*60}")
        print(f"K-means 聚类: {n_clusters} 个簇")
        print(f"{'='*60}")
        
        if self.use_gpu:
            # 使用 cuVS K-means
            vectors_gpu = cp.array(self.vectors)
            
            # 配置 K-means 参数
            params = cuvs.cluster.kmeans.KMeansParams(
                n_clusters=n_clusters,
                max_iter=max_iter,
                metric='l2',
                init='k-means++',
                verbose=True
            )
            
            # 执行聚类
            centers, labels = cuvs.cluster.kmeans.fit_predict(
                vectors_gpu,
                params
            )
            
            # 转换回 CPU
            labels = cp.asnumpy(labels)
            centers = cp.asnumpy(centers)
        else:
            # CPU fallback: pure NumPy k-means
            labels, centers = self._kmeans_numpy(self.vectors, int(n_clusters), max_iter=int(max_iter), seed=42)
        
        print("✓ 聚类完成")
        return labels, centers
    
    def hierarchical_kmeans(self, levels, clusters_per_level):
        """
        分层 K-means 聚类
        
        Args:
            levels: 层级数量
            clusters_per_level: 每层的聚类数量列表 [n1, n2, n3, ...]
        
        Returns:
            hierarchy: 分层聚类结果
        """
        print(f"\n{'='*60}")
        print("分层 K-means 聚类")
        print(f"层级: {levels}, 每层聚类数: {clusters_per_level}")
        print(f"{'='*60}\n")
        
        # 第一层：对所有数据聚类
        hierarchy = {}
        current_data = {
            'root': {
                'indices': list(range(len(self.vectors))),
                'vectors': self.vectors,
                'ids': self.vector_ids
            }
        }
        
        for level in range(levels):
            n_clusters = clusters_per_level[level]
            print(f"\n第 {level + 1} 层: 将每个簇分为 {n_clusters} 个子簇")
            
            next_data = {}
            hierarchy[f'level_{level}'] = {}
            
            for parent_key, parent_data in current_data.items():
                parent_vectors = parent_data['vectors']
                parent_indices = parent_data['indices']
                parent_ids = parent_data['ids']

                # 为了保证“每一层都是对全部点的完整划分”，即便簇很小也必须进入下一层。
                # 当簇太小无法可靠切分时，退化为 n_sub=1（单一子簇），把全部成员继承下去。
                n_parent = len(parent_vectors)
                if n_parent <= 0:
                    continue

                n_sub = min(int(n_clusters), int(n_parent))
                if n_sub <= 1:
                    child_key = f"{parent_key}_c0"
                    center = np.mean(parent_vectors, axis=0).tolist() if n_parent > 0 else []

                    hierarchy[f'level_{level}'][child_key] = {
                        'parent': parent_key,
                        'cluster_id': 0,
                        'size': int(n_parent),
                        'indices': parent_indices,
                        'ids': parent_ids,
                        'center': center,
                    }
                    next_data[child_key] = {
                        'indices': parent_indices,
                        'vectors': parent_vectors,
                        'ids': parent_ids,
                    }
                    print(f"  {parent_key}: 向量数 {n_parent}，不切分，继承为 {child_key}")
                    continue

                print(f"  对 {parent_key} 进行聚类 ({n_parent} 个向量, n_sub={n_sub})...")

                # 执行 K-means
                if self.use_gpu:
                    vectors_gpu = cp.array(parent_vectors)
                    params = cuvs.cluster.kmeans.KMeansParams(
                        n_clusters=n_sub,
                        max_iter=300,
                        metric='l2',
                        init='k-means++',
                    )
                    centers, labels = cuvs.cluster.kmeans.fit_predict(vectors_gpu, params)
                    labels = cp.asnumpy(labels)
                    centers = cp.asnumpy(centers)
                else:
                    labels, centers = self._kmeans_numpy(parent_vectors, int(n_sub), max_iter=300, seed=42)

                # 为每个子簇创建数据
                for cluster_id in range(n_sub):
                    mask = labels == cluster_id
                    cluster_indices = [parent_indices[i] for i, m in enumerate(mask) if m]
                    cluster_vectors = parent_vectors[mask]
                    cluster_ids = [parent_ids[i] for i, m in enumerate(mask) if m]

                    child_key = f"{parent_key}_c{cluster_id}"

                    # 保存到层级结构
                    hierarchy[f'level_{level}'][child_key] = {
                        'parent': parent_key,
                        'cluster_id': cluster_id,
                        'size': len(cluster_indices),
                        'indices': cluster_indices,
                        'ids': cluster_ids,
                        'center': centers[cluster_id].tolist()
                    }

                    # 准备下一层的数据
                    next_data[child_key] = {
                        'indices': cluster_indices,
                        'vectors': cluster_vectors,
                        'ids': cluster_ids
                    }

                    print(f"    → {child_key}: {len(cluster_indices)} 个向量")
            
            current_data = next_data
            
            if not current_data:
                print(f"  第 {level + 1} 层没有可继续分割的簇，停止")
                break
        
        return hierarchy
    
    def analyze_clusters(self, labels, level_name=""):
        """分析聚类结果"""
        print(f"\n聚类分析 {level_name}")
        print("=" * 60)
        
        # 统计每个簇的大小
        unique_labels = np.unique(labels)
        cluster_stats = []
        
        for label in unique_labels:
            mask = labels == label
            cluster_ids = [self.vector_ids[i] for i, m in enumerate(mask) if m]
            cluster_meta = [self.metadata[i] for i, m in enumerate(mask) if m]
            
            # 统计项目分布
            project_dist = defaultdict(int)
            for meta in cluster_meta:
                folder = meta.get('folder', 'unknown')
                project = folder.split('_')[0]
                project_dist[project] += 1
            
            cluster_stats.append({
                'label': int(label),
                'size': int(mask.sum()),
                'ids': cluster_ids,
                'project_distribution': dict(project_dist)
            })
        
        # 打印统计信息
        print(f"\n总簇数: {len(unique_labels)}")
        for stat in sorted(cluster_stats, key=lambda x: x['size'], reverse=True):
            print(f"\n簇 {stat['label']}: {stat['size']} 个向量")
            print("  项目分布:")
            for proj, count in sorted(stat['project_distribution'].items(), 
                                     key=lambda x: x[1], reverse=True)[:5]:
                print(f"    {proj}: {count}")
        
        return cluster_stats
    
    def save_results(self, hierarchy, output_file):
        """保存聚类结果"""
        output_path = Path(output_file)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        # 准备输出数据（添加元数据）
        output_data = {
            'total_vectors': len(self.vectors),
            'dimension': self.vectors.shape[1],
            'hierarchy': {}
        }
        
        for level_name, level_data in hierarchy.items():
            output_data['hierarchy'][level_name] = {}
            for cluster_key, cluster_info in level_data.items():
                # 获取簇内向量的元数据
                cluster_metadata = []
                for vec_id in cluster_info['ids']:
                    meta = self.vs.get_metadata(vec_id)
                    cluster_metadata.append({
                        'id': vec_id,
                        'folder': meta.get('folder'),
                        'file': meta.get('file_name'),
                        'tokens': meta.get('tokens')
                    })
                
                # 统计项目分布
                project_dist = defaultdict(int)
                for meta in cluster_metadata:
                    folder = meta.get('folder', 'unknown')
                    project = folder.split('_')[0]
                    project_dist[project] += 1
                
                output_data['hierarchy'][level_name][cluster_key] = {
                    'parent': cluster_info['parent'],
                    'cluster_id': cluster_info['cluster_id'],
                    'size': cluster_info['size'],
                    'center': cluster_info['center'],
                    'project_distribution': dict(project_dist),
                    'vectors': cluster_metadata
                }
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(output_data, f, indent=2, ensure_ascii=False)
        
        print(f"\n✓ 结果已保存到: {output_path}")


def main():
    parser = argparse.ArgumentParser(description='使用 cuVS 进行分层聚类')
    parser.add_argument('--levels', type=int, default=3, help='层级数量')
    parser.add_argument('--clusters', type=str, default='10,5,3', 
                       help='每层的聚类数，逗号分隔，如 "10,5,3"')
    parser.add_argument('--output', type=str, default='clustering_results.json',
                       help='输出文件路径')
    parser.add_argument('--no-gpu', action='store_true', help='禁用 GPU，使用 CPU')
    
    args = parser.parse_args()
    
    # 解析每层的聚类数
    clusters_per_level = [int(x.strip()) for x in args.clusters.split(',')]
    if len(clusters_per_level) != args.levels:
        print(f"警告: 聚类数参数数量 ({len(clusters_per_level)}) 与层级数 ({args.levels}) 不匹配")
        # 自动调整
        if len(clusters_per_level) < args.levels:
            clusters_per_level.extend([3] * (args.levels - len(clusters_per_level)))
        else:
            clusters_per_level = clusters_per_level[:args.levels]
    
    # 加载配置
    config_path = Path(__file__).parent / 'config.yaml'
    with open(config_path, 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)
    
    embedding_config = config.get('embedding_config', {})
    vs_config = embedding_config.get('vector_store', {})
    index_path = vs_config.get('index_path', 'vector_index')
    
    # 加载向量存储
    print(f"加载向量存储: {index_path}")
    vector_store = VectorStore(index_path, vs_config)
    
    # 创建聚类器
    clusterer = HierarchicalClusterer(vector_store, use_gpu=not args.no_gpu)
    
    # 执行分层聚类
    hierarchy = clusterer.hierarchical_kmeans(args.levels, clusters_per_level)
    
    # 保存结果
    output_path = Path(__file__).parent / args.output
    clusterer.save_results(hierarchy, output_path)
    
    print("\n" + "="*60)
    print("分层聚类完成！")
    print(f"总层级数: {len(hierarchy)}")
    print(f"结果文件: {output_path}")
    print("="*60)


if __name__ == '__main__':
    main()
