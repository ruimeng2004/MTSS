"""
Interactive command-line tool to query vector store
Can be run in VSCode integrated terminal
"""
import sys
import argparse
import numpy as np
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent))

# Simple table formatter (no external dependency)
def simple_table(data, headers):
    if not data:
        return ""
    
    # Calculate column widths
    col_widths = [len(h) for h in headers]
    for row in data:
        for i, cell in enumerate(row):
            col_widths[i] = max(col_widths[i], len(str(cell)))
    
    # Format table
    sep = "+" + "+".join("-" * (w + 2) for w in col_widths) + "+"
    header_row = "|" + "|".join(f" {h:^{col_widths[i]}} " for i, h in enumerate(headers)) + "|"
    
    lines = [sep, header_row, sep]
    for row in data:
        row_str = "|" + "|".join(f" {str(cell):<{col_widths[i]}} " for i, cell in enumerate(row)) + "|"
        lines.append(row_str)
    lines.append(sep)
    
    return "\n".join(lines)

from embedding.vector_store import VectorStore


def list_all_vectors(vs):
    """List all vectors in the store"""
    all_ids = vs.get_all_ids()
    
    table_data = []
    for vec_id in all_ids:
        meta = vs.get_metadata(vec_id)
        table_data.append([
            vec_id,
            meta.get('folder', 'N/A'),
            meta.get('file_name', 'N/A'),
            meta.get('tokens', 'N/A'),
        ])
    
    headers = ['Vector ID', 'Folder', 'File', 'Tokens']
    print(f"\n总计 {len(all_ids)} 个向量:\n")
    print(simple_table(table_data, headers))


def search_by_id(vs, vector_id, k=10):
    """Search similar vectors by ID"""
    vec = vs.get_vector(vector_id)
    if vec is None:
        print(f"❌ 向量 '{vector_id}' 不存在")
        return
    
    meta = vs.get_metadata(vector_id)
    print(f"\n查询向量: {vector_id}")
    print(f"  文件夹: {meta.get('folder')}")
    print(f"  文件: {meta.get('file_name')}")
    print(f"\n最相似的 {k} 个向量:\n")
    
    results = vs.search(vec, k=k)
    
    table_data = []
    for i, (vid, dist) in enumerate(results, 1):
        m = vs.get_metadata(vid)
        table_data.append([
            i,
            vid,
            f"{dist:.4f}",
            m.get('folder', 'N/A'),
            m.get('file_name', 'N/A'),
        ])
    
    headers = ['排名', 'Vector ID', '距离', 'Folder', 'File']
    print(simple_table(table_data, headers))


def search_by_folder(vs, folder_name, k=5):
    """Find similar vectors within a folder"""
    all_ids = [vid for vid in vs.get_all_ids() 
               if vs.get_metadata(vid).get('folder') == folder_name]
    
    if not all_ids:
        print(f"❌ 文件夹 '{folder_name}' 中没有向量")
        return
    
    print(f"\n文件夹 '{folder_name}' 中有 {len(all_ids)} 个向量")
    print(f"\n显示前 {min(k, len(all_ids))} 个:\n")
    
    table_data = []
    for vid in all_ids[:k]:
        meta = vs.get_metadata(vid)
        table_data.append([
            vid,
            meta.get('file_name', 'N/A'),
            meta.get('tokens', 'N/A'),
        ])
    
    headers = ['Vector ID', 'File', 'Tokens']
    print(simple_table(table_data, headers))


def show_stats(vs):
    """Show vector store statistics"""
    print(f"\n向量存储统计:\n")
    print(f"  总向量数: {len(vs)}")
    print(f"  向量维度: {vs.dimension}")
    print(f"  索引类型: {vs.index_type}")
    print(f"  距离度量: {vs.metric}")
    print(f"  索引路径: {vs.index_path}")
    
    # Folder distribution
    folders = {}
    for vid in vs.get_all_ids():
        folder = vs.get_metadata(vid).get('folder', 'Unknown')
        folders[folder] = folders.get(folder, 0) + 1
    
    print(f"\n文件夹分布:\n")
    table_data = [[folder, count] for folder, count in sorted(folders.items())]
    print(simple_table(table_data, headers=['Folder', 'Count']))


def interactive_mode(vs):
    """Interactive query mode"""
    print("\n" + "=" * 60)
    print("向量存储交互查询工具")
    print("=" * 60)
    print("\n命令:")
    print("  list              - 列出所有向量")
    print("  search <id> [k]   - 搜索相似向量")
    print("  folder <name> [k] - 查看文件夹中的向量")
    print("  stats             - 显示统计信息")
    print("  quit / exit       - 退出")
    print("\n" + "=" * 60 + "\n")
    
    while True:
        try:
            cmd = input(">>> ").strip()
            
            if not cmd:
                continue
            
            if cmd in ['quit', 'exit', 'q']:
                print("再见!")
                break
            
            parts = cmd.split()
            action = parts[0].lower()
            
            if action == 'list':
                list_all_vectors(vs)
            
            elif action == 'search':
                if len(parts) < 2:
                    print("用法: search <vector_id> [k]")
                    continue
                vector_id = parts[1]
                k = int(parts[2]) if len(parts) > 2 else 10
                search_by_id(vs, vector_id, k)
            
            elif action == 'folder':
                if len(parts) < 2:
                    print("用法: folder <folder_name> [k]")
                    continue
                folder_name = parts[1]
                k = int(parts[2]) if len(parts) > 2 else 5
                search_by_folder(vs, folder_name, k)
            
            elif action == 'stats':
                show_stats(vs)
            
            else:
                print(f"未知命令: {action}")
                print("输入 'help' 查看可用命令")
        
        except KeyboardInterrupt:
            print("\n再见!")
            break
        except Exception as e:
            print(f"错误: {e}")


def main():
    parser = argparse.ArgumentParser(description='查询向量存储')
    parser.add_argument('--index-path', default='/home/base/APR/D4C/embedding/vector_index',
                       help='向量索引路径')
    parser.add_argument('--list', action='store_true', help='列出所有向量')
    parser.add_argument('--search', type=str, help='搜索相似向量 (提供 vector_id)')
    parser.add_argument('--folder', type=str, help='查看文件夹中的向量')
    parser.add_argument('--stats', action='store_true', help='显示统计信息')
    parser.add_argument('-k', type=int, default=10, help='返回结果数量')
    parser.add_argument('--interactive', '-i', action='store_true', help='交互模式')
    
    args = parser.parse_args()
    
    # Load vector store
    config = {
        'index_type': 'ivf_flat',
        'metric': 'l2',
        'nprobe': 10,
    }
    
    if not Path(args.index_path).exists():
        print(f"❌ 向量存储不存在: {args.index_path}")
        print("请先运行 embedder.py 生成向量")
        return
    
    print(f"加载向量存储: {args.index_path}")
    vs = VectorStore(args.index_path, config)
    
    if len(vs) == 0:
        print("❌ 向量存储为空")
        return
    
    print(f"✓ 已加载 {len(vs)} 个向量")
    
    # Execute commands
    if args.interactive:
        interactive_mode(vs)
    elif args.list:
        list_all_vectors(vs)
    elif args.search:
        search_by_id(vs, args.search, args.k)
    elif args.folder:
        search_by_folder(vs, args.folder, args.k)
    elif args.stats:
        show_stats(vs)
    else:
        # Default: show stats and enter interactive mode
        show_stats(vs)
        print("\n提示: 使用 -i 进入交互模式")


if __name__ == '__main__':
    main()
