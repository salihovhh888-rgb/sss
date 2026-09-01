"""Реестр функций (tool use) для диалогового движка.

Каждый профиль (courses/salon/sales, см. app/agent/profiles/*.yaml)
перечисляет подмножество этих функций в поле ``functions``. FunctionRegistry
собирает JSON-схемы для Claude tool use по этому списку и умеет выполнить
вызов функции, делегируя в интеграции (calendar.py, crm.py) или в базу
знаний тенанта (knowledge.py).
"""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any

from app.agent.knowledge import TenantKnowledgeBase
from app.integrations.calendar import GoogleCalendarClient, TimeSlot
from app.integrations.crm import CrmClient, Lead

# Схемы в формате Anthropic tool use (name/description/input_schema).
FUNCTION_SCHEMAS: dict[str, dict[str, Any]] = {
    "get_services": {
        "name": "get_services",
        "description": "Получить список услуг салона с ценами и длительностью.",
        "input_schema": {"type": "object", "properties": {}},
    },
    "get_courses": {
        "name": "get_courses",
        "description": "Получить список курсов учебного центра с ценами, длительностью и расписанием.",
        "input_schema": {"type": "object", "properties": {}},
    },
    "search_knowledge_base": {
        "name": "search_knowledge_base",
        "description": "Найти ответ на вопрос клиента в базе знаний (FAQ) бизнеса.",
        "input_schema": {
            "type": "object",
            "properties": {"query": {"type": "string", "description": "Вопрос клиента"}},
            "required": ["query"],
        },
    },
    "check_availability": {
        "name": "check_availability",
        "description": "Проверить свободные слоты в календаре на указанную дату.",
        "input_schema": {
            "type": "object",
            "properties": {
                "date": {"type": "string", "description": "Дата в формате YYYY-MM-DD"},
                "duration_minutes": {"type": "integer", "description": "Длительность услуги/урока в минутах"},
            },
            "required": ["date", "duration_minutes"],
        },
    },
    "book_appointment": {
        "name": "book_appointment",
        "description": "Записать клиента на услугу в выбранный слот времени.",
        "input_schema": {
            "type": "object",
            "properties": {
                "client_name": {"type": "string"},
                "client_phone": {"type": "string"},
                "start": {"type": "string", "description": "ISO datetime начала слота"},
                "duration_minutes": {"type": "integer"},
                "service": {"type": "string"},
            },
            "required": ["client_name", "client_phone", "start", "duration_minutes", "service"],
        },
    },
    "reschedule_appointment": {
        "name": "reschedule_appointment",
        "description": "Перенести существующую запись на новое время.",
        "input_schema": {
            "type": "object",
            "properties": {
                "event_id": {"type": "string"},
                "new_start": {"type": "string", "description": "ISO datetime нового начала"},
                "duration_minutes": {"type": "integer"},
            },
            "required": ["event_id", "new_start", "duration_minutes"],
        },
    },
    "cancel_appointment": {
        "name": "cancel_appointment",
        "description": "Отменить существующую запись.",
        "input_schema": {
            "type": "object",
            "properties": {"event_id": {"type": "string"}},
            "required": ["event_id"],
        },
    },
    "book_trial_lesson": {
        "name": "book_trial_lesson",
        "description": "Записать клиента на бесплатный пробный урок по курсу.",
        "input_schema": {
            "type": "object",
            "properties": {
                "client_name": {"type": "string"},
                "client_phone": {"type": "string"},
                "course": {"type": "string"},
                "start": {"type": "string", "description": "ISO datetime начала пробного урока"},
            },
            "required": ["client_name", "client_phone", "course", "start"],
        },
    },
    "create_lead": {
        "name": "create_lead",
        "description": "Создать лид в CRM (тёплый клиент, готовый к оплате, или квалифицированный контакт с холодного звонка).",
        "input_schema": {
            "type": "object",
            "properties": {
                "name": {"type": "string"},
                "phone": {"type": "string"},
                "notes": {"type": "string"},
            },
            "required": ["name", "phone"],
        },
    },
    "update_lead_status": {
        "name": "update_lead_status",
        "description": "Обновить статус лида в CRM (например: отказ, заинтересован, недозвон).",
        "input_schema": {
            "type": "object",
            "properties": {
                "lead_id": {"type": "string"},
                "status": {"type": "string"},
            },
            "required": ["lead_id", "status"],
        },
    },
    "schedule_followup": {
        "name": "schedule_followup",
        "description": "Запланировать повторный контакт с клиентом на указанное время.",
        "input_schema": {
            "type": "object",
            "properties": {
                "lead_id": {"type": "string"},
                "followup_at": {"type": "string", "description": "ISO datetime повторного звонка"},
                "note": {"type": "string"},
            },
            "required": ["lead_id", "followup_at"],
        },
    },
    "get_product_pitch": {
        "name": "get_product_pitch",
        "description": "Получить краткую презентацию продукта/услуги для холодного звонка.",
        "input_schema": {"type": "object", "properties": {}},
    },
    "get_objection_response": {
        "name": "get_objection_response",
        "description": "Получить рекомендованный ответ на возражение клиента.",
        "input_schema": {
            "type": "object",
            "properties": {"objection": {"type": "string", "description": "Возражение клиента своими словами"}},
            "required": ["objection"],
        },
    },
    "escalate_to_human": {
        "name": "escalate_to_human",
        "description": "Передать звонок живому сотруднику, когда агент не может помочь или клиент явно просит человека.",
        "input_schema": {
            "type": "object",
            "properties": {"reason": {"type": "string", "description": "Причина эскалации"}},
            "required": ["reason"],
        },
    },
}


