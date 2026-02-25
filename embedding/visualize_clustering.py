"""
可视化和分析分层聚类结果
"""
import json
import argparse
from pathlib import Path
from collections import defaultdict


def load_results(filepath):
    """加载聚类结果"""
    with open(filepath, 'r', encoding='utf-8') as f:
        return json.load(f)


def print_tree(hierarchy, max_depth=None, indent_size=2):
    """打印聚类树结构"""
    print("\n" + "="*80)
    print("分层聚类树结构")
    print("="*80)
    
    # 按层级组织数据
    levels = sorted(hierarchy.keys(), key=lambda x: int(x.split('_')[1]))
    
    for level_idx, level_name in enumerate(levels):
        if max_depth and level_idx >= max_depth:
            break
        
        level_data = hierarchy[level_name]
        print(f"\n{'='*80}")
        print(f"第 {level_idx + 1} 层: {len(level_data)} 个簇")
        print(f"{'='*80}\n")
        
        # 按父节点组织
        parent_groups = defaultdict(list)
        for cluster_key, cluster_info in level_data.items():
            parent = cluster_info['parent']
            parent_groups[parent].append((cluster_key, cluster_info))
        
        for parent in sorted(parent_groups.keys()):
            clusters = sorted(parent_groups[parent], key=lambda x: x[1]['cluster_id'])
            
            print(f"{parent}:")
            for cluster_key, cluster_info in clusters:
                indent = "  "
                size = cluster_info['size']
                proj_dist = cluster_info['project_distribution']
                
                # 找出主要项目（占比最高的前3个）
                top_projects = sorted(proj_dist.items(), key=lambda x: x[1], reverse=True)[:3]
                proj_str = ", ".join([f"{p}({c})" for p, c in top_projects])
                
                print(f"{indent}├─ {cluster_key}: {size} 个向量")
                print(f"{indent}│  主要项目: {proj_str}")
            print()


def analyze_level(hierarchy, level_idx):
    """分析某一层的详细信息"""
    level_name = f"level_{level_idx}"
    if level_name not in hierarchy:
        print(f"❌ 第 {level_idx + 1} 层不存在")
        return
    
    level_data = hierarchy[level_name]
    print(f"\n{'='*80}")
    print(f"第 {level_idx + 1} 层详细分析")
    print(f"{'='*80}\n")
    print(f"总簇数: {len(level_data)}")
    
    # 统计信息
    sizes = [info['size'] for info in level_data.values()]
    print(f"簇大小: 最小={min(sizes)}, 最大={max(sizes)}, 平均={sum(sizes)/len(sizes):.1f}")
    
    # 按大小排序显示
    sorted_clusters = sorted(level_data.items(), key=lambda x: x[1]['size'], reverse=True)
    
    print(f"\n按大小排序的簇:")
    for i, (cluster_key, cluster_info) in enumerate(sorted_clusters, 1):
        print(f"\n{i}. {cluster_key}")
        print(f"   父节点: {cluster_info['parent']}")
        print(f"   大小: {cluster_info['size']} 个向量")
        print(f"   项目分布:")
        
        proj_dist = cluster_info['project_distribution']
        for proj, count in sorted(proj_dist.items(), key=lambda x: x[1], reverse=True):
            pct = count / cluster_info['size'] * 100
            print(f"     {proj:15s}: {count:3d} ({pct:5.1f}%)")


def show_cluster_details(hierarchy, cluster_key):
    """显示某个簇的详细信息"""
    # 查找簇所在的层级
    found = False
    for level_name, level_data in hierarchy.items():
        if cluster_key in level_data:
            cluster_info = level_data[cluster_key]
            found = True
            break
    
    if not found:
        print(f"❌ 未找到簇: {cluster_key}")
        return
    
    print(f"\n{'='*80}")
    print(f"簇详细信息: {cluster_key}")
    print(f"{'='*80}\n")
    print(f"层级: {level_name}")
    print(f"父节点: {cluster_info['parent']}")
    print(f"簇ID: {cluster_info['cluster_id']}")
    print(f"大小: {cluster_info['size']} 个向量")
    
    print(f"\n项目分布:")
    proj_dist = cluster_info['project_distribution']
    for proj, count in sorted(proj_dist.items(), key=lambda x: x[1], reverse=True):
        pct = count / cluster_info['size'] * 100
        print(f"  {proj:15s}: {count:3d} ({pct:5.1f}%)")
    
    print(f"\n包含的向量 (前20个):")
    for i, vec_meta in enumerate(cluster_info['vectors'][:20], 1):
        print(f"  {i:2d}. {vec_meta['id']:30s} ({vec_meta['folder']})")
    
    if len(cluster_info['vectors']) > 20:
        print(f"  ... 还有 {len(cluster_info['vectors']) - 20} 个向量")


