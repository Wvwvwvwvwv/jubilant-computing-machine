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
curl -sSL https://raw.githubusercontent.com/yourusername/roampal-android/main/termux/setup.sh | bash
```

### 2. Запуск сервисов
```bash
cd ~/roampal-android
./termux/start-services.sh
```

### 3. Запуск frontend
```bash
cd frontend
npm run dev
```

Открыть http://localhost:5173

## Возможности

- ✅ Чат с локальным LLM
- ✅ Память с outcome-based learning (Roampal)
- ✅ Загрузка/удаление книг и текстов
- ✅ Песочница для выполнения кода
- ✅ Векторный поиск и эмбеддинги
- ✅ MCP интеграция
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
- [Разработка](docs/development.md)

## Благодарности

Проект Roampal Android построен на основе следующих замечательных проектов. Спасибо всем разработчикам и сообществам:

### Ключевые компоненты

- **[Roampal](https://github.com/roampal-ai/roampal)** - основной фреймворк и [MCP интеграция](https://github.com/roampal-ai/roampal?tab=readme-ov-file#mcp-integration)
- **[Termux](https://termux.dev/)** - терминальная среда для Android
- **[proot-distro](https://github.com/termux/proot-distro)** - запуск Linux дистрибутивов в Termux
- **[KoboldCpp](https://github.com/LostRuins/koboldcpp)** - оптимизированный LLM на C++
- **[llama.cpp](https://github.com/ggerganov/llama.cpp)** - CPU-инференс для LLM
- **[Ralph](https://github.com/snarktank/ralph)** - инструменты и утилиты
- **[Hugging Face](https://huggingface.co/)** - модели и датасеты
- **[Node.js](https://nodejs.org/)** - JavaScript runtime
- **[Python](https://www.python.org/)** - язык программирования

Спасибо всем мейнтейнерам и контрибьюторам за их отличную работу!