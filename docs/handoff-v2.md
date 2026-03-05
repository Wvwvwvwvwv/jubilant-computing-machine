# Handoff v2 (актуализировано)

Краткий срез текущего состояния репозитория и ближайший план.

## Что уже есть

### Backend (Core)
- Подключены роуты: `/api/chat`, `/api/memory`, `/api/books`, `/api/sandbox`, `/api/tasks`.
- `MemoryEngine` и `TaskRunner` инициализируются в lifespan приложения.
- Есть `/health` и `/docs`.

### Tasks API
- Реализованы endpoints:
  - `POST /api/tasks/` — создание задачи,
  - `GET /api/tasks/` — список,
  - `GET /api/tasks/{task_id}` — карточка,
  - `POST /api/tasks/{task_id}/approve` — ручное одобрение,
  - `POST /api/tasks/{task_id}/run` — запуск через sandbox (`bash`).
- Стейт-машина задачи: `PENDING`, `RUNNING`, `RETRYING`, `SUCCESS`, `FAILED`, `NEEDS_APPROVAL`.
- Включены:
  - автоматический `approval_required` для опасных шаблонов команд,
  - классификация ошибок (`permission`, `command`, `transient`, `runtime`),
  - аудит-события в `backend/core/logs/task_audit.log`.

### Frontend
- Добавлена страница `TasksPage` с созданием/запуском/approve задач и просмотром последних событий.
- Добавлен роут `/tasks` и пункт «Задачи» в нижней навигации.
- В API-клиенте добавлен `tasksAPI`.

## Что важно учитывать сейчас
- `TaskRunner` сохраняет состояние в `backend/core/logs/tasks_state.json` и загружает его на старте (базовая file-based persistence).
- `run` пока исполняет `goal` как `bash` без planner/tool-routing.
- Нужны интеграционные тесты с персистентным хранилищем задач перед production-эксплуатацией.
- Embeddings сервис теперь имеет deterministic fallback, в `/health` отражаются `fallback_active` и `fallback_dimension`.

## Что делать дальше (поэтапно)
1. **Persistence v2**: заменить file-based `tasks_state.json` на SQLite/Postgres и добавить миграции схемы.
2. **Planner/Tools**: развязать `goal` и `bash`, добавить маршрутизацию по инструментам.
3. **Надёжность**: расширить retry/backoff policy с учётом `error_class`.
4. **Безопасность**: ввести policy-уровни действий + журнал подтверждений пользователя.
5. **Тесты/CI**: добавить автотесты для `/api/tasks` и e2e smoke в CI.

## Базовые проверки
```bash
# backend
python -m py_compile backend/core/main.py backend/core/routers/tasks.py backend/core/services/task_runner.py

# frontend
cd frontend && npm run build
```


## Операционный smoke
- Добавлен скрипт `termux/full-smoke.sh` для полного прогона: restart + health + chat + memory + sandbox + tasks.
