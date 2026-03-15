# API Documentation

## Core API (Port 8000)

Base URL: `http://localhost:8000`

### Chat Endpoints

#### POST /api/chat

Отправить сообщение в чат с LLM.

**Request:**
```json
{
  "messages": [
    {"role": "user", "content": "Привет!"}
  ],
  "use_memory": true,
  "max_tokens": 512,
  "temperature": 0.7
}
```

**Response:**
```json
{
  "response": "Привет! Чем могу помочь?",
  "memory_used": true,
  "context_items": 3
}
```

#### POST /api/chat/feedback

Отправить обратную связь для outcome learning.

**Query Parameters:**
- `interaction_id` (string) - ID взаимодействия
- `helpful` (boolean) - Полезен ли ответ

**Response:**
```json
{
  "status": "success",
  "message": "Обратная связь записана"
}
```

> Week 1 retrieval rollout: `POST /api/chat` can use either `legacy` memory retrieval (default) or a multimodal retriever when `MULTIMODAL_RAG_ENABLED=1` and backend runtime injects `app.state.multimodal_retriever`.

### Memory Endpoints

#### POST /api/memory/search

Поиск в памяти.

**Request:**
```json
{
  "query": "как работает Python",
  "limit": 10
}
```

**Response:**
```json
{
  "results": [
    {
      "id": "abc123",
      "content": "Python - интерпретируемый язык...",
      "score": 0.85,
      "outcome_score": 0.4,
      "metadata": {}
    }
  ],
  "count": 1
}
```

#### POST /api/memory/add

Добавить элемент в память.

**Request:**
```json
{
  "content": "Важная информация",
  "metadata": {"source": "manual"}
}
```

**Response:**
```json
{
  "id": "xyz789",
  "status": "added"
}
```

#### DELETE /api/memory/{memory_id}

Удалить элемент из памяти.

**Response:**
```json
{
  "status": "deleted"
}
```

#### GET /api/memory/stats

Статистика памяти.

**Response:**
```json
{
  "total_items": 150,
  "interactions": 120,
  "permanent_memories": 30
}
```

### Books Endpoints

#### POST /api/books/upload

Загрузить книгу или текстовый файл.

**Request:** `multipart/form-data`
- `file` - .txt, .md или .pdf файл (для PDF: text-layer extraction через `pypdf`, fallback OCR через `pytesseract`)

**Response:**
```json
{
  "id": "abc123",
  "filename": "book.txt",
  "size": 102400,
  "status": "uploaded"
}
```

#### GET /api/books/list

Список всех книг.

**Response:**
```json
{
  "books": [
    {
      "id": "abc123",
      "filename": "book.txt",
      "size": 102400,
      "modified": 1234567890
    }
  ],
  "count": 1
}
```

#### DELETE /api/books/{book_id}

Удалить книгу.

**Response:**
```json
{
  "status": "deleted",
  "id": "abc123"
}
```

#### GET /api/books/{book_id}/content

Получить содержимое книги.

**Response:**
```json
{
  "id": "abc123",
  "filename": "book.txt",
  "content": "Содержимое книги..."
}
```


### Tasks Endpoints (MVP baseline v1)

> Execution-контракт: endpoint `POST /api/tasks/{task_id}/run` использует LLM planner (KoboldCpp) с детерминированным fallback.
> Если LLM недоступен/даёт невалидный JSON, используется безопасный эвристический fallback с поддержкой префиксов.

#### POST /api/tasks/

Создать задачу.

**Request:**
```json
{
  "goal": "echo tasks_ok",
  "max_attempts": 3,
  "approval_required": false
}
```

**Response (пример):**
```json
{
  "task_id": "0f1c...",
  "goal": "echo tasks_ok",
  "status": "PENDING",
  "attempt": 0,
  "max_attempts": 3,
  "approval_required": false,
  "approved": true,
  "events": [
    {
      "kind": "task_created",
      "message": "Task created",
      "payload": {
        "goal": "echo tasks_ok",
        "max_attempts": 3,
        "approval_required": false,
        "policy_requires_approval": false
      }
    }
  ]
}
```

