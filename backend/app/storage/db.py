"""Настройка SQLAlchemy engine/session из конфигурации приложения.

По умолчанию (см. app/config.py) используется локальный SQLite-файл для
разработки. В проде — Postgres на сервере в Узбекистане, см.
docs/compliance.md (требование локализации персональных данных).
"""

from __future__ import annotations

from collections.abc import Generator

from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.config import get_settings
from app.storage.models import Base


def make_engine(database_url: str | None = None) -> Engine:
    url = database_url or get_settings().database_url
    connect_args = {"check_same_thread": False} if url.startswith("sqlite") else {}
    return create_engine(url, connect_args=connect_args)


engine = make_engine()
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


def init_db(bind: Engine | None = None) -> None:
    """Создать все таблицы (для локальной разработки; в проде — миграции)."""
    Base.metadata.create_all(bind=bind or engine)


def get_db() -> Generator[Session, None, None]:
    """FastAPI-зависимость: сессия БД на один запрос."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
