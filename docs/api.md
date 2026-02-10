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
- `file` - .txt или .md файл

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
