# Репозиторный аудит (main vs work) — 2026-03-16

## 1) Ветки и дельта

- `origin/main` указывает на commit `93f0259`.
- `origin/work` указывает на commit `6916482`.
- Между `main -> work`: `43` изменённых файлов, `+5789/-40` строк.
- Локальная ветка `work` синхронизирована fast-forward до `origin/work`.

Ключевые направления изменений в `work` относительно `main`:
- Добавлены модули **companion** (session/profile/facts/proposals/traces).
- Добавлен **voice control-plane** (session lifecycle, mic verify, go/no-go).
- Добавлен **retrieval контур** (search API, job queue, worker metrics/control/run-once).
- Добавлены **online tools** (web search + download, feature-flag).
- Усилены Termux-скрипты и end-to-end проверки.
- Существенно расширены backend тесты.

## 2) Текущая архитектура (снимок work)

### Backend (FastAPI)
- Основной app инициализирует состояния: memory engine, task runner, companion/voice state, retrieval jobs + background worker.
- Подключены роуты:
  - `/api/chat`
  - `/api/memory`
  - `/api/books`
  - `/api/sandbox`
  - `/api/tasks`
  - `/api/companion`
  - `/api/voice`
  - `/api/retrieval`
  - `/api/online`

### Frontend (React + Vite)
- Страницы: Chat, Memory, Sandbox, Tasks, Companion, Voice.
- API-клиент расширен под companion/voice/retrieval/online функциональность.

### Ops/Termux
- Есть install/deploy/start/stop/diagnose/full-smoke/integrity сценарии.
- Добавлены спец-скрипты:
  - проверка сетевых утечек,
  - очистка шумовой памяти,
  - voice readiness-check,
  - единый full end-to-end check.

## 3) Что ассистент уже умеет (по коду work)

1. Локальный чат с KoboldCpp + контекст памяти + optional web-контекст по префиксам `web:`/`search:`.
2. Outcome-based память: добавление, поиск, удаление, статистика, feedback-петля.
3. Загрузка книг/PDF и извлечение контента, включая OCR fallback цепочку.
4. Task pipeline с риск-классификацией, approval-gate, fingerprint invalidation, retry policy, event-аудитом и SQLite-персистом.
5. Sandbox выполнение кода с Android/Termux-совместимыми ограничениями.
6. Companion API:
   - режимы рассуждения/челленджа/инициативы,
   - профиль отношений и факты,
   - proposal lifecycle,
   - explainability traces.
7. Voice API:
   - старт/стоп voice session,
   - health/metrics,
   - mic verification,
   - go/no-go оценка готовности.
8. Retrieval API:
   - unified search,
   - index jobs lifecycle,
   - worker metrics/control/run-once.
9. Online tools (по feature flag): web search и download в локальную папку.

## 4) Полный инвентарь tracked файлов (work)

Всего tracked файлов: **90**.

### Корень
- `.github/workflows/backend-tests.yml`
- `.gitignore`
- `LICENSE`
- `README.md`
- `pyproject.toml`

### backend
- `backend/__init__.py`
- `backend/core/__init__.py`
- `backend/core/main.py`
- `backend/core/routers/__init__.py`
- `backend/core/routers/books.py`
- `backend/core/routers/chat.py`
- `backend/core/routers/companion.py`
- `backend/core/routers/memory.py`
- `backend/core/routers/online.py`
- `backend/core/routers/retrieval.py`
- `backend/core/routers/sandbox.py`
- `backend/core/routers/tasks.py`
- `backend/core/routers/voice.py`
- `backend/core/services/__init__.py`
- `backend/core/services/companion_memory.py`
- `backend/core/services/companion_state.py`
- `backend/core/services/embeddings_client.py`
- `backend/core/services/kobold_client.py`
- `backend/core/services/memory_engine.py`
- `backend/core/services/online_tools.py`
- `backend/core/services/retrieval.py`
- `backend/core/services/retrieval_jobs.py`
- `backend/core/services/task_planner.py`
- `backend/core/services/task_runner.py`
- `backend/core/services/voice_state.py`
- `backend/core/tests/conftest.py`
- `backend/core/tests/test_books_router.py`
- `backend/core/tests/test_chat_router.py`
- `backend/core/tests/test_companion_router.py`
- `backend/core/tests/test_companion_state_trace.py`
- `backend/core/tests/test_full_system_check.py`
- `backend/core/tests/test_online_router.py`
- `backend/core/tests/test_retrieval_jobs_state.py`
- `backend/core/tests/test_retrieval_router.py`
- `backend/core/tests/test_retrieval_week1.py`
- `backend/core/tests/test_retrieval_worker.py`
- `backend/core/tests/test_sandbox_termux_detection.py`
- `backend/core/tests/test_task_planner.py`
- `backend/core/tests/test_task_runner_and_tasks_api.py`
- `backend/core/tests/test_voice_router.py`
- `backend/embeddings/main.py`
- `backend/embeddings/requirements-lite-termux.txt`
- `backend/embeddings/requirements.txt`
- `backend/sandbox/requirements-termux.txt`
- `backend/sandbox/requirements.txt`

### docs
- `docs/api.md`
- `docs/architecture.md`
- `docs/companion-implementation-plan.md`
- `docs/companion-vision.md`
- `docs/expert-opinion.md`
- `docs/handoff-v2.md`
- `docs/installation.md`
- `docs/multimodal-rag-week1.md`
- `docs/multimodal-rag-week2.md`
- `docs/multimodal-rag-week3.md`
- `docs/repo-audit-overview.md`
- `docs/repository-analysis-2026-03-16.md`

### frontend
- `frontend/index.html`
- `frontend/package.json`
- `frontend/tsconfig.json`
- `frontend/tsconfig.node.json`
- `frontend/vite.config.ts`
- `frontend/src/App.tsx`
- `frontend/src/index.css`
- `frontend/src/main.tsx`
- `frontend/src/api/client.ts`
- `frontend/src/components/Layout.tsx`
- `frontend/src/pages/ChatPage.tsx`
- `frontend/src/pages/CompanionPage.tsx`
- `frontend/src/pages/MemoryPage.tsx`
- `frontend/src/pages/SandboxPage.tsx`
- `frontend/src/pages/TasksPage.tsx`
- `frontend/src/pages/VoicePage.tsx`

### scripts
- `scripts/full-end-to-end-check.sh`

### termux
- `termux/check-no-internet-leak.sh`
- `termux/cleanup-memory-noise.sh`
- `termux/constraints-termux.txt`
- `termux/deploy.sh`
- `termux/diagnose.sh`
- `termux/full-smoke.sh`
- `termux/setup.sh`
- `termux/start-kobold.sh`
- `termux/start-services.sh`
- `termux/stop-services.sh`
- `termux/verify-repo-integrity.sh`
- `termux/voice-readiness-check.sh`

## 5) Выводы

- Ветка `work` значительно ушла вперёд по функциональности относительно `main` и уже содержит расширенную платформу ассистента (companion + voice + retrieval + online).
- По backend-тестам состояние стабильное (полный локальный пакет тестов проходит).
- По процессу синхронизации ветки: после fast-forward локальный `work` совпадает с `origin/work`.
- На текущем этапе проект покрывает почти весь заявленный концепт локального Android-ассистента; ключевые open-item'ы остаются в плоскости on-device прогонов deploy/full-smoke и валидации OCR-окружения на конкретном устройстве.
