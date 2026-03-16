# Roampal Android - Локальный AI Ассистент

Полнофункциональный AI-ассистент на Android с локальным LLM, памятью, библиотекой и песочницей для выполнения кода.

## Стек

- **Termux**: Окружение Android
- **KoboldCpp**: Локальный LLM (GGUF модели)
- **Debian (proot-distro)**: Контейнер для сервисов
- **Backend**: FastAPI (core + embeddings + sandbox)
- **Frontend**: Vite + React + TypeScript
- **Memory**: Roampal outcome-based learning
- **Sandbox**: Termux-sandbox для безопасного выполнения кода

## Железо

- OnePlus 13
- Snapdragon 8 Elite
- 24GB RAM / 1TB Storage

## Быстрый старт

### 1. Установка Termux
```bash
# Скачать Termux с F-Droid
# Запустить автоустановку
curl -sSL https://raw.githubusercontent.com/Wvwvwvwvwv/jubilant-computing-machine/main/termux/setup.sh | bash
```

### 2. Запуск сервисов
```bash
cd ~/roampal-android
bash termux/start-services.sh
```

### 3. Запуск frontend
```bash
cd frontend
npm run dev
```

Открыть http://localhost:5173


### 4. Полный smoke-прогон
```bash
cd ~/roampal-android
bash termux/full-smoke.sh
```

### Voice readiness-check на устройстве
```bash
cd ~/roampal-android
# Базовый прогон (PTT, женский голос, GO-метрики по умолчанию)
bash termux/voice-readiness-check.sh

# Строгий режим: завершится с code=1, если решение не GO
MODE=duplex VOICE_GENDER=male bash termux/voice-readiness-check.sh --strict

# сохранить JSON-отчёт прогона
bash termux/voice-readiness-check.sh --json-out logs/voice-readiness.json

# требовать подтверждение физического микрофона (Termux:API/arecord)
bash termux/voice-readiness-check.sh --require-mic

# если прямой probe недоступен, скрипт в интерактивном TTY предложит ручное подтверждение
# (ответьте y, если видите реальную активность микрофона на устройстве)
bash termux/voice-readiness-check.sh

# ручной override, если физическая проверка недоступна в текущем окружении
bash termux/voice-readiness-check.sh --manual-mic-ok
```

### Настройка микрофона в Termux (обязательно для auto preflight)
```bash
cd ~/roampal-android

# 1) установить Termux:API CLI
pkg update && pkg install -y termux-api

# 2) выдать Android-разрешение RECORD_AUDIO для приложения Termux
#    Android Settings -> Apps -> Termux -> Permissions -> Microphone -> Allow

# 3) базовый тест записи (должен отработать без ошибки permissions)
termux-microphone-record -d 2
```

Если `termux-microphone-record` недоступен или не может создать временный файл в `/tmp`,
`voice-readiness-check.sh` автоматически использует fallback-директории (`$TMPDIR`, `$HOME/tmp`,
`/data/data/com.termux/files/usr/tmp`, `/tmp`).

Если видите "Ошибка соединения с сервером", запустите диагностику:
```bash
cd ~/roampal-android
bash termux/diagnose.sh
```


### Включение интернет-поиска и скачивания инструментов
```bash
cd ~/roampal-android
export ENABLE_ONLINE_TOOLS=1

# Поиск из API
curl -sS -X POST http://127.0.0.1:8000/api/online/search \
  -H 'Content-Type: application/json' \
  -d '{"query":"latest python release","limit":3}'

# Скачать файл/инструмент в ~/roampal-android/downloads
curl -sS -X POST http://127.0.0.1:8000/api/online/download \
  -H 'Content-Type: application/json' \
  -d '{"url":"https://example.com/tool.sh","filename":"tool.sh"}'
```

Для чата интернет-контекст можно подтягивать префиксами `web:` или `search:`
(например: `web: свежие новости по llama.cpp`).

### Проверка, что модель не выходит в интернет
```bash
cd ~/roampal-android
bash termux/check-no-internet-leak.sh

# строгий режим (exit code != 0 при подозрительных внешних соединениях)
STRICT=1 bash termux/check-no-internet-leak.sh
```

