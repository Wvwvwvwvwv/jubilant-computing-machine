# Companion Implementation Plan (пунктами): API, БД, Voice Go/No-Go

Дата: 2026-03-13
Связанный vision-документ: `docs/companion-vision.md`

## 0) Границы и проверяемые допущения

- Цель: реализовать «мыслящего союзника» как инженерную систему, а не как абстрактную метафору.
- Базовый принцип: каждое «личностное» поведение должно иметь наблюдаемый сигнал (поле API, запись в БД, событие аудита).
- Все предложения ниже локально-first (без обязательных облачных сервисов).

---

## 1) План реализации по пунктам (этапы)

### Этап A — Контракт поведения (STABLE/WILD + право спорить)

1. Ввести session-политику рассуждения:
   - `reasoning_mode`: `stable | wild`
   - `challenge_mode`: `off | balanced | strict`
2. Добавить единый internal response-shape для аналитики:
   - `known_facts[]`, `hypotheses[]`, `unknowns[]`, `alternatives[]`, `recommendation`, `confidence`.
3. Логировать в audit-событиях:
   - какой режим был применен,
   - была ли активная контр-позиция,
   - какие uncertainty-маркеры были возвращены.

### Этап B — Relationship Memory (память отношений)

1. Ввести отдельный слой памяти отношений (не смешивать с общей memory-коллекцией).
2. Поддержать редактирование профиля пользователем + историю изменений.
3. В каждом ответе давать trace: какие relationship-данные реально использовались.

### Этап C — Инициатива без навязчивости

1. Ввести инициативные подсказки как отдельную сущность `proposals`.
2. Каждое предложение должно иметь:
   - `reason`, `expected_value`, `risk_level`, `stop_condition`.
3. Ограничить частоту инициативы policy-правилом (например, не чаще 1 инициативы на N сообщений без явного запроса).

### Этап D — Локальный голос (MVP)

1. MVP: push-to-talk (half-duplex).
2. Затем: full-duplex с барж-ином и interruption policy.
3. Голосовые действия, влияющие на систему, всегда проходят существующий approval/risk gate.

---

## 2) API-контракты (v1)

## 2.1 Session / Persona

### `GET /api/companion/session`

Ответ:
```json
{
  "session_id": "sess_123",
  "reasoning_mode": "stable",
  "challenge_mode": "balanced",
  "initiative_mode": "adaptive",
  "voice_mode": "off"
}
```

### `PATCH /api/companion/session`

Запрос:
```json
{
  "reasoning_mode": "wild",
  "challenge_mode": "strict",
  "initiative_mode": "adaptive",
  "voice_mode": "ptt"
}
```

Правила валидации:
- `reasoning_mode ∈ {stable,wild}`
- `challenge_mode ∈ {off,balanced,strict}`
- `initiative_mode ∈ {off,adaptive,proactive}`
- `voice_mode ∈ {off,ptt,duplex}`

---

## 2.2 Relationship Memory

### `GET /api/companion/relationship-profile`

Ответ:
```json
{
  "user_id": "local_user",
  "style": {
    "verbosity": "medium",
    "tone": "direct",
    "language": "ru"
  },
  "debate_preferences": {
    "allow_disagreement": true,
    "strictness": "balanced"
  },
  "initiative_preferences": {
    "allow_proactive_suggestions": true,
    "max_unsolicited_per_hour": 3
  },
  "updated_at": 1730000000
}
```

### `PATCH /api/companion/relationship-profile`

Запрос (partial update):
```json
{
  "style": {"verbosity": "high"},
  "debate_preferences": {"strictness": "strict"}
}
```

### `POST /api/companion/relationship-facts`

Запрос:
```json
{
  "fact": "Пользователь предпочитает сначала риски, потом идеи",
  "source": {
    "type": "chat_message",
    "ref_id": "msg_abc"
  },
  "confidence": 0.82,
  "ttl_days": 120
}
```

### `GET /api/companion/relationship-facts?query=...&limit=...`

Ответ:
```json
{
  "items": [
    {
      "fact_id": "rf_1",
      "fact": "Пользователь предпочитает сначала риски, потом идеи",
      "confidence": 0.82,
      "source": {"type": "chat_message", "ref_id": "msg_abc"},
      "status": "active"
    }
  ],
  "count": 1
}
```

### `POST /api/companion/relationship-facts/{fact_id}/invalidate`

Назначение: ручное опровержение/устаревание факта.

---

## 2.3 Explainability / Trace

### `GET /api/companion/last-response-trace`

Ответ:
```json
{
  "response_id": "resp_42",
  "reasoning_mode": "stable",
  "challenge_mode": "balanced",
  "relationship_used": ["rf_1", "rf_7"],
  "uncertainty_markers": ["insufficient_data"],
  "counter_position_used": true,
  "confidence": 0.71
}
```

---

## 2.4 Voice API (локальный backend control-plane)

### `POST /api/voice/session/start`

