#!/bin/bash
# 监控 qwen3coder30b gen 评估进度

LOG_FILE="/home/base/mengrui/MTSS/gen_evaluation_20260214.log"
RESULT_FILE="/home/base/mengrui/MTSS/evaluation_output/qwen3coder30b_FIXED_20260214/gen_batch_evaluation_results.json"

echo "========================================================================"
echo "Qwen3Coder-30B Gen 评估监控"
echo "========================================================================"
echo ""

# 检查进程状态
PID=$(pgrep -f 'run_gen_batch_evaluation.py.*20260106_030425')
if [ -n "$PID" ]; then
    echo "✓ 评估进程运行中 (PID: $PID)"
else
    echo "✗ 评估进程未运行"
fi

echo ""
echo "------------------------------------------------------------------------"
echo "最新进度:"
echo "------------------------------------------------------------------------"
tail -20 "$LOG_FILE" | grep -E "Progress:|PROGRESS REPORT|Fixed:|Failed:|Success Rate:"

echo ""
echo "------------------------------------------------------------------------"
echo "关键统计:"
echo "------------------------------------------------------------------------"

# 提取进度信息
PROGRESS=$(tail -100 "$LOG_FILE" | grep "Progress:" | tail -1)
if [ -n "$PROGRESS" ]; then
    echo "$PROGRESS"
fi

# 提取成功率
SUCCESS=$(tail -100 "$LOG_FILE" | grep "Success Rate:" | tail -1)
if [ -n "$SUCCESS" ]; then
    echo "$SUCCESS"
fi

# 检查结果文件
if [ -f "$RESULT_FILE" ]; then
    echo ""
    echo "当前结果文件:"
    FIXED=$(jq -r '.fixed_bugs // 0' "$RESULT_FILE")
    TOTAL=$(jq -r '.total_bugs // 0' "$RESULT_FILE")
    RATE=$(jq -r '.success_rate // 0' "$RESULT_FILE")
    echo "  修复: $FIXED / $TOTAL"
    echo "  成功率: $(echo "$RATE * 100" | bc)%"
fi

echo ""
echo "========================================================================" 
echo "命令:"
echo "  查看完整日志: tail -f $LOG_FILE"
echo "  持续监控: watch -n 5 $0"
echo "========================================================================"