#### GET /api/tasks/

Список задач. Query параметр: `limit` (по умолчанию 50).

#### GET /api/tasks/{task_id}

Получить карточку задачи по id.

#### POST /api/tasks/{task_id}/approve

Подтвердить задачу, если она находится в состоянии `NEEDS_APPROVAL`.

#### POST /api/tasks/{task_id}/run

Запустить выполнение задачи.

- Planner запрашивает у LLM JSON вида `{tool, language, code, timeout}` и исполняет `tool=sandbox.execute`.
- При ошибке LLM используется fallback: префиксы (`python:`, `js:`, ...) + intent-маркеры.
- При `HTTPException(408)` из sandbox задача получает транзиентный результат (`exit_code=124`).
- Событие `task_started` содержит `payload` с полями `tool` и `language`.

**Planner routing examples:**
```text
goal: "echo ok"                  -> language=bash
goal: "python: print(2+2)"       -> language=python
goal: "js: console.log(42)"      -> language=javascript
goal: "print(2+2)"               -> heuristic language=python
```

### Tasks Statuses

- `PENDING`
- `RUNNING`
- `RETRYING`
- `SUCCESS`
- `FAILED`
- `NEEDS_APPROVAL`

### Tasks Security/Approval Policy (v1)

- Используется policy version: `task-approval-policy-v1`.
- Risk levels: `low`, `medium`, `high`.
- `high` риск (например destructive patterns) требует обязательного approve и переводит задачу в `NEEDS_APPROVAL`.
- События `task_created`, `task_needs_approval`, `task_blocked`, `task_approved` содержат policy/audit поля (`policy_version`, `risk_level`, `approval_reason`, `approver`, `approved_at`).
- Для approve-гейта используется `approval_fingerprint`; если задача/политика дрейфует после approve, событие `task_approval_invalidated` сбрасывает approve и снова требует подтверждение.

### Tasks Retry Policy (v1)

- `transient` ошибки: переход в `RETRYING` (если `attempt < max_attempts`) и событие `task_retry`.
- `command`, `permission`, `runtime`: fail-fast (событие `task_failed` без промежуточного `RETRYING`).
- События `task_retry` и `task_failed` включают поля `retry_allowed` и `retry_delay_seconds`.

### Tasks Event Ordering Contract (v1)

Ниже зафиксирован ожидаемый порядок событий для ключевых веток исполнения.

1. **Success flow**
   - `task_created` → `task_started` → `task_success`

2. **Retry/failed flow**
   - `task_created` → `task_started` → `task_retry` (повторяется) → `task_failed`

3. **Approval-gated flow**
   - `task_created` → `task_needs_approval` → `task_blocked` → `task_approved` → `task_started` → (`task_success` | `task_retry` | `task_failed`)
   - при дрейфе policy/goal: `... -> task_approval_invalidated -> task_needs_approval/task_blocked`

4. **Terminal re-run / idempotent skip**
   - После терминального статуса (`SUCCESS` или `FAILED`) повторный `run` не выполняет команду заново и пишет событие `task_skip`.

### Tasks Event Types (v1)

- `task_created`
- `task_needs_approval`
- `task_blocked`
- `task_approved`
- `task_started`
- `task_retry`
- `task_failed`
- `task_success`
- `task_skip`
- `task_approval_invalidated`

### Sandbox Endpoints

#### POST /api/sandbox/execute

Выполнить код в песочнице.

**Request:**
```json
{
  "code": "print('Hello')",
  "language": "python",
  "timeout": 30
}
```

**Response:**
```json
{
  "execution_id": "exec123",
  "stdout": "Hello\n",
  "stderr": "",
  "exit_code": 0,
  "execution_time": 0.15
}
```

**Supported Languages:**
- `python`
- `javascript`
- `bash`

#### GET /api/sandbox/list

Список выполненных задач.

**Response:**
```json
{
  "executions": [
    {
      "id": "exec123",
      "created": 1234567890
    }
  ],
  "count": 1
}
```

