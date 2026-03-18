#!/data/data/com.termux/files/usr/bin/bash
# Запуск KoboldCpp

set -euo pipefail

MODEL_PATH="${MODEL_PATH:-$HOME/roampal-android/models}"
KOBOLD_PATH="${KOBOLD_PATH:-$HOME/koboldcpp}"
KOBOLD_PORT="${KOBOLD_PORT:-5001}"
KOBOLD_CONTEXTSIZE="${KOBOLD_CONTEXTSIZE:-4096}"
KOBOLD_THREADS="${KOBOLD_THREADS:-6}"
KOBOLD_BLASTHREADS="${KOBOLD_BLASTHREADS:-4}"
KOBOLD_USE_MLOCK="${KOBOLD_USE_MLOCK:-0}"
KOBOLD_EXTRA_ARGS="${KOBOLD_EXTRA_ARGS:-}"

# Поиск первой доступной модели
MODEL=$(find "$MODEL_PATH" -name "*.gguf" | head -n 1)

if [ -z "$MODEL" ]; then
    echo "❌ Модель не найдена в $MODEL_PATH"
    echo "Скачайте модель:"
    echo "  cd $MODEL_PATH"
    echo "  wget https://huggingface.co/bartowski/L3-8B-Stheno-v3.2-GGUF/resolve/main/L3-8B-Stheno-v3.2-Q4_K_M.gguf"
    exit 1
fi

if [ ! -d "$KOBOLD_PATH" ]; then
    echo "❌ Директория KoboldCpp не найдена: $KOBOLD_PATH"
    exit 1
fi

EXTRA_FLAGS=()
if [ "$KOBOLD_USE_MLOCK" = "1" ]; then
    EXTRA_FLAGS+=(--usemlock)
else
    echo "ℹ️  --usemlock отключён по умолчанию: на Termux он часто приводит к OOM/failed to mlock для больших GGUF."
fi

if [ -n "$KOBOLD_EXTRA_ARGS" ]; then
    # shellcheck disable=SC2206
    EXTRA_FLAGS+=( $KOBOLD_EXTRA_ARGS )
fi

echo "🤖 Запуск KoboldCpp с моделью: $(basename "$MODEL")"
echo "📍 Порт: $KOBOLD_PORT"
echo "🧠 Context: $KOBOLD_CONTEXTSIZE"
echo "🧵 Threads: $KOBOLD_THREADS / BLAS: $KOBOLD_BLASTHREADS"
echo "🔒 Mlock: $KOBOLD_USE_MLOCK"
echo ""

cd "$KOBOLD_PATH"

exec python koboldcpp.py \
    --model "$MODEL" \
    --port "$KOBOLD_PORT" \
    --contextsize "$KOBOLD_CONTEXTSIZE" \
    --threads "$KOBOLD_THREADS" \
    --blasthreads "$KOBOLD_BLASTHREADS" \
    --noblas \
    "${EXTRA_FLAGS[@]}"
