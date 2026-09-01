"""Централизованная конфигурация приложения из переменных окружения.

Значения читаются из .env (см. .env.example) через pydantic-settings.
Ничего в этом модуле не должно обращаться к внешним сервисам напрямую —
он только собирает конфигурацию, которую используют providers/integrations.
"""

from __future__ import annotations

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # LLM
    anthropic_api_key: str = ""
    anthropic_model: str = "claude-sonnet-5"

    # STT/TTS (основной провайдер)
    yandex_speechkit_api_key: str = ""
    yandex_speechkit_folder_id: str = ""

    # STT/TTS (резерв/A-B тест для узбекского)
    aisha_ai_api_key: str = ""
    neuronai_api_key: str = ""

    # Телефония (SIP-транк / Asterisk ARI)
    sip_trunk_host: str = ""
    sip_trunk_user: str = ""
    sip_trunk_password: str = ""
    asterisk_ari_url: str = ""
    asterisk_ari_user: str = ""
    asterisk_ari_password: str = ""

    # Интеграции
    google_calendar_credentials_json: str = ""
    amocrm_api_key: str = ""
    amocrm_subdomain: str = ""
    bitrix24_webhook_url: str = ""

    # Хранение данных
    database_url: str = "sqlite:///./ai_agent.db"


@lru_cache
def get_settings() -> Settings:
    return Settings()
