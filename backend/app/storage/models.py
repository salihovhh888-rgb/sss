"""Модели БД: клиенты (бизнесы-арендаторы SaaS), звонки, брони, лиды.

Postgres, физически/юридически размещённый в Узбекистане — см.
docs/compliance.md (требование локализации персональных данных).
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class Tenant(Base):
    """Бизнес-клиент SaaS (учебный центр / салон / продающая компания)."""

    __tablename__ = "tenants"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(255))
    business_profile: Mapped[str] = mapped_column(String(50))  # courses | salon | sales
    phone_number: Mapped[str] = mapped_column(String(32))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class CallLog(Base):
    """Запись об одном звонке (для аналитики и прослушивания владельцем бизнеса)."""

    __tablename__ = "call_logs"

    id: Mapped[int] = mapped_column(primary_key=True)
    tenant_id: Mapped[int] = mapped_column(ForeignKey("tenants.id"))
    tenant: Mapped["Tenant"] = relationship()
    direction: Mapped[str] = mapped_column(String(16))  # inbound | outbound
    caller_number: Mapped[str] = mapped_column(String(32))
    language: Mapped[str] = mapped_column(String(8))  # ru | uz
    transcript: Mapped[str] = mapped_column(Text, default="")
    outcome: Mapped[str] = mapped_column(String(50), default="")  # booked | lead_created | escalated | no_action
    started_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    ended_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    recording_path: Mapped[str | None] = mapped_column(String(255), nullable=True)


class Booking(Base):
    """Запись клиента на услугу/курс (профили salon и courses)."""

    __tablename__ = "bookings"

    id: Mapped[int] = mapped_column(primary_key=True)
    tenant_id: Mapped[int] = mapped_column(ForeignKey("tenants.id"))
    call_log_id: Mapped[int | None] = mapped_column(ForeignKey("call_logs.id"), nullable=True)
    client_name: Mapped[str] = mapped_column(String(255))
    client_phone: Mapped[str] = mapped_column(String(32))
    service_or_course: Mapped[str] = mapped_column(String(255))
    scheduled_at: Mapped[datetime] = mapped_column(DateTime)
    external_calendar_event_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    status: Mapped[str] = mapped_column(String(32), default="confirmed")  # confirmed | rescheduled | cancelled


class Lead(Base):
    """Лид из холодного/входящего звонка (профиль sales, и тёплые лиды courses)."""

    __tablename__ = "leads"

    id: Mapped[int] = mapped_column(primary_key=True)
    tenant_id: Mapped[int] = mapped_column(ForeignKey("tenants.id"))
    call_log_id: Mapped[int | None] = mapped_column(ForeignKey("call_logs.id"), nullable=True)
    name: Mapped[str] = mapped_column(String(255))
    phone: Mapped[str] = mapped_column(String(32))
    status: Mapped[str] = mapped_column(String(32), default="new")  # new | qualified | rejected | converted
    external_crm_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    notes: Mapped[str] = mapped_column(Text, default="")
