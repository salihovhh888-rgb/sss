from datetime import datetime
from unittest.mock import MagicMock

import pytest

from app.integrations.calendar import CalendarError, GoogleCalendarClient, TimeSlot


def _fake_service_with_busy(busy_periods: list[dict]) -> MagicMock:
    service = MagicMock()
    service.freebusy.return_value.query.return_value.execute.return_value = {
        "calendars": {"cal-1": {"busy": busy_periods}}
    }
    return service


async def test_get_free_slots_excludes_busy_periods(monkeypatch):
    client = GoogleCalendarClient(credentials_json="{}", calendar_id="cal-1")
    busy = [
        {
            "start": "2026-09-10T10:00:00+05:00",
            "end": "2026-09-10T11:00:00+05:00",
        }
    ]
    monkeypatch.setattr(client, "_build_service", lambda: _fake_service_with_busy(busy))

    from datetime import timedelta, timezone

    tz = timezone(timedelta(hours=5))
    date = datetime(2026, 9, 10, tzinfo=tz)

    slots = await client.get_free_slots(date, duration_minutes=60, day_start_hour=9, day_end_hour=12)
    slot_starts = [s.start.hour for s in slots]
    assert 10 not in slot_starts  # занято
    assert 9 in slot_starts
    assert 11 in slot_starts


async def test_get_free_slots_raises_calendar_error_on_api_failure(monkeypatch):
    client = GoogleCalendarClient(credentials_json="{}", calendar_id="cal-1")
    service = MagicMock()
    service.freebusy.return_value.query.return_value.execute.side_effect = RuntimeError("boom")
    monkeypatch.setattr(client, "_build_service", lambda: service)

    with pytest.raises(CalendarError):
        await client.get_free_slots(datetime(2026, 9, 10), duration_minutes=60)


async def test_book_appointment_returns_event_id(monkeypatch):
    client = GoogleCalendarClient(credentials_json="{}", calendar_id="cal-1")
    service = MagicMock()
    service.events.return_value.insert.return_value.execute.return_value = {"id": "evt-123"}
    monkeypatch.setattr(client, "_build_service", lambda: service)

    slot = TimeSlot(start=datetime(2026, 9, 10, 10, 0), end=datetime(2026, 9, 10, 11, 0))
    event_id = await client.book_appointment(slot, "Иван", "+998901234567", note="Стрижка")
    assert event_id == "evt-123"


async def test_cancel_appointment_calls_delete(monkeypatch):
    client = GoogleCalendarClient(credentials_json="{}", calendar_id="cal-1")
    service = MagicMock()
    monkeypatch.setattr(client, "_build_service", lambda: service)

    await client.cancel_appointment("evt-123")
    service.events.return_value.delete.assert_called_once_with(calendarId="cal-1", eventId="evt-123")
