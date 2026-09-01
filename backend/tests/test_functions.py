from datetime import datetime
from unittest.mock import AsyncMock

import pytest

from app.agent.functions import FunctionCallError, FunctionRegistry
from app.agent.knowledge import TenantKnowledgeBase
from app.integrations.calendar import TimeSlot


@pytest.fixture
def registry() -> FunctionRegistry:
    kb = TenantKnowledgeBase.load("demo-salon")
    return FunctionRegistry(knowledge_base=kb)


def test_tools_for_known_functions_returns_schemas(registry):
    tools = registry.tools_for(["get_services", "escalate_to_human"])
    names = {t["name"] for t in tools}
    assert names == {"get_services", "escalate_to_human"}


def test_tools_for_unknown_function_raises(registry):
    with pytest.raises(FunctionCallError):
        registry.tools_for(["not_a_real_function"])


async def test_call_get_services_reads_from_knowledge_base(registry):
    result = await registry.call("get_services", {})
    assert any(s["name"] == "Мужская стрижка" for s in result["services"])


async def test_call_unknown_function_raises(registry):
    with pytest.raises(FunctionCallError):
        await registry.call("does_not_exist", {})


async def test_escalate_to_human_sets_flag(registry):
    result = await registry.call("escalate_to_human", {"reason": "клиент попросил человека"})
    assert result == {"escalated": True}
    assert registry.escalated is True
    assert registry.escalation_reason == "клиент попросил человека"


async def test_check_availability_without_calendar_raises(registry):
    with pytest.raises(FunctionCallError):
        await registry.call("check_availability", {"date": "2026-09-10", "duration_minutes": 60})


async def test_check_availability_delegates_to_calendar():
    kb = TenantKnowledgeBase.load("demo-salon")
    calendar = AsyncMock()
    calendar.get_free_slots.return_value = [
        TimeSlot(start=datetime(2026, 9, 10, 9, 0), end=datetime(2026, 9, 10, 10, 0))
    ]
    registry = FunctionRegistry(knowledge_base=kb, calendar=calendar)

    result = await registry.call("check_availability", {"date": "2026-09-10", "duration_minutes": 60})
    assert result["slots"][0]["start"] == "2026-09-10T09:00:00"
    calendar.get_free_slots.assert_called_once()


async def test_book_appointment_delegates_to_calendar():
    kb = TenantKnowledgeBase.load("demo-salon")
    calendar = AsyncMock()
    calendar.book_appointment.return_value = "evt-1"
    registry = FunctionRegistry(knowledge_base=kb, calendar=calendar)

    result = await registry.call(
        "book_appointment",
        {
            "client_name": "Иван",
            "client_phone": "+998901234567",
            "start": "2026-09-10T10:00:00",
            "duration_minutes": 60,
            "service": "Мужская стрижка",
        },
    )
    assert result == {"event_id": "evt-1"}
    args, kwargs = calendar.book_appointment.call_args
    slot: TimeSlot = args[0]
    assert slot.start == datetime(2026, 9, 10, 10, 0)
    assert slot.end == datetime(2026, 9, 10, 11, 0)


async def test_create_lead_without_crm_raises():
    kb = TenantKnowledgeBase.load("demo-sales")
    registry = FunctionRegistry(knowledge_base=kb)
    with pytest.raises(FunctionCallError):
        await registry.call("create_lead", {"name": "Иван", "phone": "+998901234567"})


async def test_create_lead_delegates_to_crm():
    kb = TenantKnowledgeBase.load("demo-sales")
    crm = AsyncMock()
    crm.create_lead.return_value = "lead-1"
    registry = FunctionRegistry(knowledge_base=kb, crm=crm)

    result = await registry.call("create_lead", {"name": "Иван", "phone": "+998901234567", "notes": "интересуется"})
    assert result == {"lead_id": "lead-1"}
    crm.create_lead.assert_called_once()


async def test_get_objection_response_reads_from_knowledge_base():
    kb = TenantKnowledgeBase.load("demo-sales")
    registry = FunctionRegistry(knowledge_base=kb)
    result = await registry.call("get_objection_response", {"objection": "дорого"})
    assert "окупается" in result["response"]
