#!/data/data/com.termux/files/usr/bin/bash
# Автоустановка Roampal Android Stack

set -e

PIP_BIN="python -m pip"
PIP_FLAGS="--prefer-binary --only-binary=:all:"

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

# Самовосстановление deploy.sh для старых/неполных клонов.
# Частый кейс: локальный репозиторий был создан до добавления termux/deploy.sh.
if [ ! -f "$HOME/roampal-android/termux/deploy.sh" ]; then
    echo "ℹ️ termux/deploy.sh не найден, восстанавливаю из GitHub..."
    BRANCH=$(git -C "$HOME/roampal-android" rev-parse --abbrev-ref HEAD 2>/dev/null || echo "work")
    RAW_URL="https://raw.githubusercontent.com/Wvwvwvwvwv/jubilant-computing-machine/${BRANCH}/termux/deploy.sh"

    if curl -fsSL "$RAW_URL" -o "$HOME/roampal-android/termux/deploy.sh"; then
        chmod +x "$HOME/roampal-android/termux/deploy.sh"
        echo "✅ termux/deploy.sh восстановлен (${BRANCH})"
    else
        echo "⚠️ Не удалось загрузить deploy.sh из ${BRANCH}, пробую ветку work..."
        curl -fsSL "https://raw.githubusercontent.com/Wvwvwvwvwv/jubilant-computing-machine/work/termux/deploy.sh" \
          -o "$HOME/roampal-android/termux/deploy.sh"
        chmod +x "$HOME/roampal-android/termux/deploy.sh"
        echo "✅ termux/deploy.sh восстановлен (work)"
    fi
fi

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

# Самовосстановление старых шаблонов для Termux:
# тяжелые/компилируемые зависимости исключаем из pip-профиля и оставляем только pkg-версии.
for req in \
  "$HOME/roampal-android/backend/core/requirements-termux.txt" \
  "$HOME/roampal-android/backend/embeddings/requirements-lite-termux.txt"
do
  sed -i '/^numpy==/d' "$req" 2>/dev/null || true
  sed -i '/^torch==/d' "$req" 2>/dev/null || true
  sed -i '/^sentence-transformers==/d' "$req" 2>/dev/null || true
  sed -i '/^chromadb==/d' "$req" 2>/dev/null || true
done

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

# Termux default: lite embeddings profile to avoid source builds (numpy/ninja/torch chain).
# Full profile only by explicit opt-in: FORCE_FULL_EMBEDDINGS=1 bash termux/setup.sh
if [ "${FORCE_FULL_EMBEDDINGS:-0}" = "1" ] && [ "$PY_VER" != "3.13" ]; then
    echo "ℹ️ FORCE_FULL_EMBEDDINGS=1: trying full embeddings requirements."
    if ! $PIP_BIN install $PIP_FLAGS -c "$CONSTRAINTS" -r requirements.txt; then
        echo "⚠️ Full embeddings deps failed, falling back to lite Termux profile..."
        $PIP_BIN install $PIP_FLAGS -c "$CONSTRAINTS" -r requirements-lite-termux.txt
    fi
else
    echo "ℹ️ Using lite embeddings profile on Termux (stable default, Python=$PY_VER)."
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
