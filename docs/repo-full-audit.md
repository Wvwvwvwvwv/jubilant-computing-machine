# Roampal Android — полный технический аудит репозитория (skeptical, verified)

> Цель: не предполагать, а фиксировать только подтверждённое кодом и командами. Где данных не хватает, это отмечено как **не подтверждено**.

## 1) Проверенный baseline git

Команда:

```bash
git status --short --branch && git rev-parse --abbrev-ref HEAD && git rev-parse HEAD
```

Факт на момент аудита:
- branch: `work`
- HEAD: `9dae2bd` (после предыдущего docs-коммита)
- рабочее дерево перед этим коммитом — чистое.

## 2) Что просмотрено (полный охват файлов репозитория)

Проверено содержимое всех tracked файлов из `rg --files`:
- docs (`README.md`, `docs/*.md`)
- backend (`backend/core/**`, `backend/embeddings/**`, `backend/sandbox/requirements*`)
- frontend (`frontend/**`)
- termux scripts (`termux/*.sh`)

Команда инвентаризации:

```bash
rg --files
```

## 3) Подтвержденная архитектура vs фактическая реализация

### 3.1 Core backend (FastAPI)

Подтверждено:
- Core поднимает `memory_engine` и `task_runner` в lifespan, роуты подключены: `chat/memory/books/sandbox/tasks`.
- `/health` есть и возвращает `{"status":"healthy"}`.

Вывод:
- Оркестратор реализован как единый сервис на порту 8000.

### 3.2 Tasks: plan→execute→observe→retry→policy

Подтверждено:
- Есть state machine и аудит событий (`TaskStatus`, `TaskEvent`, `task_audit.log`).
- Есть авто-gate на dangerous паттерны (`DANGEROUS_PATTERNS`) + approve endpoint.
- Есть file persistence (`tasks_state.json`) с save/load на старте/остановке.
- Endpoint `/api/tasks/{task_id}/run` исполняет `goal` напрямую как bash через sandbox execute.

Неподтверждено / gap:
- отдельного planner/tool-router слоя нет.
- нет policy-уровней как first-class модели (safe/sensitive/dangerous), только regex.

### 3.3 Memory

Подтверждено:
- MemoryEngine работает в двух режимах: Chroma persistent или fallback in-memory.
- Есть outcome-based learning (`record_outcome`) с авто-удалением при `score < -0.5`.

Неподтверждено / gap:
- Нет отдельной персистентности fallback-store (после перезапуска теряется).
- Нет dedup/TTL/compaction политики.

### 3.4 Sandbox

Подтверждено:
- Выполнение `python/javascript/bash`, отдельный workspace, timeout.
- Возвращает `stdout/stderr/exit_code/execution_time`.

Неподтверждено / gap:
- нет жёсткой OS-level изоляции в коде core (namespaces/seccomp/cgroups).
- на timeout делается `process.kill()`, но нет явной очистки process-group/child-chain.

### 3.5 Embeddings

Подтверждено:
- Service имеет fallback deterministic embeddings при неуспехе загрузки модели.
- `/health` отражает fallback status.

Неподтверждено / gap:
- Нет явных latency/capacity guardrails и метрик качества эмбеддингов в API summary.

### 3.6 Frontend

Подтверждено:
- Есть страницы Chat/Memory/Sandbox/Tasks и API client для всех endpoint-ов.
- Прокси настроен через `VITE_API_PROXY_TARGET` с fallback `127.0.0.1:8000`.

Неподтверждено / gap:
- Нет e2e/ui smoke тестов в репозитории.
- Нет явного UX-потока для policy levels (потому что backend levels ещё не реализованы).

### 3.7 Termux Operations

Подтверждено:
- Есть setup/deploy/start/stop/diagnose/full-smoke.
- deploy делает git fetch/checkout/reset hard на origin branch и запускает smoke.

Неподтверждено / gap:
- Нет watchdog/supervisor для auto-recovery при runtime падениях после deploy.
- Нет формализованного canary rollout в скриптах.

## 4) Несоответствия документации и кода (важно)

1. В docs архитектуры фигурирует backend/sandbox как отдельный сервис, но runtime по скриптам запускает embeddings + core + kobold + frontend; sandbox-исполнение в core router.
2. API docs частично описывают поведение, но не фиксируют ограничения policy/retry semantics детально.
3. README позиционирует “MCP интеграция”, в просмотренном коде явной реализации MCP endpoint/transport не найдено (**не подтверждено**).

