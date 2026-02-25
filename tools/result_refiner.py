import pandas as pd
import os
def collect_successful_slugs(csv_file_path):
    """
    收集 reward 为 True 的 slug。如果某个 slug 在两次尝试中有一次 reward 为 True，则标记为 True。
    
    :param csv_file_path: CSV 文件路径
    :return: 包含 reward 为 True 的 slug 的集合
    """
    # 读取 CSV 文件
    df = pd.read_csv(csv_file_path, sep=',', encoding='utf-8', engine='python')
    
    # 按 slug 分组，检查是否有任意一次 reward 为 True
    successful_slugs = df.groupby('slug')['reward'].any()
    
    # 筛选出 reward 为 True 的 slug
    successful_slugs = set(successful_slugs[successful_slugs].index)
    
    return successful_slugs

# 使用示例
csv_file_path = '/home/lith/APR_formulation/D4C/D4C/result/defects4j/eval_full_1shot_deepseek-chat_2try_temp=1.0.csv'
successful_slugs = collect_successful_slugs(csv_file_path)

log_dir = '/home/lith/APR_formulation/D4C/D4C/log'

with open(os.path.join(log_dir, 'refined_result.txt'), 'w') as f:
    for slug in successful_slugs:
        f.write(slug+'\n')