# Репозиторный аудит (main vs work) — 2026-03-16

## 1) Статус веток и дельта

- `origin/main` → `93f0259`.
- `origin/work` → `35d7d74`.
- `work` опережает `main` на **57 commit**.
- Общая дельта `main..work`: **44 files changed, +5969 / -40**.
- Локальный `HEAD` синхронизирован с `origin/work`.

Ключевые направления изменений в `work` относительно `main`:
- Добавлены модули **companion** (session/profile/facts/proposals/traces).
- Добавлен **voice control-plane** (session lifecycle, mic verification, go/no-go).
- Добавлен **retrieval контур** (поиск, очередь индексации, worker metrics/control/run-once).
- Добавлены **online tools** (web search + download, feature-flag).
- Существенно усилены Termux/ops сценарии (diagnose, readiness, integrity, e2e checks).
- Расширен набор backend-тестов.

## 2) Архитектура (снимок branch `work`)

### Backend (FastAPI)
Единый orchestrator поднимает и держит в `app.state`:
- `MemoryEngine`
- `TaskRunner` (SQLite persistence + event audit)
- `CompanionState`
- `CompanionMemory`
- `VoiceState`
- `RetrievalJobState`
- фоновый worker для обработки retrieval jobs

Подключённые API-префиксы:
- `/api/chat`
- `/api/memory`
- `/api/books`
- `/api/sandbox`
- `/api/tasks`
- `/api/companion`
- `/api/voice`
- `/api/retrieval`
- `/api/online`

### Frontend (React + Vite + TS)
В UI доступны страницы:
- Chat
- Memory
- Sandbox
- Tasks
- Companion
- Voice

### Ops/Termux
Есть полный набор скриптов lifecycle и диагностики:
- `setup/deploy/start/stop/diagnose/full-smoke`
- `verify-repo-integrity.sh`
- `voice-readiness-check.sh`
- `check-no-internet-leak.sh`
- `cleanup-memory-noise.sh`
- `scripts/full-end-to-end-check.sh`

## 3) Что ассистент уже умеет на текущем этапе

1. **Локальный чат с LLM** через KoboldCpp с памятью и компактной инъекцией контекста.
2. **Companion-политики поведения**: STABLE/WILD + challenge-mode с trace explainability.
3. **Память отношений**: facts/profile и учёт в генерации ответа.
4. **Outcome-based memory loop**: add/search/delete/stats/feedback.
5. **Книги/PDF ingestion** с OCR fallback-путём.
6. **Task execution pipeline**: risk-level, approval gate, fingerprint invalidation, retry policy, event-аудит.
7. **Sandbox execution** с Termux/Android-aware ограничениями.
8. **Voice control-plane API**: start/stop, health, metrics, microphone verify, go/no-go.
9. **Retrieval API**: unified search + индексирующие jobs + фоновый worker и управление им.
10. **Online tools (feature-flag)**: web search + controlled download в локальную директорию.

## 4) Что изменилось относительно `main` (смысловой итог)

`work` фактически превратился из «ядра чат+память+sandbox» в более полный локальный assistant-platform слой:
- Added: companion subsystem.
- Added: voice orchestration layer.
- Added: retrieval jobs lifecycle + worker.
- Added: online tools integration.
- Added: дополнительные on-device readiness/integrity сценарии.
- Added: существенно более широкое тестовое покрытие backend API.

## 5) Полный инвентарь tracked-файлов в `work`

Текущий tracked inventory: **91 файл**.

### root
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

## 6) Выводы (для чата)

- `work` — текущий source-of-truth: там уже собран «расширенный» локальный ассистент с companion/voice/retrieval/online подсистемами.
- Архитектурно проект перешёл от MVP к платформенному слою с наблюдаемостью, управляемыми state-машинами и ops-скриптами для on-device эксплуатации.
- По коду и тестам backend состояние стабильное; риски остаются в runtime-плоскости конкретного устройства (Termux Python 3.13/ocr/toolchain).
- Практический следующий шаг: on-device прогон `termux/deploy.sh work` + `termux/full-smoke.sh` с приложением полного лога.
