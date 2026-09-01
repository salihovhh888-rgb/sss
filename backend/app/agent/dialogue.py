"""Диалоговый менеджер: обёртка над Claude API с function calling.

Загружает профиль бизнеса (courses/salon/sales) из app/agent/profiles/*.yaml,
ведёт историю диалога для звонка и вызывает функции-интеграции
(через FunctionRegistry, app/agent/functions.py) в ответ на tool_use от модели.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml
from anthropic import AsyncAnthropic

from app.agent.functions import FunctionRegistry

PROFILES_DIR = Path(__file__).parent / "profiles"

MAX_TOOL_ROUNDTRIPS = 5

_ESCALATION_REPLY = {
    "ru": "Хорошо, сейчас переключу вас на сотрудника, оставайтесь на линии.",
    "uz": "Yaxshi, hozir sizni xodimga ulayman, iltimos kutib turing.",
}


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

    def __init__(
        self,
        profile: BusinessProfile,
        language: str,
        client_id: str,
        function_registry: FunctionRegistry,
        anthropic_client: AsyncAnthropic,
        model: str,
    ) -> None:
        self.profile = profile
        self.language = language
        self.client_id = client_id
        self.function_registry = function_registry
        self.anthropic_client = anthropic_client
        self.model = model
        self.history: list[DialogueTurn] = []
        self._messages: list[dict[str, Any]] = []

    @property
    def escalated(self) -> bool:
        return self.function_registry.escalated

    async def handle_user_utterance(self, text: str) -> str:
        """Принять распознанную реплику клиента, вернуть текст ответа агента."""
        self.history.append(DialogueTurn(role="user", text=text))

        if self.should_escalate(text):
            reply = _ESCALATION_REPLY.get(self.language, _ESCALATION_REPLY["ru"])
            self.function_registry.escalated = True
            self.function_registry.escalation_reason = "ключевая фраза клиента"
            self.history.append(DialogueTurn(role="assistant", text=reply))
            return reply

        self._messages.append({"role": "user", "content": text})
        system_prompt = self.profile.system_prompt.get(self.language, self.profile.system_prompt.get("ru", ""))
        tools = self.function_registry.tools_for(self.profile.functions)

        for _ in range(MAX_TOOL_ROUNDTRIPS):
            response = await self.anthropic_client.messages.create(
                model=self.model,
                max_tokens=1024,
                system=system_prompt,
                messages=self._messages,
                tools=tools,
            )
            self._messages.append({"role": "assistant", "content": response.content})

            if response.stop_reason != "tool_use":
                reply = "".join(block.text for block in response.content if block.type == "text")
                self.history.append(DialogueTurn(role="assistant", text=reply))
                return reply

            tool_results = []
            for block in response.content:
                if block.type != "tool_use":
                    continue
                result = await self.function_registry.call(block.name, block.input)
                tool_results.append(
                    {
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": str(result),
                    }
                )
            self._messages.append({"role": "user", "content": tool_results})

            if self.function_registry.escalated:
                reply = _ESCALATION_REPLY.get(self.language, _ESCALATION_REPLY["ru"])
                self.history.append(DialogueTurn(role="assistant", text=reply))
                return reply

        fallback = _ESCALATION_REPLY.get(self.language, _ESCALATION_REPLY["ru"])
        self.function_registry.escalated = True
        self.function_registry.escalation_reason = "превышен лимит обращений к функциям"
        self.history.append(DialogueTurn(role="assistant", text=fallback))
        return fallback

    def should_escalate(self, text: str) -> bool:
        lowered = text.lower()
        return any(trigger.lower() in lowered for trigger in self.profile.escalation_triggers)
