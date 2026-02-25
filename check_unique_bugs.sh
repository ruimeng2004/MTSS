#!/bin/bash
# 统计唯一的bug数量

echo "统计唯一bug..."
echo ""

# 提取所有成功的bug（去重）
FIXED_BUGS=$(grep "✓.*fixed" parallel_evaluation.log | awk '{print $3}' | sort -u)
FIXED_COUNT=$(echo "$FIXED_BUGS" | grep -v "^$" | wc -l | tr -d ' ')

# 提取所有失败的bug（去重）
FAILED_BUGS=$(grep "✗.*failed" parallel_evaluation.log | awk '{print $3}' | sort -u)
FAILED_COUNT=$(echo "$FAILED_BUGS" | grep -v "^$" | wc -l | tr -d ' ')

TOTAL=$((FIXED_COUNT + FAILED_COUNT))

echo "唯一bug统计："
echo "  成功修复: $FIXED_COUNT 个"
echo "  修复失败: $FAILED_COUNT 个"
echo "  总计: $TOTAL 个"
echo ""

if [ $TOTAL -gt 0 ]; then
    SUCCESS_RATE=$(echo "scale=1; $FIXED_COUNT * 100 / $TOTAL" | bc)
    PROGRESS=$(echo "scale=1; $TOTAL * 100 / 698" | bc)
    echo "  成功率: ${SUCCESS_RATE}%"
    echo "  进度: ${PROGRESS}%"
fi
