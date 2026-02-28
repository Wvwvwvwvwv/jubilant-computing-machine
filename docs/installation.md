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
cd ~/roampal-android/models
wget https://huggingface.co/bartowski/L3-8B-Stheno-v3.2-GGUF/resolve/main/L3-8B-Stheno-v3.2-Q4_K_M.gguf
```

**Для продвинутых (тяжелая):**
```bash
wget https://huggingface.co/bartowski/Qwen2.5-14B-Instruct-GGUF/resolve/main/Qwen2.5-14B-Instruct-Q4_K_M.gguf
```

### 4. Запуск

```bash
cd ~/roampal-android
bash termux/start-services.sh
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
pkg install -y python python-pip python-numpy rust nodejs git wget curl proot-distro openssl clang make cmake
```

### Шаг 3: Клонирование репозитория

```bash
cd ~
git clone https://github.com/Wvwvwvwvwv/jubilant-computing-machine.git roampal-android
cd roampal-android
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
cd ~/roampal-android/backend/core
python -m pip install --prefer-binary -c ~/roampal-android/termux/constraints-termux.txt -r requirements-termux.txt

cd ~/roampal-android/backend/sandbox
python -m pip install --prefer-binary -c ~/roampal-android/termux/constraints-termux.txt -r requirements-termux.txt

cd ~/roampal-android/backend/embeddings
python -m pip install --prefer-binary -c ~/roampal-android/termux/constraints-termux.txt -r requirements-lite-termux.txt
```

### Шаг 6: Frontend

```bash
cd ~/roampal-android/frontend
npm install
```

### Шаг 7: Запуск

```bash
cd ~/roampal-android
bash termux/start-services.sh
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
ls ~/roampal-android/models/*.gguf

# Запустите вручную
cd ~/koboldcpp
python koboldcpp.py --model ~/roampal-android/models/YOUR_MODEL.gguf
```

### Backend ошибки

```bash
# Проверьте логи
cat ~/roampal-android/logs/core.log
cat ~/roampal-android/logs/embeddings.log
```

### Ошибка `pydantic-core` / `maturin` в Termux

Если установка падает на `pydantic-core`, используйте Termux-профиль и constraints (без сборки `pydantic-core`).

> Важно: НЕ запускайте просто `python -m pip install pydantic` на Termux — это тянет pydantic v2 и сборку `pydantic-core` через `maturin`.

```bash
cd ~/roampal-android
python -m pip uninstall -y pydantic pydantic-core
python -m pip install --prefer-binary -c termux/constraints-termux.txt pydantic==1.10.21

cd backend/core && python -m pip install --prefer-binary -c ~/roampal-android/termux/constraints-termux.txt -r requirements-termux.txt
cd ../sandbox && python -m pip install --prefer-binary -c ~/roampal-android/termux/constraints-termux.txt -r requirements-termux.txt
cd ../embeddings && python -m pip install --prefer-binary -c ~/roampal-android/termux/constraints-termux.txt -r requirements-lite-termux.txt
```

### Frontend не открывается

```bash
# Перезапустите сервисы (скрипт сам проверит :5173 и применит fallback)
cd ~/roampal-android
bash termux/stop-services.sh
bash termux/start-services.sh

# Если всё ещё не открывается — проверьте лог фронта
tail -n 120 ~/roampal-android/logs/frontend.log

# Если в логе есть "Port 5173 is already in use":
pkill -f "frontend/node_modules/.bin/vite" || true
bash termux/start-services.sh
```

## Обновление

```bash
cd ~/roampal-android
git pull
./termux/stop-services.sh
bash termux/start-services.sh
```

### Зафиксировать рабочее состояние (на случай отката)

```bash
cd ~/roampal-android
git checkout -b backup/chat-fix-$(date +%Y%m%d-%H%M)
git tag -a stable-chat-fix -m "Working chat fix (ChatMessage + Kobold formatter)"
```

Скрипт `termux/start-services.sh` теперь выполняет preflight-проверку
`termux/verify-chat-fix.sh` и не даст запустить сервисы, если критичный фикc чата отсутствует.

Если фронт видит `❌ Ошибка соединения с сервером`, можно явно задать proxy target для Vite:

```bash
cd ~/roampal-android/frontend
VITE_API_PROXY_TARGET=http://127.0.0.1:8000 npm run dev -- --host 127.0.0.1 --port 5173 --strictPort
```

### Диагностика ошибки "Ошибка соединения с сервером"

Выполните полный диагностический прогон:

```bash
cd ~/roampal-android
bash termux/diagnose.sh
```

Быстрый ручной smoke-check:

```bash
cd ~/roampal-android
bash termux/stop-services.sh
bash termux/start-services.sh

curl -sS http://localhost:8000/health
curl -sS http://localhost:8001/health
curl -sS http://localhost:5001/api/v1/model
curl -sS http://127.0.0.1:5173 | head -c 300
```

Если фронт открыт, но чат пишет "Ошибка соединения с сервером", пришлите:

```bash
tail -n 120 ~/roampal-android/logs/core.log
tail -n 120 ~/roampal-android/logs/embeddings.log
tail -n 120 ~/roampal-android/logs/frontend.log

# Если в логе есть "Port 5173 is already in use":
pkill -f "frontend/node_modules/.bin/vite" || true
bash termux/start-services.sh
```

### Permission denied при запуске скриптов

Если видите `bash: ./termux/start-services.sh: Permission denied`, выполните:

```bash
cd ~/roampal-android
chmod +x termux/*.sh
bash termux/start-services.sh
```