class FunctionCallError(RuntimeError):
    """Ошибка выполнения функции (неизвестное имя или отсутствует интеграция)."""


class FunctionRegistry:
    """Собирает схемы инструментов для профиля и выполняет их вызовы."""

    def __init__(
        self,
        knowledge_base: TenantKnowledgeBase,
        calendar: GoogleCalendarClient | None = None,
        crm: CrmClient | None = None,
    ) -> None:
        self.knowledge_base = knowledge_base
        self.calendar = calendar
        self.crm = crm
        self.escalated = False
        self.escalation_reason = ""

    def tools_for(self, function_names: list[str]) -> list[dict[str, Any]]:
        unknown = [name for name in function_names if name not in FUNCTION_SCHEMAS]
        if unknown:
            raise FunctionCallError(f"Неизвестные функции в профиле: {unknown}")
        return [FUNCTION_SCHEMAS[name] for name in function_names]

    async def call(self, name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        handler = getattr(self, f"_handle_{name}", None)
        if handler is None:
            raise FunctionCallError(f"Нет обработчика для функции '{name}'")
        return await handler(**arguments)

    # --- База знаний -----------------------------------------------------

    async def _handle_get_services(self) -> dict[str, Any]:
        return {"services": self.knowledge_base.get_services()}

    async def _handle_get_courses(self) -> dict[str, Any]:
        return {"courses": self.knowledge_base.get_courses()}

    async def _handle_search_knowledge_base(self, query: str) -> dict[str, Any]:
        return {"results": self.knowledge_base.search_knowledge_base(query)}

    async def _handle_get_product_pitch(self) -> dict[str, Any]:
        return {"pitch": self.knowledge_base.get_product_pitch()}

    async def _handle_get_objection_response(self, objection: str) -> dict[str, Any]:
        return {"response": self.knowledge_base.get_objection_response(objection)}

    # --- Календарь ---------------------------------------------------------

    def _require_calendar(self) -> GoogleCalendarClient:
        if self.calendar is None:
            raise FunctionCallError("Интеграция с календарём не настроена для этого тенанта")
        return self.calendar

    async def _handle_check_availability(self, date: str, duration_minutes: int) -> dict[str, Any]:
        calendar = self._require_calendar()
        parsed_date = datetime.fromisoformat(date)
        slots = await calendar.get_free_slots(parsed_date, duration_minutes)
        return {"slots": [{"start": s.start.isoformat(), "end": s.end.isoformat()} for s in slots]}

    async def _handle_book_appointment(
        self, client_name: str, client_phone: str, start: str, duration_minutes: int, service: str
    ) -> dict[str, Any]:
        calendar = self._require_calendar()
        start_dt = datetime.fromisoformat(start)
        slot = TimeSlot(start=start_dt, end=start_dt + timedelta(minutes=duration_minutes))
        event_id = await calendar.book_appointment(slot, client_name, client_phone, note=service)
        return {"event_id": event_id}

    async def _handle_book_trial_lesson(
        self, client_name: str, client_phone: str, course: str, start: str
    ) -> dict[str, Any]:
        calendar = self._require_calendar()
        start_dt = datetime.fromisoformat(start)
        slot = TimeSlot(start=start_dt, end=start_dt + timedelta(minutes=60))
        event_id = await calendar.book_appointment(
            slot, client_name, client_phone, note=f"Пробный урок: {course}"
        )
        return {"event_id": event_id}

    async def _handle_reschedule_appointment(
        self, event_id: str, new_start: str, duration_minutes: int
    ) -> dict[str, Any]:
        calendar = self._require_calendar()
        start_dt = datetime.fromisoformat(new_start)
        slot = TimeSlot(start=start_dt, end=start_dt + timedelta(minutes=duration_minutes))
        await calendar.reschedule_appointment(event_id, slot)
        return {"status": "rescheduled"}

    async def _handle_cancel_appointment(self, event_id: str) -> dict[str, Any]:
        calendar = self._require_calendar()
        await calendar.cancel_appointment(event_id)
        return {"status": "cancelled"}

    # --- CRM -----------------------------------------------------------

    def _require_crm(self) -> CrmClient:
        if self.crm is None:
            raise FunctionCallError("Интеграция с CRM не настроена для этого тенанта")
        return self.crm

    async def _handle_create_lead(self, name: str, phone: str, notes: str = "") -> dict[str, Any]:
        crm = self._require_crm()
        lead = Lead(name=name, phone=phone, source="call", business_profile="", notes=notes)
        lead_id = await crm.create_lead(lead)
        return {"lead_id": lead_id}

    async def _handle_update_lead_status(self, lead_id: str, status: str) -> dict[str, Any]:
        crm = self._require_crm()
        await crm.update_lead_status(lead_id, status)
        return {"status": "updated"}

    async def _handle_schedule_followup(
        self, lead_id: str, followup_at: str, note: str = ""
    ) -> dict[str, Any]:
        crm = self._require_crm()
        await crm.update_lead_status(lead_id, f"followup:{followup_at} {note}".strip())
        return {"status": "followup_scheduled"}

    # --- Эскалация -------------------------------------------------------

    async def _handle_escalate_to_human(self, reason: str) -> dict[str, Any]:
        self.escalated = True
        self.escalation_reason = reason
        return {"escalated": True}

