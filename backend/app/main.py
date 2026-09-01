"""FastAPI приложение: webhooks для телефонии и админ-эндпоинты.

MVP-каркас: реальная реализация принимает события звонков от Asterisk ARI
(или webhook облачной телефонии), поднимает CallOrchestrator на каждый новый
звонок и отдаёт минимальный API для дашборда (список звонков/броней/лидов).
"""

from __future__ import annotations

from fastapi import FastAPI

app = FastAPI(title="AI Voice Agent")


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/webhooks/telephony/call-started")
async def call_started() -> dict[str, str]:
    """Webhook: новый звонок начался — запустить CallOrchestrator."""
    raise NotImplementedError


@app.get("/api/tenants/{tenant_id}/calls")
async def list_calls(tenant_id: int) -> list[dict]:
    """Список звонков для дашборда владельца бизнеса."""
    raise NotImplementedError