#### DELETE /api/sandbox/{execution_id}

Удалить workspace выполнения.

**Response:**
```json
{
  "status": "deleted"
}
```


## Companion API (Port 8000)

Base URL: `http://localhost:8000`

### GET /api/companion/session

Текущая сессионная политика поведения ассистента (`reasoning_mode`, `challenge_mode`, `initiative_mode`, `voice_mode`).

### PATCH /api/companion/session

Частичное обновление сессионной политики.

Пример:
```json
{
  "reasoning_mode": "wild",
  "challenge_mode": "strict",
  "initiative_mode": "proactive",
  "voice_mode": "ptt"
}
```

### GET /api/companion/last-response-trace

Последний explainability trace по ответу ассистента. До появления ответа может вернуть `null`.

Примечание: trace обновляется после успешного `POST /api/chat/` и отражает активные `reasoning_mode/challenge_mode`.
Примечание: `relationship_used` в trace заполняется ID relationship-фактов, реально подмешанных в chat prompt.
Примечание: поле `retrieval_backend` показывает источник retrieval-контекста (`legacy` или `multimodal`).

### GET /api/companion/response-traces?limit=50

История explainability trace (в порядке накопления) для аудита динамики поведения.

### GET /api/companion/relationship-profile

Получить профиль relationship memory (стиль, дебат-предпочтения, инициативность).

### PATCH /api/companion/relationship-profile

Частичное обновление relationship profile.

Пример:
```json
{
  "style": {"verbosity": "high"},
  "debate_preferences": {"strictness": "strict"}
}
```

### POST /api/companion/relationship-facts

Добавить relationship-факт.

Пример:
```json
{
  "fact": "Пользователь предпочитает сначала риски",
  "source": {"type": "chat_message", "ref_id": "msg_1"},
  "confidence": 0.8,
  "ttl_days": 90
}
```

### GET /api/companion/relationship-facts?query=...&limit=...

Поиск активных relationship-фактов.

### POST /api/companion/relationship-facts/{fact_id}/invalidate

Ручная инвалидизация relationship-факта (status -> `invalidated`).

### POST /api/companion/proposals/suggest

Сгенерировать инициативное предложение по теме (`topic`, опционально `context`) с учетом `initiative_mode` и `challenge_mode` текущей сессии.

- При `initiative_mode=off` вернётся `400`.
- При `initiative_mode=proactive` предложение создаётся как `unsolicited=true`.

### POST /api/companion/proposals

Создать инициативное предложение (`reason`, `expected_value`, `risk_level`, `stop_condition`, `unsolicited`).
Для `unsolicited=true` применяется профильный лимит `max_unsolicited_per_hour`.

### GET /api/companion/proposals?status=open&limit=20

Список предложений по статусу (`open|accepted|dismissed|all`).

### POST /api/companion/proposals/{proposal_id}/accept

Отметить предложение как принятое.

### GET /api/companion/proposals/{proposal_id}/events?limit=50

Получить audit trail по инициативному предложению (`created`, `status_accepted`, `status_dismissed` и т.д.).

### POST /api/companion/proposals/{proposal_id}/dismiss

Отметить предложение как отклонённое.

## Voice API (Port 8000)

Base URL: `http://localhost:8000`

### POST /api/voice/session/start

Старт локальной voice-сессии.

Пример:
```json
{
  "mode": "ptt",
  "stt_engine": "local_whisper_cpp",
  "tts_engine": "local_piper"
}
```

### POST /api/voice/session/{voice_session_id}/stop

Остановка voice-сессии.

### GET /api/voice/session/{voice_session_id}/health

Health-статус сессии (для MVP: synthetic health snapshot).

Возвращает также активную voice-конфигурацию: `mode`, `stt_engine`, `tts_engine`.
Теперь health включает поля проверки микрофона:
- `microphone_verified` (`true|false`)
- `microphone_source` (источник проверки)
- `microphone_detail` (диагностическая строка)

Если микрофон не подтвержден, `input_device=not_verified` и `stt=degraded`.

