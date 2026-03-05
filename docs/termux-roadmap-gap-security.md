# Roampal Android: MVP→Beta→Stable + Gap-анализ + Security/Ops (Termux)

> Метод: skeptical review. Все утверждения опираются на код/скрипты и командные проверки (`git status`, `git rev-parse`, `py_compile`, `npm run build`). Неподтвержденные гипотезы помечены как **не подтверждено**.

## 0) Верифицированный baseline

- Ветка: `work`
- SHA: `b45d3d4ff336ebeab0032361bda5a70b1c7d665a`
- Рабочее дерево перед изменениями: чистое

Команда:

```bash
git status --short --branch && git rev-parse --abbrev-ref HEAD && git rev-parse HEAD
```

## 1) Целевая архитектура и текущий gap (plan → execute → observe → retry → memory → policy)

### Что подтверждено кодом

1. **execute + retry + partial policy есть в TaskRunner**:
   - Статусы `PENDING/RUNNING/RETRYING/SUCCESS/FAILED/NEEDS_APPROVAL`.
   - Классификация ошибок (`permission/command/transient/runtime`).
   - `DANGEROUS_PATTERNS` и авто-блок до approve.
   - Аудит в `backend/core/logs/task_audit.log` и file persistence `tasks_state.json`.

2. **memory есть и работает в 2 режимах**:
   - Chroma persistent + fallback in-memory.
   - Outcome learning через `record_outcome`.

3. **observe частично есть**:
   - События задачи (`TaskEvent`) и статусные endpoint-ы.
   - Termux-диагностика (`termux/diagnose.sh`) и full smoke (`termux/full-smoke.sh`).

4. **ops-автоматизация есть**:
   - setup/deploy/start/stop/full-smoke.

### Что отсутствует или нестабильно (подтвержденные gaps)

1. **plan слой отсутствует как отдельный компонент**:
   - `goal` в `/api/tasks/{id}/run` исполняется напрямую как bash, без planner/tool routing.

2. **policy неполная**:
   - Есть только regex-детектор опасных команд.
   - Нет уровней действий `safe/sensitive/dangerous` как first-class модели.
   - Нет журнала решений approve с actor/device/session контекстом.

3. **sandbox изоляция ограниченная**:
   - Выполнение через `asyncio.create_subprocess_exec` с `cwd=workspace`, но без OS-level sandbox boundary (cgroups/seccomp/ns) в коде core.
   - Это acceptable для MVP в Termux, но риск для `dangerous` действий.

4. **persistency задач MVP-уровня**:
   - `tasks_state.json` file-based, без схемы, миграций, конкурентной записи/транзакций.

5. **SLO/метрики не закреплены в API**:
   - Нет встроенного экспорта success rate/latency/retry rate/crash-free.

## 2) Консолидированный roadmap (A+B+C)

## Stage 1 — MVP Hardening (локально-надежный single-user)

### Обязательные функции MVP

- Task lifecycle API + run/approve + retry (уже есть, стабилизировать).
- Memory add/search/outcome-feedback (уже есть, покрыть тестами).
- Sandbox execute с timeout (уже есть, усилить ограничениями).
- Termux deploy/start/full-smoke/diagnose (уже есть).
- Базовый policy gate: regex + manual approval (уже есть).

### Критерии готовности MVP

- `full-smoke.sh` проходит 5 прогонов подряд без ручных фиксов.
- `/api/tasks` сценарии (safe success, dangerous needs_approval, retry/fail) покрыты автотестами.
- Метрики (минимум):
  - task success rate >= 85% для safe smoke-набора,
  - p95 run latency <= 8s для `echo/ls/cat` класса,
  - retry rate <= 20% на smoke-наборе,
  - crash-free run >= 24h на idle+periodic smoke.

### Риски + mitigation

- Риск: false negative в dangerous regex → добавить denylist команд + обязательный approve для shell redirections на системные пути.
- Риск: corruption `tasks_state.json` → atomic write + backup rotate.
- Риск: runaway process → обязательный kill process group при timeout.

---

## Stage 2 — Beta (управляемая автономность)

### Изменения

- Ввести planner abstraction:
  - `task.goal` -> `plan` (structured steps),
  - шаги исполняются tool-router (sandbox/book/memory/chat).
- Ввести Policy Engine v1:
  - action level: `safe/sensitive/dangerous`,
  - per-level execution rules,
  - explicit approval token с TTL.
- Заменить file persistence на SQLite (+миграции Alembic/ручные SQL).
- Добавить telemetry endpoints `/api/metrics/summary`.

### Критерии готовности Beta

- 0 data-loss в задачах при restart/kill core.
- deterministic replay task history из SQLite.
- approval flow подтвержден e2e: create→needs_approval→approve→run.
- p95 latency на типовых task-пайплайнах <= 12s.

