#!/usr/bin/env python3
"""
准备完整的Defects4J实验数据

将现有的PPL数据和聚类数据整理成BTMS预算分配实验所需的格式。
"""

import json
import shutil
from pathlib import Path
from typing import Dict, List

def convert_ppl_format(input_file: Path, output_file: Path):
    """将PPL数据从 {slug, value} 格式转换为标准格式"""
    print(f"  转换: {input_file.name} -> {output_file.name}")
    
    with open(input_file, 'r') as f_in, open(output_file, 'w') as f_out:
        for line in f_in:
            obj = json.loads(line)
            # 保持原格式即可，只是复制
            f_out.write(json.dumps(obj) + '\n')
    
    count = sum(1 for _ in open(output_file))
    print(f"    ✓ {count} 条记录")

def prepare_experiment_data(
    source_dir: Path,
    target_dir: Path,
    model: str = "qwen3_coder",
    clustering_config: str = "buggy_code_kmeans_k100_kdpp_r3"
):
    """准备完整实验数据"""
    
    print(f"\n{'='*80}")
    print(f"准备实验数据: {model} / {clustering_config}")
    print(f"{'='*80}\n")
    
    # 创建目标目录
    target_dir.mkdir(parents=True, exist_ok=True)
    
    # 1. PPL数据
    print("1. 准备PPL数据...")
    ppl_source = source_dir / "bug_task_model_selection/data/ppl"
    
    convert_ppl_format(
        ppl_source / f"{model}_edit.jsonl",
        target_dir / "edit_ppl.jsonl"
    )
    convert_ppl_format(
        ppl_source / f"{model}_gen.jsonl",
        target_dir / "gen_ppl.jsonl"
    )
    
    # 2. 聚类数据
    print("\n2. 准备聚类数据...")
    clustering_source = source_dir / f"bug_task_model_selection/data/exp3_voting_coder/{clustering_config}"
    
    # 复制 representatives.jsonl
    src_reps = clustering_source / "representatives.jsonl"
    dst_reps = target_dir / "representatives.jsonl"
    shutil.copy2(src_reps, dst_reps)
    reps_count = sum(1 for _ in open(dst_reps))
    print(f"  ✓ representatives.jsonl: {reps_count} 条记录")
    
    # 复制 assignments.jsonl  
    src_assign = clustering_source / "assignments.jsonl"
    dst_assign = target_dir / "assignments.jsonl"
    shutil.copy2(src_assign, dst_assign)
    assign_count = sum(1 for _ in open(dst_assign))
    print(f"  ✓ assignments.jsonl: {assign_count} 条记录")
    
    # 3. 统计信息
    print("\n3. 数据统计...")
    
    # 统计簇数
    clusters = set()
    with open(dst_assign, 'r') as f:
        for line in f:
            obj = json.loads(line)
            clusters.add(obj['cluster_id'])
    
    print(f"  总bugs数: {assign_count}")
    print(f"  总簇数: {len(clusters)}")
    print(f"  代表点数: {reps_count}")
    print(f"  平均每簇代表点: {reps_count / len(clusters):.1f}")
    
    print(f"\n✓ 数据准备完成! 输出目录: {target_dir}")
    
    return {
        "bugs": assign_count,
        "clusters": len(clusters),
        "representatives": reps_count
    }

def main():
    """主函数"""
    
    base_dir = Path("/home/base/mengrui/MTSS")
    
    # 准备数据集
    datasets = [
        {
            "name": "qwen3_coder_k100_r3",
            "model": "qwen3_coder",
            "clustering": "buggy_code_kmeans_k100_kdpp_r3",
            "description": "Qwen3-Coder, K=100, KDpp采样r=3"
        },
        {
            "name": "qwen3_30b_k100_r3",
            "model": "qwen3_30b", 
            "clustering": "buggy_code_kmeans_k100_kdpp_r3",
            "description": "Qwen3-30B, K=100, KDpp采样r=3"
        }
    ]
    
    print("\n" + "="*80)
    print("BTMS预算分配实验 - 完整数据准备")
    print("="*80)
    
    results = {}
    
    for config in datasets:
        target_dir = base_dir / "btms_budget_experiments/data" / config["name"]
        
        stats = prepare_experiment_data(
            source_dir=base_dir,
            target_dir=target_dir,
            model=config["model"],
            clustering_config=config["clustering"]
        )
        
        results[config["name"]] = {
            "description": config["description"],
            **stats
        }
    
    # 保存数据集信息
    datasets_info_path = base_dir / "btms_budget_experiments/data/datasets_info.json"
    with open(datasets_info_path, 'w') as f:
        json.dump(results, f, indent=2)
    
    print("\n" + "="*80)
    print("数据准备总结")
    print("="*80)
    
    for name, info in results.items():
        print(f"\n{name}:")
        print(f"  {info['description']}")
        print(f"  Bugs: {info['bugs']}, Clusters: {info['clusters']}, Reps: {info['representatives']}")
    
    print(f"\n数据集信息已保存到: {datasets_info_path}")
    print("\n✅ 所有数据准备完成!")

if __name__ == "__main__":
    main()
