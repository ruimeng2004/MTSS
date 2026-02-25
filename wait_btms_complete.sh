#!/bin/bash
# 等待BTMS评测完成并显示最终结果

LOG_FILE="/home/base/mengrui/MTSS/btms_routing_baseline3-size-adjusted_20260215_043340.log"
RESULT_FILE="/home/base/mengrui/MTSS/evaluation_output/btms_routing_baseline3-size-adjusted/btms_routing_results.json"

echo "等待BTMS路由评测完成..."
echo ""

while true; do
    if pgrep -f "run_btms_routing_eval.py" > /dev/null; then
        # 进程还在运行
        python3 -c "
log = open('$LOG_FILE').read()
success = log.count(': ✓')
fail = log.count(': ✗')
total = success + fail
print(f'\r进度: {total}/698  成功: {success}  失败: {fail}  成功率: {success/total*100:.2f}%' if total > 0 else '\r等待中...', end='', flush=True)
"
        sleep 5
    else
        echo -e "\n\n评测已完成！"
        break
    fi
done

echo ""
echo "=========================================="
echo "BTMS路由评测最终结果"
echo "=========================================="

if [ -f "$RESULT_FILE" ]; then
    python3 -c "
import json
with open('$RESULT_FILE', 'r') as f:
    data = json.load(f)
    print(f\"总bugs:      {data['total_bugs']}\")
    print(f\"修复成功:    {data['fixed_bugs']}\")
    print(f\"失败:        {data['failed_bugs']}\")
    print(f\"成功率:      {data['success_rate']*100:.2f}%\")
    print(f\"Edit成功:    {data['edit_success']}\")
    print(f\"Gen成功:     {data['gen_success']}\")
    print(f\"总耗时:      {data['total_time']:.2f}秒\")
    print(f\"平均耗时:    {data['average_time_per_bug']:.2f}秒/bug\")
"
else
    echo "结果文件未找到: $RESULT_FILE"
fi

echo "=========================================="
