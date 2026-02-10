# Архитектура Roampal Android

## Обзор

```
┌─────────────────────────────────────────────────────────┐
│                    OnePlus 13 (Android)                 │
│                                                         │
│  ┌───────────────────────────────────────────────────┐ │
│  │              Termux Environment                   │ │
│  │                                                   │ │
│  │  ┌─────────────┐      ┌──────────────────────┐  │ │
│  │  │ KoboldCpp   │      │  Frontend (Vite)     │  │ │
│  │  │ :5001       │      │  :5173               │  │ │
│  │  │             │      │  React + TypeScript  │  │ │
│  │  │ GGUF Model  │      └──────────────────────┘  │ │
│  │  └─────────────┘                                │ │
│  │                                                   │ │
│  │  ┌─────────────────────────────────────────────┐ │ │
│  │  │     Debian (proot-distro)                   │ │ │
│  │  │                                             │ │ │
│  │  │  ┌──────────┐  ┌────────────┐  ┌─────────┐│ │ │
│  │  │  │ Core API │  │ Embeddings │  │ Sandbox ││ │ │
│  │  │  │ :8000    │  │ :8001      │  │         ││ │ │
│  │  │  │          │  │            │  │         ││ │ │
│  │  │  │ FastAPI  │  │ FastAPI    │  │ Executor││ │ │
│  │  │  └──────────┘  └────────────┘  └─────────┘│ │ │
│  │  └─────────────────────────────────────────────┘ │ │
│  │                                                   │ │
│  │  ┌─────────────────────────────────────────────┐ │ │
│  │  │              Data Storage                   │ │ │
│  │  │  • ChromaDB (memory)                        │ │ │
│  │  │  • Books (.txt/.md)                         │ │ │
│  │  │  • Sandbox workspaces                       │ │ │
│  │  └─────────────────────────────────────────────┘ │ │
│  └───────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────┘
```

## Компоненты

### 1. KoboldCpp (LLM Engine)

**Порт:** 5001  
**Роль:** Локальный inference GGUF моделей

**Возможности:**
- Загрузка GGUF моделей (Llama, Qwen, Mistral и др.)
- OpenAI-compatible API
- Оптимизация для ARM (Snapdragon 8 Elite)
- Context window до 32K токенов

**API Endpoints:**
- `POST /api/v1/generate` - Генерация текста
- `GET /api/v1/model` - Информация о модели

### 2. Core API (Orchestrator)

**Порт:** 8000  
**Роль:** Главный оркестратор всех сервисов

**Модули:**

#### Chat Router (`/api/chat`)
- Обработка сообщений
- Интеграция с памятью Roampal
- Проксирование в KoboldCpp
- Outcome-based learning

#### Memory Router (`/api/memory`)
- Поиск в памяти (hybrid: BM25 + vector)
- Добавление/удаление элементов
- Статистика

#### Books Router (`/api/books`)
- Загрузка .txt/.md файлов
- Индексация для поиска
- Управление библиотекой

#### Sandbox Router (`/api/sandbox`)
- Выполнение кода (Python/JS/Bash)
- Изоляция через Termux-sandbox
- Логирование результатов

**Сервисы:**

- `KoboldClient` - Клиент для KoboldCpp
- `EmbeddingsClient` - Клиент для embeddings
- `MemoryEngine` - Roampal логика

### 3. Embeddings Service

**Порт:** 8001  
**Роль:** Генерация векторных представлений

**Модель:** `all-MiniLM-L6-v2` (легковесная, 384 dim)

**API:**
- `POST /embed` - Генерация эмбеддингов

### 4. Sandbox

**Роль:** Безопасное выполнение кода

**Поддерживаемые языки:**
- Python
- JavaScript (Node.js)
- Bash

**Изоляция:**
- Отдельные workspace для каждого выполнения
- Timeout защита
- Логирование stdout/stderr

### 5. Frontend (React)

**Порт:** 5173  
**Роль:** Мобильный UI

