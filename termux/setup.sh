#!/data/data/com.termux/files/usr/bin/bash
# Автоустановка Roampal Android Stack

set -e

PIP_BIN="python -m pip"
PIP_FLAGS="--prefer-binary"

echo "🚀 Roampal Android Setup"
echo "========================"

# Обновление пакетов
echo "📦 Обновление Termux..."
pkg update -y
pkg upgrade -y

# Установка базовых зависимостей
echo "📦 Установка зависимостей..."
pkg install -y \
    python \
    python-pip \
    python-numpy \
    rust \
    nodejs \
    git \
    wget \
    curl \
    proot-distro \
    openssl \
    clang \
    make \
    cmake

# OCR/runtime deps for PDF fallback (best-effort on constrained mirrors/devices)
echo "🔎 Установка OCR/graphics зависимостей (tesseract/poppler/pillow build deps)..."
if ! pkg install -y tesseract poppler libjpeg-turbo libpng zlib build-essential; then
    echo "⚠️ Не все OCR/graphics пакеты установились через pkg; продолжаю best-effort режимом."
fi

# Клонирование репозитория (если еще не склонирован)
if [ ! -d "$HOME/roampal-android" ]; then
    echo "📥 Клонирование репозитория..."
    cd "$HOME"
    git clone https://github.com/Wvwvwvwvwv/jubilant-computing-machine.git roampal-android
fi

# Try to ensure Python OCR extras even when Poetry path succeeds.
echo "🐍 OCR python extras (best-effort): pytesseract + pillow"
if ! $PIP_BIN install $PIP_FLAGS pytesseract==0.3.10 pillow==10.4.0; then
    echo "⚠️ OCR python extras install failed; CLI OCR path (tesseract/pdftoppm) will be used if available."
fi

cd "$HOME/roampal-android"