Запрос:
```json
{
  "mode": "ptt",
  "stt_engine": "local_whisper_cpp",
  "tts_engine": "local_piper"
}
```

Ответ:
```json
{
  "voice_session_id": "vs_001",
  "mode": "ptt",
  "status": "ready"
}
```

### `POST /api/voice/session/{id}/stop`

### `GET /api/voice/session/{id}/health`

Ответ:
```json
{
  "status": "healthy",
  "input_device": "ok",
  "stt": "ok",
  "tts": "ok",
  "latency_p95_ms": 1700,
  "xruns_per_min": 0
}
```

---

## 3) Схема БД: Relationship Memory (SQLite)

```sql
CREATE TABLE IF NOT EXISTS relationship_profiles (
  user_id TEXT PRIMARY KEY,
  verbosity TEXT NOT NULL DEFAULT 'medium',
  tone TEXT NOT NULL DEFAULT 'direct',
  language TEXT NOT NULL DEFAULT 'ru',
  allow_disagreement INTEGER NOT NULL DEFAULT 1,
  disagreement_strictness TEXT NOT NULL DEFAULT 'balanced',
  allow_proactive_suggestions INTEGER NOT NULL DEFAULT 1,
  max_unsolicited_per_hour INTEGER NOT NULL DEFAULT 3,
  created_at REAL NOT NULL,
  updated_at REAL NOT NULL,
  version INTEGER NOT NULL DEFAULT 1
);

CREATE TABLE IF NOT EXISTS relationship_facts (
  fact_id TEXT PRIMARY KEY,
  user_id TEXT NOT NULL,
  fact TEXT NOT NULL,
  confidence REAL NOT NULL CHECK (confidence >= 0.0 AND confidence <= 1.0),
  source_type TEXT NOT NULL,
  source_ref_id TEXT,
  status TEXT NOT NULL DEFAULT 'active', -- active|invalidated|expired
  ttl_days INTEGER,
  created_at REAL NOT NULL,
  updated_at REAL NOT NULL,
  FOREIGN KEY(user_id) REFERENCES relationship_profiles(user_id)
);

CREATE TABLE IF NOT EXISTS relationship_fact_events (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  fact_id TEXT NOT NULL,
  event_kind TEXT NOT NULL, -- created|updated|invalidated|expired
  payload_json TEXT NOT NULL,
  ts REAL NOT NULL,
  FOREIGN KEY(fact_id) REFERENCES relationship_facts(fact_id)
);

CREATE INDEX IF NOT EXISTS idx_relationship_facts_user_status
  ON relationship_facts(user_id, status);

CREATE INDEX IF NOT EXISTS idx_relationship_fact_events_fact
  ON relationship_fact_events(fact_id, id);
```

Примечания:
- `version` в `relationship_profiles` нужен для optimistic concurrency.
- `status` в facts отделяет «забыто» от «опровергнуто».
- Событийная таблица нужна для объяснимости и аудита «роста личности».

---

## 4) Go/No-Go критерии по голосу

## 4.1 Go (разрешить rollout)

MVP `ptt` допускается к релизу, если все условия выполнены:
1. `latency_p95_ms <= 2500` на целевом устройстве (15+ коротких реплик).
2. `session_health` стабильно `healthy` минимум 30 минут прогона.
3. Crash-free rate voice-процесса >= 99% за 100 сессий.
4. Нет обхода approval-policy при voice-командах действия.
5. Субъективная оценка пользователя >= 4/5 по критерию «ощущение живого присутствия» (минимум 20 сессий).

## 4.2 No-Go (блокировать rollout)

Любое из условий — стоп:
1. `latency_p95_ms > 3000` устойчиво в 2+ независимых прогонах.
2. Потеря/дублирование аудио-реплик > 2%.
3. Есть хотя бы один кейс выполнения опасной команды из voice без корректного approval.
4. Падения STT/TTS процесса > 1% сессий.
5. Пользовательские оценки < 3/5 по двум неделям подряд.

---

## 5) Метрики зрелости «союзника» (не только голоса)

- `useful_disagreement_rate`: доля возражений, признанных полезными.
- `false_confidence_rate`: доля ответов с завышенной уверенностью, позже опровергнутых.
- `initiative_accept_rate`: доля инициативных предложений, которые пользователь принял.
- `trace_completeness`: доля ответов с корректным explainability trace.
- `relationship_drift_errors`: число случаев, когда assistant использовал устаревший/invalidated факт.

---

## 6) Минимальный план проверки (Definition of Done для MVP)

1. Backend:
   - API `/api/companion/session` + `/relationship-profile` + `/relationship-facts` реализованы.
   - Миграция БД создаёт таблицы relationship memory без регрессий tasks DB.
2. Frontend:
   - Тумблеры STABLE/WILD и challenge-mode доступны и сохраняются.
   - Есть UI просмотра/редактирования relationship profile.
3. Observability:
   - `last-response-trace` показывает, какие relation-факты были использованы.
4. Voice:
   - PTT сценарий проходит Go-критерии.

