# RFC v3.1 Integration Findings (Roampal Android)

Дата: 2026-03-05  
Подход: skeptical/verified (только подтверждаемое кодом и скриптами репозитория).

## 1) Базовая проверка перед выводами

Проверено командами:

```bash
git status --short --branch
git rev-parse --abbrev-ref HEAD
git rev-parse HEAD
```

На момент анализа:
- branch: `work`
- HEAD: `c6bb472ffd199391c06e38d2bd56a34246d5eff5`

## 2) Что из RFC v3.1 уже частично реализовано

1. **Core orchestrator + модульность** есть:
   - отдельные роуты `chat/memory/books/sandbox/tasks`.
2. **Durable state для tasks** есть в MVP-виде:
   - `tasks_state.json` load/save и аудит `task_audit.log`.
3. **Policy gate (базовый)** есть:
   - dangerous regex + `NEEDS_APPROVAL` + ручной approve.
4. **Outcome memory** есть:
   - score update + auto-delete при низком score.
5. **Termux ops pipeline** есть:
   - `setup/deploy/start/stop/diagnose/full-smoke`.

## 3) Критичные расхождения RFC v3.1 vs текущий код

### P0 gaps

1. **Нет Durable Job Queue в RFC-смысле**
   - есть Tasks API, но нет общей очереди `jobs` с `at-least-once` семантикой для reflection/embed/audit/web.

2. **Нет unified SQLite schema (users/runtime_settings/messages/memory_chunks/vss/jobs/models...)**
   - сейчас persistence разрозненная (json + Chroma/in-memory + file system).

3. **Нет Resource Guard hard-rules** (`battery < 20`, `temp > 100`) на запуск LLM.

4. **Нет Model Registry / Persona Modes (`STABLE/WILD`)**
   - в коде не найдена таблица/слой выбора движка по persona и визуальным триггерам.

5. **Нет Consent-Gated WebPlan pipeline RFC-уровня**
   - отсутствуют сущности `web_plans/web_evidence` и токены approval execution chain.

### P1 gaps

1. **Voice Session как continuous duplex loop** в архитектуре RFC не реализован в backend.
2. **Inbox/OpenLoops/ActiveContract/Judgments** как state stores отсутствуют как first-class persistence.
3. **Idempotency keys** в очереди общего назначения отсутствуют.
4. **Инварианты-аудит job** (`audit_invariants`) отсутствует.

## 4) Риски интеграции RFC (практические)

1. **Слишком большой “big-bang” перенос** (сразу всё из RFC) почти гарантированно сломает текущий termux smoke.
2. **SQLite + vss миграция** в Termux может быть нестабильна без staged rollout и fallback.
3. **Resource Guard** без UX-обвязки может выглядеть как “ассистент сломан”, если не вернуть ясные статус-ответы.
4. **WILD mode** без жёстких policy-invariants может сломать предсказуемость task-потоков.

## 5) Рекомендуемый порядок интеграции (минимум риска)

### Phase 1 (P0): Infrastructure foundation
- Ввести единый SQLite (`companion.db`) и минимальные таблицы: `users`, `runtime_settings`, `conversations`, `messages`, `jobs`.
- Перевести текущие tasks с JSON на SQLite (сохранить API-совместимость).
- Добавить idempotency (`UNIQUE(user_id, idempotency_key)`) для jobs.

**DoD:**
- restart-safe без потери задач;
- текущий `termux/full-smoke.sh` проходит без регрессии.

### Phase 2 (P0): Guardrails + policy core
- Ввести Resource Guard (`battery/temp`) в chat/task execution entrypoints.
- Ввести action levels (`safe/sensitive/dangerous`) вместо regex-only.
- Добавить audit trail решений policy.

**DoD:**
- dangerous path всегда требует approve;
- при battery/temp deny возвращается понятный machine-readable статус.

### Phase 3 (P1): Memory personality stores
- Добавить `active_contract`, `judgments`, `open_loops`, `inbox_items`, `events_log`.
- Добавить `audit_invariants` job и TTL-подчистки.

**DoD:**
- ограничения inbox/open_loops enforce-ятся и проверяются audit job.

### Phase 4 (P1): Web consent pipeline
- Реализовать `web_plans` (proposed/approved/denied/executed) и `web_evidence`.
- Добавить `sandbox_level: restricted/expanded` строго per plan.

**DoD:**
- web execute без approval невозможно;
- evidence связывается с ответами.

### Phase 5 (P2): Persona + model registry + Step3-VL wiring
- Реализовать `models` registry.
- Ввести persona modes `STABLE/WILD` и policy-safe routing.
- Подключить Step3-VL-10B как tool-brain для image/wild explicit triggers.

**DoD:**
- persona тесты проходят: стиль различается, policy/consent не нарушается.

## 6) Минимальный набор проверок перед “интеграция началась”

```bash
# 1) backend syntax sanity
python -m py_compile backend/core/main.py backend/core/routers/tasks.py backend/core/services/task_runner.py

# 2) frontend build sanity
cd frontend && npm run build

# 3) termux e2e (на устройстве)
cd ~/roampal-android && bash termux/full-smoke.sh
```

## 7) Вывод

RFC v3.1 логически цельный и реализуемый, но текущий репозиторий находится на более ранней стадии зрелости.  
Интеграция должна идти по phased-плану (foundation -> guardrails -> state stores -> web consent -> persona/models), иначе высокий риск регрессий в Termux runtime.
