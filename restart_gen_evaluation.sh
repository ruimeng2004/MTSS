#!/bin/bash
# 停止当前评测并用合理配置重新开始

echo "=== 停止当前评测 ==="
kill 73874
sleep 5

echo ""
echo "=== 清理旧的workspace ==="
# 保留已经checkout成功的目录，只清理不完整的
echo "保留已checkout的目录，清理进行中的checkout..."

echo ""
echo "=== 启动新的评测 ==="
echo "配置："
echo "  - Workers: 20个（从100减少到20）"
echo "  - Timeout: 600秒（10分钟，已修改代码为60分钟）"
echo "  - 预计时间: 2-3小时"

nohup python run_gen_batch_evaluation.py \
  --input-dir /Users/mengrui/Desktop/MTSS/ppl/result/20260106_113852 \
  --workers 20 \
  --timeout 240 \
  --d4j-path /Users/mengrui/Desktop/D4J/defects4j \
  --workspace ./parallel_workspace \
  > gen_batch_evaluation_restart.log 2>&1 &

echo "新进程ID: $!"
echo ""
echo "监控命令: tail -f gen_batch_evaluation_restart.log"