def project_distribution_summary(hierarchy):
    """按项目统计分布"""
    print(f"\n{'='*80}")
    print("项目在各层级的分布")
    print(f"{'='*80}\n")
    
    # 收集所有项目
    all_projects = set()
    for level_data in hierarchy.values():
        for cluster_info in level_data.values():
            all_projects.update(cluster_info['project_distribution'].keys())
    
    all_projects = sorted(all_projects)
    
    # 按层级统计每个项目的分布
    levels = sorted(hierarchy.keys(), key=lambda x: int(x.split('_')[1]))
    
    for project in all_projects:
        print(f"\n项目: {project}")
        for level_idx, level_name in enumerate(levels):
            level_data = hierarchy[level_name]
            
            # 统计该项目在这一层各个簇中的分布
            project_clusters = []
            for cluster_key, cluster_info in level_data.items():
                count = cluster_info['project_distribution'].get(project, 0)
                if count > 0:
                    project_clusters.append((cluster_key, count))
            
            if project_clusters:
                total = sum(c[1] for c in project_clusters)
                clusters_str = ", ".join([f"{k}({c})" for k, c in sorted(project_clusters, key=lambda x: x[1], reverse=True)[:3]])
                print(f"  第{level_idx+1}层: {len(project_clusters)} 个簇, {total} 个向量 - 主要在: {clusters_str}")


def main():
    parser = argparse.ArgumentParser(description='可视化和分析聚类结果')
    parser.add_argument('--input', type=str, default='clustering_results.json',
                       help='聚类结果文件')
    parser.add_argument('--tree', action='store_true', help='显示完整树结构')
    parser.add_argument('--level', type=int, help='分析指定层级（0-based）')
    parser.add_argument('--cluster', type=str, help='显示指定簇的详细信息')
    parser.add_argument('--projects', action='store_true', help='显示项目分布统计')
    
    args = parser.parse_args()
    
    input_path = Path(__file__).parent / args.input
    
    if not input_path.exists():
        print(f"❌ 文件不存在: {input_path}")
        return
    
    print(f"加载聚类结果: {input_path}")
    results = load_results(input_path)
    
    print(f"\n总向量数: {results['total_vectors']}")
    print(f"向量维度: {results['dimension']}")
    print(f"层级数: {len(results['hierarchy'])}")
    
    hierarchy = results['hierarchy']
    
    if args.tree:
        print_tree(hierarchy)
    
    if args.level is not None:
        analyze_level(hierarchy, args.level)
    
    if args.cluster:
        show_cluster_details(hierarchy, args.cluster)
    
    if args.projects:
        project_distribution_summary(hierarchy)
    
    # 默认显示简要摘要
    if not (args.tree or args.level is not None or args.cluster or args.projects):
        print("\n提示:")
        print("  --tree          显示完整树结构")
        print("  --level N       分析第 N 层（0-based）")
        print("  --cluster KEY   显示指定簇的详细信息")
        print("  --projects      显示项目分布统计")
        
        # 显示简要统计
        print(f"\n{'='*80}")
        print("各层级概览")
        print(f"{'='*80}\n")
        
        for level_idx, level_name in enumerate(sorted(hierarchy.keys(), key=lambda x: int(x.split('_')[1]))):
            level_data = hierarchy[level_name]
            sizes = [info['size'] for info in level_data.values()]
            print(f"第 {level_idx + 1} 层: {len(level_data)} 个簇, "
                  f"大小范围 [{min(sizes)}, {max(sizes)}], 平均 {sum(sizes)/len(sizes):.1f}")


if __name__ == '__main__':
    main()
