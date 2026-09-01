"""Интеграция с Google Calendar для записи клиентов на приём (booking).

Самый быстрый вариант для MVP (профиль "salon" и пробные уроки в "courses").
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass
class TimeSlot:
    start: datetime
    end: datetime


class GoogleCalendarClient:
    def __init__(self, credentials_json: str, calendar_id: str) -> None:
        self.credentials_json = credentials_json
        self.calendar_id = calendar_id

    async def get_free_slots(self, date: datetime, duration_minutes: int) -> list[TimeSlot]:
        raise NotImplementedError

    async def book_appointment(
        self, slot: TimeSlot, client_name: str, client_phone: str, note: str = ""
    ) -> str:
        """Создать событие в календаре, вернуть event_id."""
        raise NotImplementedError

    async def reschedule_appointment(self, event_id: str, new_slot: TimeSlot) -> None:
        raise NotImplementedError

    async def cancel_appointment(self, event_id: str) -> None:
        raise NotImplementedError