# Гарантируем права на запуск termux-скриптов
chmod +x "$HOME/roampal-android"/termux/*.sh 2>/dev/null || true

# Самовосстановление Termux-файлов, если репозиторий локально старый/неполный
mkdir -p \
    "$HOME/roampal-android/termux" \
    "$HOME/roampal-android/backend/core" \
    "$HOME/roampal-android/backend/sandbox" \
    "$HOME/roampal-android/backend/embeddings"

if [ ! -f "$HOME/roampal-android/termux/constraints-termux.txt" ]; then
    cat > "$HOME/roampal-android/termux/constraints-termux.txt" <<'EOF'
pydantic==1.10.21
EOF
fi

if [ ! -f "$HOME/roampal-android/backend/sandbox/requirements-termux.txt" ]; then
    cat > "$HOME/roampal-android/backend/sandbox/requirements-termux.txt" <<'EOF'
fastapi==0.109.0
uvicorn==0.27.0
pydantic==1.10.21
EOF
fi

if [ ! -f "$HOME/roampal-android/backend/embeddings/requirements-lite-termux.txt" ]; then
    cat > "$HOME/roampal-android/backend/embeddings/requirements-lite-termux.txt" <<'EOF'
fastapi==0.109.0
uvicorn==0.27.0
pydantic==1.10.21
EOF
fi

# Самовосстановление старых шаблонов: numpy ставим только через pkg (python-numpy),
# т.к. pip на Python 3.13 в Termux часто уходит в source build и падает.
sed -i '/^numpy==/d' "$HOME/roampal-android/backend/embeddings/requirements-lite-termux.txt" 2>/dev/null || true

# Установка KoboldCpp
echo "🤖 Установка KoboldCpp..."
if [ ! -d "$HOME/koboldcpp" ]; then
    cd "$HOME"
    git clone https://github.com/LostRuins/koboldcpp.git
    cd koboldcpp
    make LLAMA_PORTABLE=1
fi

# Установка Termux Sandbox
echo "📦 Установка Termux Sandbox..."
if [ ! -d "$HOME/termux-sandbox" ]; then
    cd "$HOME"
    git clone https://github.com/788009/termux-sandbox.git
fi

# Установка Debian в proot-distro
echo "🐧 Установка Debian..."
if [ ! -d "$PREFIX/var/lib/proot-distro/installed-rootfs/debian" ]; then
    proot-distro install debian
fi

# Настройка Debian окружения
echo "⚙️ Настройка Debian..."
proot-distro login debian -- bash -c "
    apt update
    apt install -y python3 python3-pip python3-venv
    exit
"

# Создание директорий
echo "📁 Создание директорий..."
mkdir -p "$HOME/roampal-android/models"
mkdir -p "$HOME/roampal-android/data/memory"
mkdir -p "$HOME/roampal-android/data/books"
mkdir -p "$HOME/roampal-android/data/sandbox"

# Установка Python зависимостей для backend
echo "🐍 Установка Python зависимостей..."
CONSTRAINTS="$HOME/roampal-android/termux/constraints-termux.txt"

# Некоторые rust/maturin пакеты на Android требуют явный API level.
if [ -z "${ANDROID_API_LEVEL:-}" ]; then
    ANDROID_API_LEVEL="$(getprop ro.build.version.sdk 2>/dev/null || echo 24)"
    export ANDROID_API_LEVEL
    echo "ℹ️ ANDROID_API_LEVEL set to: $ANDROID_API_LEVEL"
fi

echo "📦 Установка Poetry..."
$PIP_BIN install $PIP_FLAGS poetry==1.8.3
poetry config virtualenvs.create false

cd "$HOME/roampal-android"
# Для Termux (особенно Python 3.13) ставим только core runtime без heavy memory-группы,
# иначе возможны падения сборки rust/maturin зависимостей (hf-xet и др.).
if ! poetry install --only main --without memory --no-interaction --no-ansi; then
    echo "⚠️ Poetry install failed (likely pydantic-core/rust build on Termux)."
    echo "↪️ Fallback: installing core runtime via pip with Termux constraints (pydantic v1)."
    echo "↪️ numpy is provided by Termux package (python-numpy), not pip (avoids source-build failures)."
    $PIP_BIN install $PIP_FLAGS -c "$CONSTRAINTS" \
        fastapi==0.109.0 \
        uvicorn==0.27.0 \
        pydantic==1.10.21 \
        httpx==0.26.0 \
        python-multipart==0.0.6 \
        aiofiles==23.2.1 \
        pypdf==4.2.0

    echo "↪️ Optional OCR python deps (pytesseract/pillow): install best-effort only."
    if ! $PIP_BIN install $PIP_FLAGS pytesseract==0.3.10 pillow==10.4.0; then
        echo "⚠️ Optional OCR python deps failed to install; CLI tesseract path will be used if available."
    fi
fi

if [ -n "${ROAMPAL_INSTALL_MEMORY_GROUP:-}" ]; then
    echo "ℹ️ ROAMPAL_INSTALL_MEMORY_GROUP=1: пытаюсь установить memory group..."
    if ! poetry install --only memory --no-interaction --no-ansi; then
        echo "⚠️ Memory group install failed on this Termux environment; continuing with fallback in-memory store."
    fi
fi

cd "$HOME/roampal-android/backend/sandbox"
$PIP_BIN install $PIP_FLAGS -c "$CONSTRAINTS" -r requirements-termux.txt

cd "$HOME/roampal-android/backend/embeddings"
PY_VER=$(python - <<'PYV'
import sys
print(f"{sys.version_info.major}.{sys.version_info.minor}")
PYV
)

if [ "$PY_VER" = "3.13" ]; then
    echo "ℹ️ Python $PY_VER detected: skipping heavy embeddings deps, using lite Termux profile."
    $PIP_BIN install $PIP_FLAGS -c "$CONSTRAINTS" -r requirements-lite-termux.txt
elif ! $PIP_BIN install $PIP_FLAGS -c "$CONSTRAINTS" -r requirements.txt; then
    echo "⚠️ Full embeddings deps failed, installing lite Termux profile..."
    $PIP_BIN install $PIP_FLAGS -c "$CONSTRAINTS" -r requirements-lite-termux.txt
fi

# Проверка установленной версии pydantic
python - <<'CHECK'
import pydantic
v = getattr(pydantic, '__version__', 'unknown')
print(f"✅ pydantic version: {v}")
if not (v.startswith('1.10.') or v.startswith('2.')):
    raise SystemExit(f"❌ Unexpected pydantic version on Termux: {v}")
CHECK

# Установка Node.js зависимостей для frontend
echo "📦 Установка Node.js зависимостей..."
cd "$HOME/roampal-android/frontend"
npm install

# Скачивание рекомендуемой модели (опционально)
# В non-interactive режиме (например, curl | bash) пропускаем вопрос.
response="n"
if [ -t 0 ]; then
    echo "🤔 Скачать рекомендуемую модель? (y/n)"
    read -r response || response="n"
else
    echo "ℹ️ Non-interactive режим: скачивание модели пропущено (можно выполнить вручную позже)."
fi

case "$response" in
    [yY]|[yY][eE][sS])
        echo "📥 Скачивание L3-8B-Stheno-v3.2..."
        cd "$HOME/roampal-android/models"
        wget -c https://huggingface.co/bartowski/L3-8B-Stheno-v3.2-GGUF/resolve/main/L3-8B-Stheno-v3.2-Q4_K_M.gguf
        ;;
    *)
        echo "⏭️ Скачивание модели пропущено."
        ;;
esac

echo ""
echo "✅ Установка завершена!"
echo ""
echo "Для запуска:"
echo "  cd ~/roampal-android"
echo "  ./termux/start-services.sh"
echo ""
