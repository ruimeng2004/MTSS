#!/bin/bash
# 监控嵌入生成进度

LOG_FILE="/tmp/embedding_all.log"
INDEX_PATH="/home/base/APR/D4C/embedding/vector_index"

echo "========================================"
echo "嵌入向量生成进度监控"
echo "========================================"
echo ""

# 检查进程是否运行
PID=$(pgrep -f "embedder.py --categories")
if [ -z "$PID" ]; then
    echo "❌ 嵌入生成进程未运行"
    echo ""
else
    echo "✅ 进程运行中 (PID: $PID)"
    echo ""
fi

# 统计处理的文件夹数量
if [ -f "$LOG_FILE" ]; then
    PROCESSED=$(grep -c "^Processed" "$LOG_FILE")
    echo "📁 已处理文件夹: $PROCESSED"
    
    # 最近处理的10个
    echo ""
    echo "最近处理:"
    grep "^Processed" "$LOG_FILE" | tail -5
fi

echo ""
echo "----------------------------------------"

# 向量存储统计
if [ -f "$INDEX_PATH/metadata.json" ]; then
    VECTOR_COUNT=$(python3 -c "import json; print(json.load(open('$INDEX_PATH/metadata.json'))['num_vectors'])" 2>/dev/null)
    echo "📊 向量数据库: $VECTOR_COUNT 个向量"
    
    # JSON 文件数量
    JSON_COUNT=$(ls -1 /home/base/APR/D4C/embedding/vectors/*_embeddings.json 2>/dev/null | wc -l)
    echo "📄 JSON 文件: $JSON_COUNT 个"
fi

echo ""
echo "----------------------------------------"
echo ""
echo "实时日志 (Ctrl+C 退出):"
echo ""

# 实时跟踪日志
tail -f "$LOG_FILE" | grep --line-buffered -E "Processed|Added|Vector store|Done"
