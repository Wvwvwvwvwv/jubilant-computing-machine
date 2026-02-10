#!/data/data/com.termux/files/usr/bin/bash
# Автоустановка Roampal Android Stack

set -e

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
    cd $HOME
    git clone https://github.com/yourusername/roampal-android.git
fi

cd $HOME/roampal-android

# Установка KoboldCpp
echo "🤖 Установка KoboldCpp..."
if [ ! -d "$HOME/koboldcpp" ]; then
    cd $HOME
    git clone https://github.com/LostRuins/koboldcpp.git
    cd koboldcpp
    make LLAMA_PORTABLE=1
fi

# Установка Termux Sandbox
echo "📦 Установка Termux Sandbox..."
if [ ! -d "$HOME/termux-sandbox" ]; then
    cd $HOME
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
mkdir -p $HOME/roampal-android/models
mkdir -p $HOME/roampal-android/data/memory
mkdir -p $HOME/roampal-android/data/books
mkdir -p $HOME/roampal-android/data/sandbox

# Установка Python зависимостей для backend
echo "🐍 Установка Python зависимостей..."
cd $HOME/roampal-android/backend/core
pip install -r requirements.txt

cd $HOME/roampal-android/backend/embeddings
pip install -r requirements.txt

cd $HOME/roampal-android/backend/sandbox
pip install -r requirements.txt

# Установка Node.js зависимостей для frontend
echo "📦 Установка Node.js зависимостей..."
cd $HOME/roampal-android/frontend
npm install

# Скачивание рекомендуемой модели (опционально)
echo "🤔 Скачать рекомендуемую модель? (y/n)"
read -r response
if [[ "$response" =~ ^([yY][eE][sS]|[yY])$ ]]; then
    echo "📥 Скачивание L3-8B-Stheno-v3.2..."
    cd $HOME/roampal-android/models
    wget https://huggingface.co/bartowski/L3-8B-Stheno-v3.2-GGUF/resolve/main/L3-8B-Stheno-v3.2-Q4_K_M.gguf
fi

echo ""
echo "✅ Установка завершена!"
echo ""
echo "Для запуска:"
echo "  cd ~/roampal-android"
echo "  ./termux/start-services.sh"
echo ""