**Страницы:**

- **Chat** - Диалог с LLM
  - Отправка сообщений
  - Feedback (👍/👎)
  - Переключение памяти

- **Memory** - Управление памятью
  - Поиск в памяти
  - Загрузка книг
  - Статистика

- **Sandbox** - Выполнение кода
  - Редактор кода
  - Выбор языка
  - Вывод результатов

## Поток данных

### Chat Flow

```
User Input
    ↓
Frontend (ChatPage)
    ↓
Core API (/api/chat)
    ↓
MemoryEngine.search() → ChromaDB
    ↓
KoboldClient.generate() → KoboldCpp
    ↓
MemoryEngine.add_interaction()
    ↓
Response to Frontend
    ↓
User Feedback (👍/👎)
    ↓
MemoryEngine.record_outcome()
```

### Memory Learning (Roampal)

```
Interaction Saved
    ↓
outcome_score = 0.0
    ↓
User Feedback
    ↓
helpful=True  → score += 0.2
helpful=False → score -= 0.3
    ↓
score < -0.5 → Auto-delete
score > 0.5  → Promoted
```

### Sandbox Flow

```
Code Input
    ↓
Frontend (SandboxPage)
    ↓
Core API (/api/sandbox/execute)
    ↓
Create workspace
    ↓
Execute with timeout
    ↓
Capture stdout/stderr
    ↓
Return result
```

## Хранение данных

### ChromaDB (Memory)

**Путь:** `~/roampal-android/data/memory/`

**Коллекции:**
- `roampal_memory` - Все элементы памяти

**Метаданные:**
```json
{
  "type": "interaction",
  "timestamp": 1234567890,
  "outcome_score": 0.2,
  "context_ids": ["id1", "id2"]
}
```

### Books

**Путь:** `~/roampal-android/data/books/`

**Формат:** `{hash}_{filename}.txt`

### Sandbox Workspaces

**Путь:** `~/roampal-android/data/sandbox/{execution_id}/`

## Производительность

### Оптимизации для Snapdragon 8 Elite

1. **KoboldCpp:**
   - `LLAMA_PORTABLE=1` для ARM
   - `--threads 8` (8 ядер)
   - `--contextsize 8192` (баланс RAM/скорость)

2. **Embeddings:**
   - Легковесная модель (80MB)
   - Batch processing

3. **Memory:**
   - ChromaDB с HNSW индексом
   - Кэширование частых запросов

### Потребление ресурсов

| Компонент | RAM | CPU | Disk |
|-----------|-----|-----|------|
| KoboldCpp (8B Q4) | ~6GB | 60% | 5GB |
| Core API | ~500MB | 5% | 100MB |
| Embeddings | ~300MB | 10% | 100MB |
| Frontend | ~200MB | 5% | 50MB |
| **Total** | **~7GB** | **80%** | **~5.5GB** |

## Безопасность

### Sandbox Isolation

- Отдельные директории для каждого выполнения
- Timeout защита (default 30s)
- Нет доступа к системным файлам

### Data Privacy

- 100% локально
- Нет телеметрии
- Нет облачных запросов

## Масштабирование

### Добавление новых сервисов

1. Создать новый роутер в `backend/core/routers/`
2. Зарегистрировать в `main.py`
3. Добавить API клиент в `frontend/src/api/`

### Интеграция MCP

Roampal поддерживает MCP (Model Context Protocol):

```python
# Пример MCP интеграции
from roampal_mcp import RoampalMCP

mcp = RoampalMCP(memory_engine)
mcp.register_tools([
    "search_memory",
    "add_to_memory",
    "record_outcome"
])
```

## Мониторинг

### Логи

```bash
# Все логи
ls ~/roampal-android/logs/

# Просмотр в реальном времени
tail -f ~/roampal-android/logs/core.log
```

### Health Checks

```bash
# Проверка всех сервисов
curl http://localhost:5001/api/v1/model
curl http://localhost:8000/health
curl http://localhost:8001/health
```
