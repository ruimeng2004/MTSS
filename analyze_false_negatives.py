#!/usr/bin/env python3
"""
分析evaluation_output中4个目录的假阴性测试结果
假阴性 (False Negative): 补丁实际上修复了bug，但测试显示失败
"""

import json
import os
from collections import defaultdict
from pathlib import Path

def load_json(filepath):
    """加载JSON文件"""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"Error loading {filepath}: {e}")
        return None

def analyze_failures(result_data, model_name):
    """分析失败原因"""
    false_negative_indicators = {
        'patch_application_failed': [],  # 补丁应用失败 - 可能是路径/格式问题
        'test_timeout': [],              # 测试超时
        'compilation_failed': [],        # 编译失败
        'patch_not_found': [],          # 补丁文件找不到
        'checkout_failed': [],          # Checkout失败
        'other_failures': []            # 其他失败
    }
    
    # 根据不同的JSON结构处理
    if 'bug_results' in result_data:
        # qwen30b_edit 格式
        bugs = result_data['bug_results']
    elif 'results' in result_data:
        # gen格式
        bugs = list(result_data['results'].values())
    else:
        bugs = []
    
    total_failed = 0
    
    for bug in bugs:
        bug_slug = bug.get('bug_slug', 'Unknown')
        failure_reasons = bug.get('failure_reasons', [])
        successful_attempt = bug.get('successful_attempt')
        
        # 失败的bug
        if successful_attempt is None and failure_reasons:
            total_failed += 1
            
            for reason in failure_reasons:
                reason_lower = reason.lower()
                
                # 分类失败原因
                if 'patch' in reason_lower and ('apply' in reason_lower or 'failed' in reason_lower):
                    false_negative_indicators['patch_application_failed'].append({
                        'bug': bug_slug,
                        'reason': reason
                    })
                elif 'timeout' in reason_lower:
                    false_negative_indicators['test_timeout'].append({
                        'bug': bug_slug,
                        'reason': reason
                    })
                elif 'compilation' in reason_lower or 'compile' in reason_lower:
                    false_negative_indicators['compilation_failed'].append({
                        'bug': bug_slug,
                        'reason': reason
                    })
                elif 'not found' in reason_lower or 'no such file' in reason_lower:
                    false_negative_indicators['patch_not_found'].append({
                        'bug': bug_slug,
                        'reason': reason
                    })
                elif 'checkout' in reason_lower:
                    false_negative_indicators['checkout_failed'].append({
                        'bug': bug_slug,
                        'reason': reason
                    })
                else:
                    false_negative_indicators['other_failures'].append({
                        'bug': bug_slug,
                        'reason': reason
                    })
    
    return false_negative_indicators, total_failed

