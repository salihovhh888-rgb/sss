"""Интеграция с CRM (amoCRM / Bitrix24) для лидов из холодных звонков и продаж.

Следующий этап после MVP на Google Calendar — см. docs/architecture.md.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class Lead:
    name: str
    phone: str
    source: str  # "outbound_call" | "inbound_call"
    business_profile: str  # "sales" | "courses" | "salon"
    notes: str = ""


class CrmClient:
    """Базовый интерфейс CRM-адаптера."""

    async def create_lead(self, lead: Lead) -> str:
        """Создать лид/сделку в CRM, вернуть внешний id."""
        raise NotImplementedError

    async def update_lead_status(self, lead_id: str, status: str) -> None:
        raise NotImplementedError


class AmoCrmClient(CrmClient):
    def __init__(self, api_key: str, subdomain: str) -> None:
        self.api_key = api_key
        self.subdomain = subdomain

    async def create_lead(self, lead: Lead) -> str:
        raise NotImplementedError

    async def update_lead_status(self, lead_id: str, status: str) -> None:
        raise NotImplementedError


class Bitrix24Client(CrmClient):
    def __init__(self, webhook_url: str) -> None:
        self.webhook_url = webhook_url

    async def create_lead(self, lead: Lead) -> str:
        raise NotImplementedError

    async def update_lead_status(self, lead_id: str, status: str) -> None:
        raise NotImplementedError
