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

## Структура проекта

```
backend/
  app/
    telephony/       # интеграция с SIP/PBX (Asterisk ARI)
    voice_pipeline/  # STT -> LLM -> TTS оркестрация одного звонка
    agent/
      profiles/      # courses.yaml, salon.yaml, sales.yaml — сценарии по вертикали
      dialogue.py     # диалоговый менеджер (Claude API + function calling)
    integrations/     # Google Calendar, amoCRM/Bitrix24
    storage/          # модели БД: тенанты, звонки, брони, лиды
    main.py           # FastAPI приложение, webhooks
  requirements.txt
  .env.example
```

Это каркас MVP (см. `docs/business-plan.md`, раздел Roadmap): интерфейсы и
структура определены, реализация наполняется по мере разработки.

## Запуск (локально, для разработки)

```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env  # заполнить ключи API
uvicorn app.main:app --reload
```

`GET /health` должен вернуть `{"status": "ok"}`.
