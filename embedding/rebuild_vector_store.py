"""
重建向量数据库：清空现有数据，从 vectors 文件夹重新加载
"""
import json
import shutil
import numpy as np
from pathlib import Path
from vector_store import VectorStore
import yaml


def main():
    # 加载配置
    config_path = Path(__file__).parent / 'config.yaml'
    with open(config_path, 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)
    
    embedding_config = config.get('embedding_config', {})
    vs_config = embedding_config.get('vector_store', {})
    
    vectors_dir = Path(__file__).parent / 'vectors'
    index_path = Path(vs_config.get('index_path', 'vector_index'))
    
    # 1. 删除现有的向量索引
    print(f"\n步骤 1: 清空现有向量索引...")
    if index_path.exists():
        print(f"  删除目录: {index_path}")
        shutil.rmtree(index_path)
        print("  ✓ 已删除")
    else:
        print("  目录不存在，跳过")
    
    # 2. 创建新的向量存储
    print(f"\n步骤 2: 创建新的向量存储...")
    vector_store = VectorStore(str(index_path), vs_config)
    print("  ✓ 向量存储已初始化")
    
    # 3. 从 vectors 文件夹加载所有嵌入
    print(f"\n步骤 3: 从 {vectors_dir} 加载嵌入...")
    
    if not vectors_dir.exists():
        print(f"  ❌ 错误: {vectors_dir} 不存在")
        return
    
    embedding_files = sorted(vectors_dir.glob('*_embeddings.json'))
    print(f"  找到 {len(embedding_files)} 个嵌入文件")
    
    # 收集所有向量
    all_vectors = []
    all_ids = []
    all_metadata = []
    
    successful = 0
    failed = 0
    
    for i, emb_file in enumerate(embedding_files, 1):
        try:
            with open(emb_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # 提取文件夹名称（去掉 _embeddings.json）
            folder_name = emb_file.stem.replace('_embeddings', '')
            
            # 处理每个文件的嵌入
            for file_data in data:
                if file_data.get('status') != 'success':
                    continue
                
                embedding = file_data.get('embedding')
                if not embedding or not isinstance(embedding, list):
                    continue
                
                vector_id = f"{folder_name}_{file_data['file_name'].replace('.txt', '')}"
                
                all_vectors.append(embedding)
                all_ids.append(vector_id)
                all_metadata.append({
                    'folder': folder_name,
                    'file_name': file_data['file_name'],
                    'tokens': file_data.get('tokens', 0)
                })
                successful += 1
            
            # 显示进度
            if i % 50 == 0 or i == len(embedding_files):
                print(f"  进度: {i}/{len(embedding_files)} 文件已处理...")
        
        except Exception as e:
            print(f"  ⚠ 警告: 处理 {emb_file.name} 失败: {e}")
            failed += 1
            continue
    
    print(f"\n  ✓ 成功加载 {successful} 个向量")
    if failed > 0:
        print(f"  ⚠ {failed} 个文件处理失败")
    
    # 4. 批量添加到向量存储
    if all_vectors:
        print(f"\n步骤 4: 批量添加 {len(all_vectors)} 个向量到存储...")
        
        # 转换为 numpy 数组
        vectors_array = np.array(all_vectors, dtype=np.float32)
        
        # 批量添加
        vector_store.add_vectors(vectors_array, all_ids, all_metadata)
        print("  ✓ 向量已添加")
        
        # 5. 构建索引
        print(f"\n步骤 5: 构建索引...")
        vector_store.build_index()
        print("  ✓ 索引已构建")
        
        # 6. 保存到磁盘
        print(f"\n步骤 6: 保存到磁盘...")
        vector_store.save()
        print("  ✓ 已保存")
        
        # 7. 显示统计信息
        print(f"\n{'='*60}")
        print("重建完成！")
        print(f"{'='*60}")
        print(f"总向量数: {len(all_vectors)}")
        print(f"向量维度: {len(all_vectors[0])}")
        print(f"索引类型: {vs_config.get('index_type', 'ivf_flat')}")
        print(f"索引路径: {index_path}")
        
        # 统计每个项目的向量数
        project_counts = {}
        for meta in all_metadata:
            folder = meta['folder']
            project = folder.split('_')[0]
            project_counts[project] = project_counts.get(project, 0) + 1
        
        print(f"\n按项目统计:")
        for project in sorted(project_counts.keys()):
            print(f"  {project}: {project_counts[project]} 个向量")
        
    else:
        print("\n  ❌ 没有找到有效的向量数据")


if __name__ == '__main__':
    main()