Скрипт делает preflight локальных endpoint-ов и снимает snapshot сокетов (`ss -tpn`) во время chat-запроса.
Отчёты сохраняются в `logs/net-leak-report-*.json` и `logs/net-sockets-*.log`.

### Проверка целостности репозитория (GitHub/ветка)
```bash
cd ~/roampal-android
bash termux/verify-repo-integrity.sh ~/roampal-android work
```

### Очистка памяти от технических/тестовых записей
```bash
cd ~/roampal-android
# сначала dry-run (показать кандидатов)
bash termux/cleanup-memory-noise.sh

# затем применить удаление
bash termux/cleanup-memory-noise.sh --apply
```


### Единая полная проверка (end-to-end)
```bash
cd ~/roampal-android
bash scripts/full-end-to-end-check.sh
```

Этот скрипт запускается из корня репозитория и выполняет:
- быструю проверку синтаксиса ключевых backend-модулей;
- единый интеграционный smoke-тест `backend/core/tests/test_full_system_check.py`.

Если в окружении нет глобальной команды `pytest`, скрипт автоматически попробует `poetry run pytest` и затем `python -m pytest`.

### 5. Автоматическое развертывание (рекомендуется)
```bash
curl -sSL https://raw.githubusercontent.com/Wvwvwvwvwv/jubilant-computing-machine/main/termux/deploy.sh | bash -s -- work
```

Локальный запуск (если репозиторий уже есть):
```bash
cd ~/roampal-android
bash termux/deploy.sh work
```

## Возможности

- ✅ Чат с локальным LLM
- ✅ Память с outcome-based learning (Roampal)
- ✅ Загрузка/удаление книг и текстов
- ✅ Песочница для выполнения кода
- ✅ Векторный поиск и эмбеддинги
- ✅ MCP интеграция
- ✅ Companion session API (STABLE/WILD, challenge/initiative/voice modes)
- ✅ Voice control-plane API (start/stop/health for local voice sessions)
- ✅ 100% локально, без облака

## Структура

```
termux/          - Скрипты установки и запуска
backend/core/    - Главный API оркестратор
backend/embeddings/ - Сервис эмбеддингов
backend/sandbox/ - Выполнение кода
frontend/        - React UI
models/          - GGUF модели
data/            - Персистентные данные
```

## Документация

- [Установка](docs/installation.md)
- [Архитектура](docs/architecture.md)
- [API](docs/api.md)
- [Handoff v2](docs/handoff-v2.md)
- [Companion Vision (STABLE/WILD, personality, voice)](docs/companion-vision.md)
- [Companion Implementation Plan (API + DB + Voice Go/No-Go)](docs/companion-implementation-plan.md)
- [Multimodal RAG Week 1 Plan](docs/multimodal-rag-week1.md)
- [Multimodal RAG Week 2 Plan](docs/multimodal-rag-week2.md)
- [Multimodal RAG Week 3 Plan](docs/multimodal-rag-week3.md)

## Backend dependency management

Backend Python dependencies are managed via `pyproject.toml` (Poetry).
Legacy `backend/core/requirements*.txt` files were removed.

For constrained Termux environments, deploy/setup installs only the core Poetry group by default;
the heavy memory stack (`chromadb`, `sentence-transformers`) stays optional and can be installed via
`ROAMPAL_INSTALL_MEMORY_GROUP=1 bash termux/setup.sh`.

If Poetry installation fails on Termux Python 3.13 due `pydantic-core`/rust build issues,
`termux/setup.sh` automatically falls back to a pip-based constrained install path.
In that fallback path, `numpy` is expected from Termux package `python-numpy` (not built via pip).
The fallback also installs plain `uvicorn` (without `[standard]`) to avoid `watchfiles`/`maturin`
Android API-level build failures on Termux.
Setup also exports `ANDROID_API_LEVEL` automatically (from system SDK level) to improve
compatibility with Android-native `maturin`/rust builds when they are encountered.
OCR Python extras (`pytesseract`/`pillow`) are installed in best-effort mode in Termux fallback;
if they fail to build, API still keeps CLI OCR fallback (`tesseract`/`pdftoppm`) when available.
Setup now also tries to install OCR system deps via `pkg` (`tesseract`, `poppler`, `libjpeg-turbo`,
`libpng`, `zlib`, `build-essential`) and retries Python OCR extras in best-effort mode.