### PATCH /api/voice/session/{voice_session_id}/metrics

Обновить наблюдаемые voice-метрики для оценки readiness (`latency_p95_ms`, `crash_free_rate`, `audio_loss_percent`, `approval_bypass_incidents`, `user_score`).

### POST /api/voice/session/{voice_session_id}/microphone/verify

Записать результат проверки физического микрофона для текущей voice-сессии.

Пример:
```json
{
  "verified": true,
  "source": "termux_microphone_record",
  "detail": "bytes=16384"
}
```

### GET /api/voice/session/{voice_session_id}/go-no-go

Вернуть решение `GO|NO_GO` по критериям rollout и список проваленных checks.

Важно: в checks добавлен `microphone_verified_true`; без подтверждения микрофона решение будет `NO_GO`.

## Embeddings Service (Port 8001)

Base URL: `http://localhost:8001`

### POST /embed

Генерация эмбеддингов для текстов.

**Request:**
```json
{
  "texts": ["текст 1", "текст 2"]
}
```

**Response:**
```json
{
  "embeddings": [
    [0.1, 0.2, ...],
    [0.3, 0.4, ...]
  ],
  "model": "all-MiniLM-L6-v2",
  "dimension": 384
}
```

### GET /health

Проверка здоровья сервиса.

**Response:**
```json
{
  "status": "healthy",
  "model_loaded": true
}
```

## KoboldCpp API (Port 5001)

Base URL: `http://localhost:5001`

### POST /api/v1/generate

Генерация текста.

**Request:**
```json
{
  "prompt": "User: Привет!\n\nAssistant:",
  "max_length": 512,
  "temperature": 0.7,
  "top_p": 0.9,
  "top_k": 40,
  "rep_pen": 1.1,
  "stop_sequence": ["</s>", "User:"]
}
```

**Response:**
```json
{
  "results": [
    {
      "text": " Привет! Чем могу помочь?"
    }
  ]
}
```

### GET /api/v1/model

Информация о загруженной модели.

**Response:**
```json
{
  "result": "model_name",
  "model": "L3-8B-Stheno-v3.2-Q4_K_M.gguf"
}
```

## Error Responses

Все API возвращают ошибки в формате:

```json
{
  "detail": "Описание ошибки"
}
```

**HTTP Status Codes:**
- `400` - Bad Request (неверные параметры)
- `404` - Not Found (ресурс не найден)
- `408` - Timeout (превышен таймаут)
- `500` - Internal Server Error (внутренняя ошибка)
- `503` - Service Unavailable (сервис недоступен)

## Rate Limiting

Нет ограничений - все локально.

## Authentication

Не требуется - все локально.


## Retrieval API (Port 8000)

Base URL: `http://localhost:8000`

### GET /api/retrieval/health

Показывает состояние week-1 retrieval переключателя:
- `multimodal_flag` — включен ли `MULTIMODAL_RAG_ENABLED`
- `multimodal_injected` — подмешан ли runtime retriever в `app.state.multimodal_retriever`

### POST /api/retrieval/search

Единая точка retrieval-поиска (legacy/multimodal в зависимости от флага).

**Request:**
```json
{
  "query": "найди контекст по миграции",
  "limit": 8
}
```

**Response:**
```json
{
  "backend": "legacy",
  "count": 1,
  "results": [
    {
      "id": "abc123",
      "content": "...",
      "score": 0.91
    }
  ]
}
```


### POST /api/retrieval/index

Создать indexing job (week-2 bootstrap).

**Request:**
```json
{
  "source_type": "book",
  "source_ref": "book_123"
}
```

**Response:**
```json
{
  "job_id": "rj_abc123",
  "source_type": "book",
  "source_ref": "book_123",
  "status": "completed",
  "created_at": 1730000000.0,
  "updated_at": 1730000000.0,
  "error": null
}
```

### GET /api/retrieval/jobs?limit=20

Список indexing jobs.

### GET /api/retrieval/jobs/{job_id}

Детали indexing job по id. Возвращает `404`, если job не найден.
