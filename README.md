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

Если видите "Ошибка соединения с сервером", запустите диагностику:
```bash
cd ~/roampal-android
bash termux/diagnose.sh
```


### Проверка целостности репозитория (GitHub/ветка)
```bash
cd ~/roampal-android
bash termux/verify-repo-integrity.sh ~/roampal-android work
```

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