## 5) Риски (операционные и безопасность)

P0:
- Выполнение `task.goal` как shell-команды без planner-шагов и без строгих action levels.
- File-based persistence задач (`tasks_state.json`) подвержен corruption/concurrent-write рискам.

P1:
- Неполная изоляция sandbox-процессов в Termux runtime.
- Отсутствуют системные метрики (`success_rate`, `p95`, `retry_rate`, `crash_free_hours`) в API.

P2:
- Нет автоматического recovery/watchdog.
- Нет CI-пакета интеграционных тестов на tasks/persistence/policy.

## 6) Консолидированный план A+B+C (задачи)

| ID | Задача | Приоритет | Владелец | Зависимости | DoD | Риск |
|---|---|---|---|---|---|---|
| A1 | Ввести action levels (`safe/sensitive/dangerous`) + policy evaluator | P0 | Backend | — | create/run возвращают level и decision, dangerous всегда требует approve | классификация команд может быть неполной |
| A2 | Перенести tasks persistence на SQLite | P0 | Backend | A1 | restart-safe, есть миграция схемы, recovery test | миграционные ошибки |
| A3 | Planner v1 (`goal -> plan steps`) + tool-router | P0 | Backend | A1/A2 | 3 шаблона goals выполняются шагами с audit trace | planner hallucinations |
| A4 | Усилить sandbox runtime safety (kill process group, cleanup, path policy) | P0 | Backend | A1 | timeout гарантированно убивает дочерние процессы | edge-cases shell |
| A5 | Metrics API summary + SLO checks | P1 | Backend/DevOps | A2 | `/api/metrics/summary` + пороги smoke | noisy alerts |
| A6 | Frontend policy UX (уровень риска, причина block, approve flow) | P1 | Frontend | A1/A3 | Tasks UI показывает decision pipeline | UI regressions |
| A7 | Watchdog + auto-restart/backoff/circuit-breaker | P1 | DevOps | A5 | сервисы восстанавливаются без ручного вмешательства | restart flapping |
| A8 | Regression suite (unit+integration+smoke loop) | P0 | QA/Backend | A1-A4 | автопрогон перед релизом | длительность тестов |

## 7) Критерии готовности MVP → Beta → Stable

### MVP (hardening)
- 5/5 проходов `termux/full-smoke.sh` подряд.
- tasks сценарии покрыты тестами: safe success, dangerous needs_approval, retry/fail.
- SLO initial: success>=85%, retry<=20%, p95<=8s на простых bash задачах.

### Beta
- planner/tool-router в проде + policy levels v1.
- SQLite persistence без потерь после restart/kill.
- metrics summary endpoint и daily отчет.

### Stable
- watchdog/recovery и rollback rehearsal <= 5 минут.
- 7-дневный crash-free run при ежедневном smoke.
- 0 обходов policy (dangerous без approve) в acceptance.

## 8) Release order + rollback

Порядок:
1) R1: A1+A2+A4+A8
2) R2: A3+A6+A5
3) R3: A7 + hardening

Rollback:

```bash
cd ~/roampal-android
PREV_SHA=<stable_sha>
bash termux/stop-services.sh
git fetch --all --prune
git checkout "$PREV_SHA"
git reset --hard "$PREV_SHA"
bash termux/start-services.sh
bash termux/full-smoke.sh
```

## 9) “Скопируй-вставь” команды для Termux

### Deploy/update
```bash
cd ~/roampal-android
bash termux/deploy.sh work
```

### Full smoke
```bash
cd ~/roampal-android
bash termux/full-smoke.sh
```

### Diagnose/recovery
```bash
cd ~/roampal-android
bash termux/diagnose.sh
bash termux/stop-services.sh
bash termux/start-services.sh
bash termux/full-smoke.sh
```

### Pre-flight git verification
```bash
cd ~/roampal-android
git status --short --branch
git rev-parse --abbrev-ref HEAD
git rev-parse HEAD
```

## 10) Что не удалось проверить в этой сессии

- Inline comments из GitHub PR в этой среде не были переданы как отдельные данные; обработаны все доступные инструкции и выполнен повторный полный аудит репозитория.
- Запуск e2e на реальном Android-устройстве не выполнялся в контейнере; требуется ваш device output после команд из секции 9.

