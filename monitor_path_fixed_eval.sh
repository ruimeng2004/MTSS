#!/bin/bash
# 监控路径修复后的评估进度

log_file="/home/base/mengrui/MTSS/gen_eval_path_fixed.log"
result_file="/home/base/mengrui/MTSS/evaluation_output/qwen30b_gen_PATH_FIXED/gen_batch_evaluation_results.json"

echo "========================================"
echo "路径修复后的评估监控"
echo "========================================"
echo ""

# 检查进程
if pgrep -f "run_gen_batch_evaluation.py.*PATH_FIXED" > /dev/null; then
    echo "✓ 评估进程运行中"
else
    echo "✗ 评估进程未运行"
fi

echo ""
echo "最新日志 (最后20行):"
echo "----------------------------------------"
tail -20 "$log_file" 2>/dev/null || echo "日志文件不存在"

echo ""
echo "========================================"
echo "进度统计:"
echo "========================================"

# 提取进度信息
if [ -f "$log_file" ]; then
    # 获取最新进度
    progress=$(grep "Progress:" "$log_file" | tail -1)
    if [ -n "$progress" ]; then
        echo "$progress"
    fi
    
    # 统计成功/失败
    fixed_count=$(grep -c "✓.*fixed" "$log_file")
    failed_count=$(grep -c "✗.*failed" "$log_file")
    total=$((fixed_count + failed_count))
    
    if [ $total -gt 0 ]; then
        success_rate=$(echo "scale=1; $fixed_count * 100 / $total" | bc)
        echo "已完成: $total 个"
        echo "  成功: $fixed_count"
        echo "  失败: $failed_count"
        echo "  当前成功率: $success_rate%"
    fi
fi

# 检查结果文件
if [ -f "$result_file" ]; then
    echo ""
    echo "========================================"
    echo "最终结果 (from JSON):"
    echo "========================================"
    python3 << EOF
import json
try:
    with open('$result_file') as f:
        data = json.load(f)
    print(f"总bug数: {data['total_bugs']}")
    print(f"成功修复: {data['fixed_bugs']}")
    print(f"失败数: {data['failed_bugs']}")
    print(f"成功率: {data['success_rate']*100:.1f}%")
except:
    print("结果文件格式错误")
EOF
fi

echo ""
echo "========================================"
echo "刷新时间: $(date '+%Y-%m-%d %H:%M:%S')"
echo "========================================"
