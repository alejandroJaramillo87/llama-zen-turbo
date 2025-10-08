#!/bin/bash
set -e

# Default values (can be overridden by environment variables)
SERVER_PORT=${SERVER_PORT:-8001}
MODEL_PATH=${MODEL_PATH:-"/app/models/gguf/Qwen3-Coder-30B-A3B-Instruct-GGUF/Qwen3-Coder-30B-A3B-Instruct-IQ4_XS.gguf"}
SERVER_HOST=${SERVER_HOST:-"0.0.0.0"}
N_GPU_LAYERS=${N_GPU_LAYERS:-0}
CTX_SIZE=${CTX_SIZE:-32768}
BATCH_SIZE=${BATCH_SIZE:-2048}
UBATCH_SIZE=${UBATCH_SIZE:-2048}
THREADS=${THREADS:-12}
THREADS_BATCH=${THREADS_BATCH:-12}
THREADS_HTTP=${THREADS_HTTP:-2}

echo "=== Starting llama.cpp CPU Server with zen5_optimizer ==="
echo "  Port: $SERVER_PORT"
echo "  Model: $MODEL_PATH"
echo "  Threads: $THREADS"

# Verify model file exists
if [[ ! -f "$MODEL_PATH" ]]; then
    echo "ERROR: Model file not found: $MODEL_PATH"
    echo "Please ensure the model file exists at the specified path."
    exit 1
fi

# Enable zen5_optimizer (Phase 1A: Hugepage support)
# The optimizer will automatically use huge pages for models > 1GB
# Set DISABLE_HUGEPAGES=1 to disable for baseline testing
if [[ "${DISABLE_HUGEPAGES}" != "1" ]]; then
    export LD_PRELOAD=/app/libzen5_optimizer.so
    echo "zen5_optimizer loaded (Phase 1A: Hugepages)"
    echo "  LD_PRELOAD set to: $LD_PRELOAD"
    echo "  MAP_HUGETLB enabled for allocations >= 1GB"
else
    echo "zen5_optimizer DISABLED (baseline mode)"
    echo "  Running without hugepage optimization for A/B testing"
fi

# Memory status before loading
echo "Memory status before model load:"
grep -E "MemTotal|MemFree|AnonHugePages|HugePages_Total|HugePages_Free|HugePages_Rsvd" /proc/meminfo | sed 's/^/  /'

# Execute the server with all parameters
# Configuration validated through benchmarking (September 2025):
# - Batch size 2048 is optimal (tested 512, 2048, 4096)
# - --cont-batching improves request handling
# - --mlock prevents swapping for consistent performance
exec ./server \
    --model "$MODEL_PATH" \
    --host "$SERVER_HOST" \
    --port "$SERVER_PORT" \
    --n-gpu-layers "$N_GPU_LAYERS" \
    --ctx-size "$CTX_SIZE" \
    --batch-size "$BATCH_SIZE" \
    --ubatch-size "$UBATCH_SIZE" \
    --threads "$THREADS" \
    --threads-batch "$THREADS_BATCH" \
    --cont-batching \
    --metrics \
    --no-warmup \
    --mlock \
    --threads-http "$THREADS_HTTP"
