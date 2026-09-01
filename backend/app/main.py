"""FastAPI приложение: webhooks для телефонии, тестовый текстовый диалог,
и минимальный API дашборда.

MVP-статус (см. README.md и docs/business-plan.md, Roadmap "Неделя 1-2"):
- Реальная интеграция с телефонией (Asterisk ARI) ещё не подключена сюда —
  для проверки диалогового движка используйте POST /dialogue/text, который
  прогоняет реплики через тот же DialogueManager/FunctionRegistry, что будет
  использовать голосовой пайплайн, только в обход STT/TTS/телефонии.
"""

from __future__ import annotations

from fastapi import Depends, FastAPI, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.agent.dialogue import DialogueManager
from app.config import get_settings
from app.providers import build_dialogue_manager
from app.storage.db import get_db, init_db
from app.storage.models import CallLog, Tenant

app = FastAPI(title="AI Voice Agent")


@app.on_event("startup")
async def _create_tables_for_local_sqlite() -> None:
    """Автосоздание таблиц только для локального SQLite (удобство разработки).

    В проде (Postgres) таблицы создаются миграциями, не автоматически при
    старте приложения.
    """
    if get_settings().database_url.startswith("sqlite"):
        init_db()

# Сессии тестового текстового диалога в памяти процесса: client_id -> DialogueManager.
# Годится для локальной разработки/QA сценариев; для прод-звонков сессия живёт
# в CallOrchestrator на время одного звонка (см. voice_pipeline/orchestrator.py).
_dialogue_sessions: dict[str, DialogueManager] = {}


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/webhooks/telephony/call-started")
async def call_started() -> dict[str, str]:
    """Webhook: новый звонок начался — запустить CallOrchestrator.

    Требует интеграции с конкретной телефонной платформой (Asterisk ARI или
    облачный webhook) — см. app/telephony/asterisk_client.py и
    docs/architecture.md. Не реализовано в MVP до подключения реального
    SIP-транка/номера.
    """
    raise NotImplementedError(
        "Webhook телефонии не подключён: нужен реальный SIP-транк/Asterisk (см. docs/architecture.md)"
    )


class TenantCreate(BaseModel):
    name: str
    business_profile: str  # courses | salon | sales
    phone_number: str


class TenantOut(BaseModel):
    id: int
    name: str
    business_profile: str
    phone_number: str

    model_config = {"from_attributes": True}


@app.post("/api/tenants", response_model=TenantOut)
async def create_tenant(payload: TenantCreate, db: Session = Depends(get_db)) -> Tenant:
    if payload.business_profile not in {"courses", "salon", "sales"}:
        raise HTTPException(status_code=400, detail="business_profile должен быть courses/salon/sales")
    tenant = Tenant(
        name=payload.name,
        business_profile=payload.business_profile,
        phone_number=payload.phone_number,
    )
    db.add(tenant)
    db.commit()
    db.refresh(tenant)
    return tenant


class CallLogOut(BaseModel):
    id: int
    direction: str
    caller_number: str
    language: str
    outcome: str

    model_config = {"from_attributes": True}


@app.get("/api/tenants/{tenant_id}/calls", response_model=list[CallLogOut])
async def list_calls(tenant_id: int, db: Session = Depends(get_db)) -> list[CallLog]:
    """Список звонков для дашборда владельца бизнеса."""
    return db.query(CallLog).filter(CallLog.tenant_id == tenant_id).order_by(CallLog.id.desc()).all()


class DialogueTextRequest(BaseModel):
    client_id: str
    business_profile: str  # courses | salon | sales
    language: str  # ru | uz
    text: str
    tenant_knowledge_id: str = ""  # по умолчанию берётся demo-<business_profile>
    calendar_id: str = ""


class DialogueTextResponse(BaseModel):
    reply: str
    escalated: bool


@app.post("/dialogue/text", response_model=DialogueTextResponse)
async def dialogue_text(payload: DialogueTextRequest) -> DialogueTextResponse:
    """Тестовый текстовый вход в диалоговый движок (в обход STT/TTS/телефонии)."""
    session = _dialogue_sessions.get(payload.client_id)
    if session is None:
        knowledge_id = payload.tenant_knowledge_id or f"demo-{payload.business_profile}"
        try:
            session = build_dialogue_manager(
                tenant_knowledge_id=knowledge_id,
                business_profile_name=payload.business_profile,
                language=payload.language,
                client_id=payload.client_id,
                calendar_id=payload.calendar_id,
            )
        except FileNotFoundError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        _dialogue_sessions[payload.client_id] = session

    reply = await session.handle_user_utterance(payload.text)
    return DialogueTextResponse(reply=reply, escalated=session.escalated)
