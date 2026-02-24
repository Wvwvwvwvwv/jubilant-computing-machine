#!/data/data/com.termux/files/usr/bin/bash
# Запуск KoboldCpp

MODEL_PATH="$HOME/roampal-android/models"
KOBOLD_PATH="$HOME/koboldcpp"

# Поиск первой доступной модели
MODEL=$(find "$MODEL_PATH" -name "*.gguf" | head -n 1)

if [ -z "$MODEL" ]; then
    echo "❌ Модель не найдена в $MODEL_PATH"
    echo "Скачайте модель:"
    echo "  cd $MODEL_PATH"
    echo "  wget https://huggingface.co/bartowski/L3-8B-Stheno-v3.2-GGUF/resolve/main/L3-8B-Stheno-v3.2-Q4_K_M.gguf"
    exit 1
fi

echo "🤖 Запуск KoboldCpp с моделью: $(basename $MODEL)"
echo "📍 Порт: 5001"
echo ""

cd "$KOBOLD_PATH"

# Запуск с оптимальными параметрами для Snapdragon 8 Elite
python koboldcpp.py \
    --model "$MODEL" \
    --port 5001 \
    --contextsize 8192 \
    --threads 8 \
    --blasthreads 8 \
    --usemlock \
    --noblas
