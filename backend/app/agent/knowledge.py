"""База знаний конкретного бизнеса-арендатора (тенанта): услуги/курсы/цены/скрипты.

MVP-хранилище — YAML-файл на тенанта в ``app/agent/knowledge_data/<tenant_id>.yaml``.
Так диалоговый движок не хардкодит факты бизнеса в системный промпт (см.
docs/architecture.md, раздел "LLM / диалоговый движок") — модель обязана
запрашивать актуальные данные через function calling. На следующем этапе
(после MVP) это заменяется на таблицы в БД с админкой для владельца бизнеса.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

KNOWLEDGE_DIR = Path(__file__).parent / "knowledge_data"


class TenantKnowledgeBase:
    def __init__(self, data: dict[str, Any]) -> None:
        self._data = data

    @classmethod
    def load(cls, tenant_id: str) -> "TenantKnowledgeBase":
        path = KNOWLEDGE_DIR / f"{tenant_id}.yaml"
        if not path.exists():
            raise FileNotFoundError(
                f"Нет базы знаний для тенанта '{tenant_id}' ({path}). "
                "Создайте app/agent/knowledge_data/<tenant_id>.yaml по образцу demo-*.yaml."
            )
        data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        return cls(data)

    def get_services(self) -> list[dict[str, Any]]:
        return self._data.get("services", [])

    def get_courses(self) -> list[dict[str, Any]]:
        return self._data.get("courses", [])

    def search_knowledge_base(self, query: str) -> list[dict[str, Any]]:
        query_lower = query.lower()
        entries = self._data.get("faq", [])
        matches = [
            entry
            for entry in entries
            if query_lower in entry.get("question", "").lower()
            or query_lower in entry.get("answer", "").lower()
        ]
        return matches or entries[:3]

    def get_product_pitch(self) -> dict[str, Any]:
        return self._data.get("product_pitch", {})

    def get_objection_response(self, objection: str) -> str:
        objections: dict[str, str] = self._data.get("objections", {})
        objection_lower = objection.lower()
        for key, response in objections.items():
            if key.lower() in objection_lower:
                return response
        return objections.get("default", "Понимаю ваши сомнения. Могу подробнее рассказать, что вас беспокоит?")
