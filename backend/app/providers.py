"""Фабрики провайдеров (STT/TTS/LLM/CRM/Calendar) из конфигурации приложения.

Отделяет "как собрать объект из env-настроек" от бизнес-логики в agent/ и
voice_pipeline/, чтобы тесты могли передавать свои реализации напрямую.
"""

from __future__ import annotations

from anthropic import AsyncAnthropic

from app.agent.dialogue import BusinessProfile, DialogueManager
from app.agent.functions import FunctionRegistry
from app.agent.knowledge import TenantKnowledgeBase
from app.config import Settings, get_settings
from app.integrations.calendar import GoogleCalendarClient
from app.integrations.crm import AmoCrmClient, Bitrix24Client, CrmClient
from app.voice_pipeline.stt import SpeechToTextProvider, YandexSpeechKitSTT
from app.voice_pipeline.tts import TextToSpeechProvider, YandexSpeechKitTTS


def build_stt(settings: Settings | None = None) -> SpeechToTextProvider:
    settings = settings or get_settings()
    return YandexSpeechKitSTT(settings.yandex_speechkit_api_key, settings.yandex_speechkit_folder_id)


def build_tts(settings: Settings | None = None) -> TextToSpeechProvider:
    settings = settings or get_settings()
    return YandexSpeechKitTTS(settings.yandex_speechkit_api_key, settings.yandex_speechkit_folder_id)


def build_calendar(calendar_id: str, settings: Settings | None = None) -> GoogleCalendarClient | None:
    """Вернуть клиент календаря, либо None если интеграция не настроена для тенанта."""
    settings = settings or get_settings()
    if not settings.google_calendar_credentials_json or not calendar_id:
        return None
    return GoogleCalendarClient(settings.google_calendar_credentials_json, calendar_id)


def build_crm(settings: Settings | None = None) -> CrmClient | None:
    """Вернуть CRM-клиент по первой сконфигурированной интеграции, либо None."""
    settings = settings or get_settings()
    if settings.bitrix24_webhook_url:
        return Bitrix24Client(settings.bitrix24_webhook_url)
    if settings.amocrm_api_key and settings.amocrm_subdomain:
        return AmoCrmClient(settings.amocrm_api_key, settings.amocrm_subdomain)
    return None


def build_dialogue_manager(
    tenant_knowledge_id: str,
    business_profile_name: str,
    language: str,
    client_id: str,
    calendar_id: str = "",
    settings: Settings | None = None,
) -> DialogueManager:
    """Собрать полностью настроенный DialogueManager для одного звонка/сессии."""
    settings = settings or get_settings()
    profile = BusinessProfile.load(business_profile_name)
    knowledge_base = TenantKnowledgeBase.load(tenant_knowledge_id)
    calendar = build_calendar(calendar_id, settings)
    crm = build_crm(settings)
    registry = FunctionRegistry(knowledge_base=knowledge_base, calendar=calendar, crm=crm)
    anthropic_client = AsyncAnthropic(api_key=settings.anthropic_api_key)
    return DialogueManager(
        profile=profile,
        language=language,
        client_id=client_id,
        function_registry=registry,
        anthropic_client=anthropic_client,
        model=settings.anthropic_model,
    )