def main():
    eval_output = Path("/home/base/mengrui/MTSS/evaluation_output")
    
    # 4个目录的配置
    configs = [
        {
            'name': 'qwen30b_edit',
            'path': eval_output / 'qwen30b_edit' / 'parallel_evaluation_results.json'
        },
        {
            'name': 'qwen30b_gen',
            'path': eval_output / 'qwen30b_gen' / 'gen_batch_evaluation_results.json'
        },
        {
            'name': 'qwencoder_edit',
            'path': eval_output / 'qwencoder_edit' / 'edit_batch_evaluation_results.json'
        },
        {
            'name': 'qwencoder_gen',
            'path': eval_output / 'qwencoder_gen' / 'gen_batch_evaluation_results.json'
        }
    ]
    
    print("=" * 80)
    print("假阴性分析报告 - False Negative Analysis Report")
    print("=" * 80)
    print()
    
    all_results = {}
    
    for config in configs:
        model_name = config['name']
        json_path = config['path']
        
        print(f"\n{'='*80}")
        print(f"模型: {model_name}")
        print(f"文件: {json_path}")
        print(f"{'='*80}")
        
        data = load_json(json_path)
        if not data:
            continue
        
        # 打印基本统计
        if 'statistics' in data:
            stats = data['statistics']
            print(f"\n基本统计:")
            print(f"  总Bug数: {stats.get('total_bugs', 'N/A')}")
            print(f"  成功修复: {stats.get('fixed_bugs', 'N/A')}")
            print(f"  修复失败: {stats.get('failed_bugs', 'N/A')}")
            print(f"  成功率: {stats.get('success_rate', 'N/A'):.2%}")
        else:
            print(f"\n基本统计:")
            print(f"  总Bug数: {data.get('total_bugs', 'N/A')}")
            print(f"  成功修复: {data.get('fixed_bugs', 'N/A')}")
            print(f"  修复失败: {data.get('failed_bugs', 'N/A')}")
            print(f"  成功率: {data.get('success_rate', 'N/A'):.2%}")
        
        # 分析失败原因
        indicators, total_failed = analyze_failures(data, model_name)
        all_results[model_name] = indicators
        
        print(f"\n失败原因分类 (总计: {total_failed}):")
        for category, failures in indicators.items():
            if failures:
                print(f"\n  【{category}】: {len(failures)} 个")
                for i, item in enumerate(failures[:5], 1):  # 只显示前5个
                    print(f"    {i}. {item['bug']}: {item['reason'][:100]}")
                if len(failures) > 5:
                    print(f"    ... 还有 {len(failures) - 5} 个")
    
    # 生成总结报告
    print(f"\n\n{'='*80}")
    print("假阴性问题总结与解决方案")
    print(f"{'='*80}\n")
    
    # 统计各类问题
    all_categories = defaultdict(int)
    for model, indicators in all_results.items():
        for category, failures in indicators.items():
            all_categories[category] += len(failures)
    
    print("跨模型失败原因统计:")
    for category, count in sorted(all_categories.items(), key=lambda x: x[1], reverse=True):
        if count > 0:
            print(f"  {category}: {count} 次")
    
    print("\n\n【解决方案建议】\n")
    
    solutions = {
        'patch_application_failed': """
1. 补丁应用失败 (Patch Application Failed)
   - 问题: 补丁格式不正确，路径不匹配，或diff格式问题
   - 解决方案:
     a) 自动检测和调整-p参数 (git apply -p0, -p1, -p2等)
     b) 标准化补丁路径格式
     c) 使用更鲁棒的补丁应用方法 (尝试多种应用策略)
     d) 在应用前验证补丁格式和路径
        """,
        
        'patch_not_found': """
2. 补丁文件未找到 (Patch Not Found)
   - 问题: 文件路径错误或文件未生成
   - 解决方案:
     a) 检查patch生成逻辑，确保文件正确保存
     b) 使用绝对路径而不是相对路径
     c) 添加文件存在性验证
     d) 在评估前验证所有必需文件
        """,
        
        'checkout_failed': """
3. Checkout失败 (Checkout Failed)
   - 问题: 目录不为空，git状态异常
   - 解决方案:
     a) 在checkout前清理工作目录
     b) 使用force checkout选项
     c) 实现重试机制
     d) 检查并修复git仓库状态
        """,
        
        'test_timeout': """
4. 测试超时 (Test Timeout)
   - 问题: 测试执行时间过长
   - 解决方案:
     a) 增加超时时间限制
     b) 优化测试执行策略
     c) 并行执行测试
     d) 识别并跳过已知慢速测试
        """,
        
        'compilation_failed': """
5. 编译失败 (Compilation Failed)
   - 问题: 补丁引入语法错误或依赖问题
   - 解决方案:
     a) 在生成补丁时进行语法检查
     b) 改进代码生成模型的上下文
     c) 添加编译前验证步骤
     d) 使用更保守的代码修改策略
        """
    }
    
    for category, count in sorted(all_categories.items(), key=lambda x: x[1], reverse=True):
        if count > 0 and category in solutions:
            print(solutions[category])
    
    print("""
【通用改进建议】

1. 实现智能重试机制
   - 对于临时性失败（如checkout失败），自动重试
   - 对于补丁应用失败，尝试不同的-p参数

2. 改进补丁格式处理
   - 自动检测和修复路径问题
   - 支持多种补丁格式 (unified diff, context diff等)

3. 加强验证流程
   - 在评估前验证环境配置
   - 检查所有必需文件是否存在
   - 验证git仓库状态

4. 优化错误处理
   - 提供更详细的错误信息
   - 区分真正的失败和可恢复的错误
   - 记录完整的调试信息

5. 实现增量评估
   - 支持从失败点继续
   - 保存中间状态
   - 允许单独重新评估失败的用例

6. 改进日志和监控
   - 实时监控评估进度
   - 记录详细的失败原因
   - 生成可操作的错误报告
""")

if __name__ == "__main__":
    main()
