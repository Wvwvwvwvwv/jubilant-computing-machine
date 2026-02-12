# Установка Roampal Android

## Требования

- Android устройство с root доступом
- Termux (установить с F-Droid)
- Минимум 8GB свободного места
- Рекомендуется: 16GB+ RAM

## Быстрая установка

### 1. Установка Termux

Скачайте Termux с [F-Droid](https://f-droid.org/packages/com.termux/):

```bash
# НЕ используйте версию из Google Play - она устарела!
```

### 2. Запуск автоустановки

```bash
# В Termux выполните:
curl -sSL https://raw.githubusercontent.com/Wvwvwvwvwv/jubilant-computing-machine/main/termux/setup.sh | bash
```

Скрипт автоматически:
- Обновит Termux
- Установит все зависимости
- Скачает и скомпилирует KoboldCpp
- Настроит Debian в proot-distro
- Установит Python и Node.js зависимости
- Предложит скачать рекомендуемую модель

### 3. Скачивание модели

Рекомендуемые модели для Snapdragon 8 Elite:

**Для начала (легкая):**
```bash
cd $HOME/roampal-android/models
wget https://huggingface.co/bartowski/L3-8B-Stheno-v3.2-GGUF/resolve/main/L3-8B-Stheno-v3.2-Q4_K_M.gguf
```

**Для продвинутых (тяжелая):**
```bash
wget https://huggingface.co/bartowski/Qwen2.5-14B-Instruct-GGUF/resolve/main/Qwen2.5-14B-Instruct-Q4_K_M.gguf
```

### 4. Запуск

```bash
cd $HOME/roampal-android
./termux/start-services.sh
```

Откройте в браузере: `http://localhost:5173`

## Ручная установка

Если автоустановка не сработала:

### Шаг 1: Обновление Termux

```bash
pkg update && pkg upgrade -y
```

### Шаг 2: Установка зависимостей

```bash
pkg install -y python python-pip nodejs git wget curl proot-distro openssl clang make cmake
```

### Шаг 3: Клонирование репозитория

```bash
cd ~
git clone https://github.com/Wvwvwvwvwv/jubilant-computing-machine.git
cd jubilant-computing-machine
```

### Шаг 4: KoboldCpp

```bash
cd ~
git clone https://github.com/LostRuins/koboldcpp.git
cd koboldcpp
make LLAMA_PORTABLE=1
```

### Шаг 5: Backend

```bash
cd $HOME/jubilant-computing-machine/backend/core
pip install -r requirements.txt

cd $HOME/jubilant-computing-machine/backend/embeddings
pip install -r requirements.txt

cd $HOME/jubilant-computing-machine/backend/sandbox
pip install -r requirements.txt
```

### Шаг 6: Frontend

```bash
cd $HOME/jubilant-computing-machine/frontend
npm install
```

### Шаг 7: Запуск

```bash
cd $HOME/jubilant-computing-machine
./termux/start-services.sh
```

## Проверка установки

```bash
# Проверка сервисов
curl http://localhost:5001/api/v1/model  # KoboldCpp
curl http://localhost:8000/health        # Core API
curl http://localhost:8001/health        # Embeddings
curl http://localhost:5173               # Frontend
```

## Устранение проблем

### KoboldCpp не запускается

```bash
# Проверьте наличие модели
ls $HOME/jubilant-computing-machine/models/*.gguf

# Запустите вручную
cd $HOME/koboldcpp
python koboldcpp.py --model $HOME/jubilant-computing-machine/models/YOUR_MODEL.gguf
```

### Backend ошибки

```bash
# Проверьте логи
cat $HOME/jubilant-computing-machine/logs/core.log
cat $HOME/jubilant-computing-machine/logs/embeddings.log
cat $HOME/jubilant-computing-machine/logs/sandbox.log
```

### Frontend не открывается

```bash
# Проверьте Node.js версию
node --version  # Должно быть v18+

# Переустанов��те зависимости
cd $HOME/jubilant-computing-machine/frontend
rm -rf node_modules
npm install
```

## Обновление

```bash
cd $HOME/jubilant-computing-machine
git pull
./termux/stop-services.sh
./termux/start-services.sh
```