### Риски + mitigation

- Риск: planner hallucination -> strict schema + command allowlist templates.
- Риск: regression UI задач -> contract tests для `tasksAPI` + e2e smoke.

---

## Stage 3 — Stable (операционно безопасный телефонный ассистент)

### Изменения

- Policy Engine v2:
  - контекстные правила (время, сеть, path scope),
  - авто-rollback действий по idempotent hooks.
- Автовосстановление:
  - supervisor script + health watchdog,
  - restart backoff + circuit breaker для flaky сервисов.
- Полный audit trail:
  - action_id, parent_task_id, actor, decision, stdout/stderr hash.
- Надежность релизов:
  - phased rollout (canary branch),
  - быстрый rollback на предыдущий commit + previous venv/node_modules snapshot.

### Критерии готовности Stable

- crash-free >= 7 дней при ежедневном smoke.
- rollback <= 5 минут (доказано runbook-репетицией).
- security incidents (dangerous без approve) = 0 в acceptance тестах.

## 3) Порядок релизов и rollback-план

1. **Release R1 (MVP hardening)**: tests + atomic persistence + timeout killpg.
2. **Release R2 (Beta planner/policy/sqlite)**: planner + policy levels + sqlite.
3. **Release R3 (Stable ops/security)**: watchdog + audit v2 + canary rollout.

Rollback (единый):

- Шаг 1: `termux/stop-services.sh`
- Шаг 2: `git checkout <prev_tag_or_sha> && git reset --hard <prev_tag_or_sha>`
- Шаг 3: восстановить `data/` snapshot и `backend/core/logs/tasks_state.json`/SQLite backup
- Шаг 4: `termux/start-services.sh`
- Шаг 5: `termux/full-smoke.sh`

## 4) Технический план задач (с приоритетами, владельцами, зависимостями, DoD, рисками)

| ID | Задача | Приоритет | Владелец | Зависимости | DoD | Риск |
|---|---|---|---|---|---|---|
| T1 | Добавить action levels (`safe/sensitive/dangerous`) и policy evaluator | P0 | Backend | Нет | API возвращает level, `dangerous` всегда `NEEDS_APPROVAL`, есть unit tests | Неполная классификация команд |
| T2 | Перевести persistence задач на SQLite | P0 | Backend | T1 (желательно) | create/list/get/approve/run читают/пишут SQLite, restart-safe integration test | Миграции/совместимость |
| T3 | Planner v1 (goal→structured steps) + tool-router | P0 | Backend | T1/T2 | Для минимум 3 шаблонов goal создается и исполняется plan, trace в audit | Ошибки маршрутизации |
| T4 | Расширить аудит: decision log + actor/session/device id | P1 | Backend/DevOps | T1 | У каждого task event есть связанный decision/audit id | Рост объема логов |
| T5 | Frontend Tasks UX: statuses, approval badge, retry visibility, filter | P1 | Frontend | T1/T3 | UI отражает уровень риска и причины блокировки | UI regression |
| T6 | Метрики качества (`success_rate`, `p95_latency`, `retry_rate`, `crash_free_hours`) | P1 | Backend/DevOps | T2 | `/api/metrics/summary` + smoke assertion thresholds | Ложные тревоги |
| T7 | Termux watchdog + recovery runbook automation | P1 | DevOps | T6 | watchdog рестартует упавший сервис, логирует событие, есть recovery smoke | Флаппинг рестартов |
| T8 | Регрессионный тестовый минимум | P0 | QA/Backend | T1-T3 | Набор тестов ниже включен в CI/local smoke | Длительность прогона |

## 5) Минимальный набор тестов против регрессий

1. **Backend unit**
   - `TaskRunner.requires_approval` dangerous patterns.
   - `classify_error` mapping.
   - state transitions (`PENDING→RUNNING→SUCCESS/RETRYING/FAILED/NEEDS_APPROVAL`).

2. **Backend integration (FastAPI TestClient/pytest)**
   - `/api/tasks` create/list/get.
   - dangerous goal требует approve.
   - approve->run success.
   - restart persistence (load/save).

3. **Memory integration**
   - add/search/record_outcome/delete threshold (< -0.5).

4. **Termux smoke**
   - existing `termux/full-smoke.sh` + 5x loop wrapper.

5. **Frontend smoke**
   - `npm run build` + basic tasks page render test.

## 6) Termux runbook (deploy/update/smoke/recovery)

### Deploy/Update

```bash
cd ~/roampal-android
bash termux/deploy.sh work
```

### Smoke

```bash
cd ~/roampal-android
bash termux/full-smoke.sh
```

### Recovery (ручной)

```bash
cd ~/roampal-android
bash termux/diagnose.sh
bash termux/stop-services.sh
bash termux/start-services.sh
bash termux/full-smoke.sh
```

### Recovery (rollback)

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

