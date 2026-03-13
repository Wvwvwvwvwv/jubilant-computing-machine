# Repo Audit Overview (work)

Дата: 2026-03-13

Этот документ фиксирует обзор текущего состояния кода Roampal Android в ветке `work`.

## 1) Что уже реализовано

- Многосервисная локальная архитектура: KoboldCpp (`:5001`), Core API (`:8000`), Embeddings (`:8001`), Frontend (`:5173`).
- Core API включает роутеры `chat`, `memory`, `books`, `sandbox`, `tasks`.
- Outcome-based memory с fallback на in-memory режим, если ChromaDB недоступна.
- Tasks API с базовой state machine, approval policy по опасным паттернам команд, retry и аудитом.
- Embeddings-сервис имеет деградированный deterministic fallback при недоступной/неподнятой модели.
- Termux-скрипты для setup/deploy/start/stop/smoke/diagnose.

## 2) Расхождения с целевой концепцией

По коду видно, что ряд пунктов уже закрыт частично, но некоторые — в упрощённом MVP-виде:

- Planner в `tasks/run` пока не использует LLM-planner/tool routing: цель запускается как `bash`.
- `books` роутер принимает только `.txt/.md`, пока без PDF/OCR пайплайна в текущем коде.
- Sandbox реализован как изолированный workspace + timeout, но без выраженной seccomp/rlimit/clamav интеграции в этом репозитории.
- Task persistence в текущем состоянии file-based (`tasks_state.json`), без SQLite в текущей ветке.

## 3) Что ассистент уже умеет практически

- Вести чат через локальный KoboldCpp и использовать память как контекст.
- Принимать feedback на ответы и корректировать outcome-score взаимодействий.
- Искать/добавлять/удалять память, получать статистику.
- Загружать и хранить книги в txt/md, просматривать список и удалять.
- Выполнять код в sandbox (python/js/bash) с timeout.
- Создавать, запускать и approve задачи с аудитом событий.
- Работать в degraded-режиме эмбеддингов без падения API.

## 4) Операционные выводы

- Для Android/Termux проект хорошо подготовлен скриптами bootstrap + smoke + diagnose.
- Самые критичные следующие шаги остаются device-level: `termux/deploy.sh work` и `termux/full-smoke.sh` на устройстве с полными логами.
- OCR/PDF функциональность требует отдельного внедрения в код books ingestion (в текущем tree не обнаружена).

