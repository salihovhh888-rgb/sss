"""Интеграция с Google Calendar для записи клиентов на приём (booking).

Самый быстрый вариант для MVP (профиль "salon" и пробные уроки в "courses").
Использует Service Account (google-api-python-client), календарь клиента
должен быть расшарен на service account email с правами на изменение.
"""

from __future__ import annotations

import asyncio
import json
from dataclasses import dataclass
from datetime import datetime, timedelta

from google.oauth2 import service_account
from googleapiclient.discovery import build

_SCOPES = ["https://www.googleapis.com/auth/calendar"]


@dataclass
class TimeSlot:
    start: datetime
    end: datetime


class CalendarError(RuntimeError):
    """Ошибка при обращении к Google Calendar API."""


class GoogleCalendarClient:
    def __init__(self, credentials_json: str, calendar_id: str) -> None:
        self.credentials_json = credentials_json
        self.calendar_id = calendar_id

    def _build_service(self):
        info = json.loads(self.credentials_json)
        credentials = service_account.Credentials.from_service_account_info(
            info, scopes=_SCOPES
        )
        return build("calendar", "v3", credentials=credentials, cache_discovery=False)

    async def get_free_slots(
        self,
        date: datetime,
        duration_minutes: int,
        day_start_hour: int = 9,
        day_end_hour: int = 19,
    ) -> list[TimeSlot]:
        return await asyncio.to_thread(
            self._get_free_slots_sync, date, duration_minutes, day_start_hour, day_end_hour
        )

    def _get_free_slots_sync(
        self, date: datetime, duration_minutes: int, day_start_hour: int, day_end_hour: int
    ) -> list[TimeSlot]:
        service = self._build_service()
        day_start = date.replace(hour=day_start_hour, minute=0, second=0, microsecond=0)
        day_end = date.replace(hour=day_end_hour, minute=0, second=0, microsecond=0)
        try:
            response = (
                service.freebusy()
                .query(
                    body={
                        "timeMin": day_start.isoformat(),
                        "timeMax": day_end.isoformat(),
                        "items": [{"id": self.calendar_id}],
                    }
                )
                .execute()
            )
        except Exception as exc:  # noqa: BLE001 - библиотека кидает разные HttpError
            raise CalendarError(f"Google Calendar freebusy запрос не удался: {exc}") from exc

        busy_periods = response["calendars"][self.calendar_id]["busy"]
        busy = [
            (datetime.fromisoformat(b["start"]), datetime.fromisoformat(b["end"]))
            for b in busy_periods
        ]
        busy.sort()

        slots: list[TimeSlot] = []
        cursor = day_start
        step = timedelta(minutes=duration_minutes)
        while cursor + step <= day_end:
            candidate_end = cursor + step
            overlaps = any(cursor < b_end and candidate_end > b_start for b_start, b_end in busy)
            if not overlaps:
                slots.append(TimeSlot(start=cursor, end=candidate_end))
            cursor += step
        return slots

    async def book_appointment(
        self, slot: TimeSlot, client_name: str, client_phone: str, note: str = ""
    ) -> str:
        return await asyncio.to_thread(self._book_appointment_sync, slot, client_name, client_phone, note)

    def _book_appointment_sync(
        self, slot: TimeSlot, client_name: str, client_phone: str, note: str
    ) -> str:
        service = self._build_service()
        event_body = {
            "summary": f"{client_name} ({client_phone})",
            "description": note,
            "start": {"dateTime": slot.start.isoformat()},
            "end": {"dateTime": slot.end.isoformat()},
        }
        try:
            event = (
                service.events()
                .insert(calendarId=self.calendar_id, body=event_body)
                .execute()
            )
        except Exception as exc:  # noqa: BLE001
            raise CalendarError(f"Не удалось создать событие в календаре: {exc}") from exc
        return event["id"]

    async def reschedule_appointment(self, event_id: str, new_slot: TimeSlot) -> None:
        await asyncio.to_thread(self._reschedule_appointment_sync, event_id, new_slot)

    def _reschedule_appointment_sync(self, event_id: str, new_slot: TimeSlot) -> None:
        service = self._build_service()
        try:
            service.events().patch(
                calendarId=self.calendar_id,
                eventId=event_id,
                body={
                    "start": {"dateTime": new_slot.start.isoformat()},
                    "end": {"dateTime": new_slot.end.isoformat()},
                },
            ).execute()
        except Exception as exc:  # noqa: BLE001
            raise CalendarError(f"Не удалось перенести событие {event_id}: {exc}") from exc

    async def cancel_appointment(self, event_id: str) -> None:
        await asyncio.to_thread(self._cancel_appointment_sync, event_id)

    def _cancel_appointment_sync(self, event_id: str) -> None:
        service = self._build_service()
        try:
            service.events().delete(calendarId=self.calendar_id, eventId=event_id).execute()
        except Exception as exc:  # noqa: BLE001
            raise CalendarError(f"Не удалось отменить событие {event_id}: {exc}") from exc
