# AI Voice Agent — SaaS для бизнеса в Узбекистане

Универсальный голосовой AI-агент: принимает и совершает звонки, записывает
клиентов на услуги/курсы через календарь/CRM, ведёт продающий диалог. Один
движок, три готовых профиля-сценария:

- 🎓 **courses** — учебный центр (консультация + запись на пробный урок)
- 💇 **salon** — салон красоты (запись на приём к мастеру)
- 🛒 **sales** — отдел продаж (холодные звонки, квалификация лида)

## Документация

- [`docs/business-plan.md`](docs/business-plan.md) — бизнес-план, сегменты, тарифы, go-to-market, roadmap.
- [`docs/architecture.md`](docs/architecture.md) — техническая архитектура, выбор STT/TTS/телефонии.
- [`docs/compliance.md`](docs/compliance.md) — юридические требования в Узбекистане (персональные данные, запись звонков).

## Статус реализации (MVP, Неделя 1-2 из roadmap)

Реализовано и покрыто тестами:
- ✅ Диалоговый движок (`app/agent/dialogue.py`) — реальный вызов Claude API
  с function calling (tool use loop) по трём профилям.
- ✅ Реестр функций (`app/agent/functions.py`) — связывает функции из
  YAML-профилей с интеграциями (календарь, CRM) и базой знаний тенанта.
- ✅ STT/TTS (`app/voice_pipeline/stt.py`, `tts.py`) — рабочая интеграция с
  Yandex SpeechKit REST API (RU/UZ).
- ✅ Google Calendar (`app/integrations/calendar.py`) — свободные слоты,
  запись/перенос/отмена приёма через Service Account.
- ✅ CRM (`app/integrations/crm.py`) — amoCRM и Bitrix24, создание лида и
  обновление статуса.
- ✅ БД (`app/storage/`) — модели тенантов/звонков/броней/лидов, SQLite для
  разработки, готово к переключению на Postgres в Узбекистане.
- ✅ FastAPI-приложение (`app/main.py`) с `/dialogue/text` — тестовый вход в
  диалоговый движок в обход STT/TTS/телефонии (см. "Быстрая проверка" ниже).

Ещё не реализовано (следующие этапы по `docs/business-plan.md`):
- ⏳ Реальная интеграция с телефонией (`app/telephony/asterisk_client.py`,
  `app/voice_pipeline/orchestrator.py`) — нужен настоящий SIP-транк/номер и
  Asterisk-сервер, поэтому оставлена как интерфейс с `NotImplementedError`.
- ⏳ Потоковое (streaming) распознавание речи с partial-результатами —
  сейчас STT работает по буферизованному REST-запросу (см. docstring в
  `stt.py`), что проще, но добавляет задержку на всю длину реплики.

## Структура проекта

```
backend/
  app/
    telephony/        # интеграция с SIP/PBX (Asterisk ARI) — каркас, ждёт реального номера
    voice_pipeline/    # STT/TTS (рабочая реализация) + orchestrator (каркас)
    agent/
      profiles/         # courses.yaml, salon.yaml, sales.yaml — сценарии по вертикали
      knowledge_data/    # demo-*.yaml — тестовые базы знаний тенантов (услуги/курсы/FAQ)
      knowledge.py        # TenantKnowledgeBase — база знаний тенанта
      functions.py         # FunctionRegistry — схемы инструментов + диспетчер вызовов
      dialogue.py           # диалоговый менеджер (Claude API + function calling)
    integrations/       # Google Calendar, amoCRM/Bitrix24 — рабочая реализация
    storage/            # модели БД + engine/session (db.py)
    providers.py         # фабрики провайдеров из конфигурации (.env)
    config.py             # настройки приложения (pydantic-settings)
    main.py                # FastAPI приложение, /dialogue/text, /api/tenants
  scripts/
    init_db.py           # создать таблицы локальной БД
    echo_test.py          # эхо-тест STT->TTS на WAV-файле (нужны реальные ключи)
  tests/                  # pytest + respx/unittest.mock, без реальных API-ключей
  requirements.txt
  requirements-dev.txt
  .env.example
  pytest.ini
```

## Запуск (локально, для разработки)

```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt
cp .env.example .env  # заполнить ключи API (для /dialogue/text нужен минимум ANTHROPIC_API_KEY)
python scripts/init_db.py  # создать таблицы SQLite (можно пропустить — создаются автоматически при старте)
uvicorn app.main:app --reload
```

`GET /health` должен вернуть `{"status": "ok"}`.

### Быстрая проверка диалогового движка (без телефонии)

```bash
curl -X POST http://127.0.0.1:8000/api/tenants \
  -H "Content-Type: application/json" \
  -d '{"name": "Demo Salon", "business_profile": "salon", "phone_number": "+998901234567"}'

curl -X POST http://127.0.0.1:8000/dialogue/text \
  -H "Content-Type: application/json" \
  -d '{"client_id": "test-1", "business_profile": "salon", "language": "ru", "text": "Хочу записаться на стрижку"}'
```

Без `ANTHROPIC_API_KEY` работает только быстрый путь эскалации (фраза вроде
"позови человека"); полноценный диалог с function calling требует реального
ключа Claude API.

### Тесты

```bash
cd backend && pytest
```

Все тесты используют mock (respx для HTTP, unittest.mock для Google Calendar
API) — реальные ключи API не нужны.
