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

# Клонирование репозитория (если еще не склонирован)
if [ ! -d "$HOME/roampal-android" ]; then
    echo "📥 Клонирование репозитория..."
    cd "$HOME"
    git clone https://github.com/Wvwvwvwvwv/jubilant-computing-machine.git roampal-android
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

if [ ! -f "$HOME/roampal-android/backend/core/requirements-termux.txt" ]; then
    cat > "$HOME/roampal-android/backend/core/requirements-termux.txt" <<'EOF'
fastapi==0.109.0
uvicorn==0.27.0
pydantic==1.10.21
httpx==0.26.0
python-multipart==0.0.6
aiofiles==23.2.1
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
sed -i '/^numpy==/d' "$HOME/roampal-android/backend/core/requirements-termux.txt" 2>/dev/null || true
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

# Защита от pydantic-core сборки на Termux
$PIP_BIN uninstall -y pydantic pydantic-core >/dev/null 2>&1 || true
$PIP_BIN install $PIP_FLAGS -c "$CONSTRAINTS" pydantic==1.10.21

cd "$HOME/roampal-android/backend/core"
$PIP_BIN install $PIP_FLAGS -c "$CONSTRAINTS" -r requirements-termux.txt

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
if not v.startswith('1.10.'):
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
