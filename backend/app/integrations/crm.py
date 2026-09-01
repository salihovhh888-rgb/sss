"""Интеграция с CRM (amoCRM / Bitrix24) для лидов из холодных звонков и продаж.

Следующий этап после MVP на Google Calendar — см. docs/architecture.md.
"""

from __future__ import annotations

from dataclasses import dataclass

import httpx


@dataclass
class Lead:
    name: str
    phone: str
    source: str  # "outbound_call" | "inbound_call"
    business_profile: str  # "sales" | "courses" | "salon"
    notes: str = ""


class CrmError(RuntimeError):
    """Ошибка при обращении к CRM."""


class CrmClient:
    """Базовый интерфейс CRM-адаптера."""

    async def create_lead(self, lead: Lead) -> str:
        """Создать лид/сделку в CRM, вернуть внешний id."""
        raise NotImplementedError

    async def update_lead_status(self, lead_id: str, status: str) -> None:
        raise NotImplementedError


class AmoCrmClient(CrmClient):
    """Клиент amoCRM API v4.

    ``api_key`` — долгоживущий (long-lived) токен доступа, выпущенный в
    настройках интеграции amoCRM (Bearer-токен для api/v4). Смена статуса
    сделки реализована через заметку с текстом статуса, т.к. соответствие
    "status" -> status_id воронки продаж специфично для каждого клиента и
    настраивается на этапе внедрения под конкретный аккаунт.
    """

    def __init__(self, api_key: str, subdomain: str, timeout_seconds: float = 15.0) -> None:
        self.api_key = api_key
        self.subdomain = subdomain
        self.timeout_seconds = timeout_seconds

    @property
    def _base_url(self) -> str:
        return f"https://{self.subdomain}.amocrm.ru/api/v4"

    def _headers(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {self.api_key}"}

    async def create_lead(self, lead: Lead) -> str:
        payload = [
            {
                "name": f"{lead.name} — {lead.business_profile}",
                "_embedded": {
                    "contacts": [
                        {
                            "first_name": lead.name,
                            "custom_fields_values": None,
                        }
                    ]
                },
            }
        ]
        async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
            response = await client.post(
                f"{self._base_url}/leads", headers=self._headers(), json=payload
            )
        if response.status_code not in (200, 201):
            raise CrmError(f"amoCRM создание лида вернуло {response.status_code}: {response.text}")
        data = response.json()
        lead_id = str(data["_embedded"]["leads"][0]["id"])
        if lead.notes or lead.phone:
            await self._add_note(lead_id, f"Телефон: {lead.phone}. {lead.notes}".strip())
        return lead_id

    async def _add_note(self, lead_id: str, text: str) -> None:
        payload = [{"note_type": "common", "params": {"text": text}}]
        async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
            await client.post(
                f"{self._base_url}/leads/{lead_id}/notes", headers=self._headers(), json=payload
            )

    async def update_lead_status(self, lead_id: str, status: str) -> None:
        await self._add_note(lead_id, f"Статус: {status}")


class Bitrix24Client(CrmClient):
    """Клиент Bitrix24 через входящий вебхук (rest/{user_id}/{webhook_key}/)."""

    def __init__(self, webhook_url: str, timeout_seconds: float = 15.0) -> None:
        self.webhook_url = webhook_url.rstrip("/")
        self.timeout_seconds = timeout_seconds

    async def create_lead(self, lead: Lead) -> str:
        payload = {
            "fields": {
                "TITLE": f"{lead.name} — {lead.business_profile}",
                "NAME": lead.name,
                "PHONE": [{"VALUE": lead.phone, "VALUE_TYPE": "WORK"}],
                "SOURCE_ID": "CALL",
                "COMMENTS": lead.notes,
            }
        }
        async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
            response = await client.post(f"{self.webhook_url}/crm.lead.add.json", json=payload)
        data = response.json()
        if "result" not in data:
            raise CrmError(f"Bitrix24 создание лида не удалось: {data}")
        return str(data["result"])

    async def update_lead_status(self, lead_id: str, status: str) -> None:
        payload = {"id": lead_id, "fields": {"STATUS_ID": status}}
        async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
            response = await client.post(f"{self.webhook_url}/crm.lead.update.json", json=payload)
        data = response.json()
        if "result" not in data:
            raise CrmError(f"Bitrix24 обновление статуса лида {lead_id} не удалось: {data}")
