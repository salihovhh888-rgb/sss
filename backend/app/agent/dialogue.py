"""Диалоговый менеджер: обёртка над Claude API с function calling.

Загружает профиль бизнеса (courses/salon/sales) из app/agent/profiles/*.yaml,
ведёт историю диалога для звонка и вызывает функции-интеграции
(app/integrations) в ответ на tool_use от модели.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

PROFILES_DIR = Path(__file__).parent / "profiles"


@dataclass
class BusinessProfile:
    name: str
    languages: list[str]
    system_prompt: dict[str, str]  # {"ru": ..., "uz": ...}
    functions: list[str]
    escalation_triggers: list[str]
    raw: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def load(cls, profile_name: str) -> "BusinessProfile":
        path = PROFILES_DIR / f"{profile_name}.yaml"
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
        return cls(
            name=data["name"],
            languages=data["languages"],
            system_prompt={
                "ru": data.get("system_prompt_ru", ""),
                "uz": data.get("system_prompt_uz", ""),
            },
            functions=data.get("functions", []),
            escalation_triggers=data.get("escalation_triggers", []),
            raw=data,
        )


@dataclass
class DialogueTurn:
    role: str  # "user" | "assistant"
    text: str


class DialogueManager:
    """Ведёт диалог одного звонка для заданного профиля бизнеса и языка."""

    def __init__(self, profile: BusinessProfile, language: str, client_id: str) -> None:
        self.profile = profile
        self.language = language
        self.client_id = client_id
        self.history: list[DialogueTurn] = []

    async def handle_user_utterance(self, text: str) -> str:
        """Принять распознанную реплику клиента, вернуть текст ответа агента.

        MVP-каркас: реальная реализация вызывает Claude API с системным
        промптом профиля, историей диалога и function calling для функций,
        перечисленных в profile.functions (реализованы в app/integrations).
        """
        raise NotImplementedError

    def should_escalate(self, text: str) -> bool:
        lowered = text.lower()
        return any(trigger.lower() in lowered for trigger in self.profile.escalation_triggers)
