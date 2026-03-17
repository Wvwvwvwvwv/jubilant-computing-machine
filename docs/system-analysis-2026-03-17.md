# Roampal Android: глубокий анализ проекта (ветка `work`) — 2026-03-17

## 1) Философия проекта

Roampal Android строится как **полностью локальная assistant-платформа для Android/Termux**:
- локальный inference через KoboldCpp (без cloud LLM);
- локальная долговременная память с outcome-feedback;
- локальное выполнение задач и кода (sandbox/task-runner);
- локальная эксплуатация и наблюдаемость через Termux-скрипты.

Ключевая идея: не «чат-бот», а **on-device orchestration слой** вокруг LLM, где модель — только один из компонентов, а ценность создают state-машины, память, retrieval и ops-процедуры.

## 2) Архитектурная картина

### 2.1 Backend orchestration (FastAPI)
`backend/core/main.py` поднимает единый runtime-контур в `app.state`:
- `MemoryEngine`
- `TaskRunner` (persistent state)
- `CompanionState`
- `CompanionMemory`
- `VoiceState`
- `RetrievalJobState`
- фоновый retrieval-worker (`asyncio` loop c pause/stop событиями).

Внешний API разбит на доменные роутеры:
`chat`, `memory`, `books`, `sandbox`, `tasks`, `companion`, `voice`, `retrieval`, `online`.

### 2.2 Frontend
React/Vite интерфейс отражает backend домены 1:1 (страницы Chat/Memory/Sandbox/Tasks/Companion/Voice), что снижает когнитивный разрыв между API-моделью и UI.

### 2.3 Ops/Termux
Сильная сторона проекта — инфраструктурная «приземлённость»: setup/deploy/smoke/readiness/integrity скрипты проектируют реальную эксплуатацию на Android, а не только development-сценарий.

## 3) Логика ключевых подсистем

### 3.1 Chat + memory + companion
`chat`-роутер строит ответ по пайплайну:
1. валидация входа;
2. инъекция companion policy (режим reasoning/challenge);
3. инъекция relationship-facts;
4. retrieval релевантного контекста памяти;
5. optional online-context (feature-flag + префикс web/search);
6. optional autonomous execution для actionable-запросов;
7. генерация через Kobold;
8. запись interaction в память;
9. запись explainability trace в companion-state.

Замечание по качеству: инъекция контекста делается компактно (дедуп + cap по количеству), что ограничивает prompt bloat.

### 3.2 Tasks / sandbox
TaskRunner даёт auditable lifecycle (создание/approve/run/result/retry). Sandbox-router обеспечивает controlled execution с timeout и возвратом stdout/stderr.

### 3.3 Retrieval
Есть двухуровневая модель:
- online search API по памяти;
- очередь jobs + worker для фоновой индексации/обработки.

Это даёт фундамент для масштабирования мультимодального retrieval без переписывания chat-пайплайна.

### 3.4 Voice
Voice-подсистема реализована как control-plane (start/stop/health/readiness), что соответствует текущему состоянию проекта: оркестрация важнее «магии ASR/TTS» внутри одного сервиса.

## 4) Проверка на ошибки и устойчивость

Проведённые проверки:
- полный backend unit/integration набор (`74 passed`);
- frontend production build успешен;
- выявлена UX-проблема тестового запуска без `PYTHONPATH=.` (исправлено в этом коммите через pytest-настройку в `pyproject.toml`).

## 5) Риски и технический долг

1. Runtime-зависимости Termux/Android остаются главным фактором риска (OCR/toolchain/system packages).
2. Включённый CORS `*` допустим для локального окружения, но требует жёсткой среды запуска.
3. Online-tools корректно под feature-flag, но operational политика источников/allowlist может быть усилена.

## 6) Инвентарь и назначение файлов (проверено)

Ниже — полный инвентарь файлов проекта, просмотренных и классифицированных по роли.

### Root
- `LICENSE` — лицензия проекта.
- `README.md` — точка входа: запуск, smoke, integrity, deployment.
- `pyproject.toml` — зависимости backend и конфиги инструментов.

### Scripts/Ops
- `scripts/full-end-to-end-check.sh` — единый e2e-check и отчёты в logs.

### Termux lifecycle & diagnostics
- `termux/setup.sh` — первичная установка окружения.
- `termux/deploy.sh` — deployment/update flow под ветку.
- `termux/start-services.sh` — старт core сервисов.
- `termux/stop-services.sh` — остановка сервисов.
- `termux/start-kobold.sh` — запуск LLM engine.
- `termux/full-smoke.sh` — быстрый эксплуатационный smoke.
- `termux/diagnose.sh` — диагностика типовых сбоев.
- `termux/voice-readiness-check.sh` — readiness/go-no-go для voice.
- `termux/check-no-internet-leak.sh` — контроль отсутствия внешних сетевых утечек.
- `termux/verify-repo-integrity.sh` — проверка parity ветки и origin.
- `termux/reset-all-memory.sh` — полный reset данных памяти/companion.
- `termux/constraints-termux.txt` — ограничения pip-пакетов для Termux.

### Backend core
- `backend/core/main.py` — инициализация приложения, state и routers.
- `backend/core/routers/*.py` — API слой доменов chat/memory/books/sandbox/tasks/companion/voice/retrieval/online.
- `backend/core/services/*.py` — бизнес-логика: memory, kobold-client, task-planning/run, companion-state, voice-state, retrieval-jobs, online-tools.
- `backend/core/tests/*.py` — покрытие роутеров/сервисов/worker поведения.

### Embeddings / Sandbox services
- `backend/embeddings/main.py` — сервис эмбеддингов.
- `backend/embeddings/requirements*.txt` — зависимые профили embeddings.
- `backend/sandbox/requirements*.txt` — зависимые профили sandbox.

### Frontend
- `frontend/src/pages/*.tsx` — доменные экраны UI.
- `frontend/src/components/Layout.tsx` — общий shell/layout.
- `frontend/src/api/client.ts` — HTTP слой взаимодействия с backend.
- `frontend/src/App.tsx`, `main.tsx`, `index.css` — bootstrap, routing, стили.
- `frontend/package.json`, `vite.config.ts`, `tsconfig*.json`, `index.html` — сборка и runtime frontend.

### Документация
- `docs/architecture.md`, `docs/api.md`, `docs/installation.md` — базовый контур проекта.
- `docs/handoff-v2.md`, `docs/repo-audit-overview.md` — передача контекста/состояния.
- `docs/companion-vision.md`, `docs/companion-implementation-plan.md` — companion стратегия и roadmap.
- `docs/multimodal-rag-week*.md` — staged plan по retrieval/RAG.
- `docs/expert-opinion.md`, `docs/repository-analysis-2026-03-16.md` — аналитические материалы.

## 7) Итог понимания

Проект уже вышел за рамки MVP: это **локальная assistant-платформа на Android**, где важнейшая инженерная ценность — в orchestration, statefulness, safety-ограничениях и reproducible ops-процедурах.

Если формулировать в одной строке: философия Roampal — **«суверенный on-device AI с управляемым поведением и наблюдаемой эксплуатацией»**.
