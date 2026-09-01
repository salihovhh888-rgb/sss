#!/usr/bin/env python3
"""Создать таблицы БД для локальной разработки (см. app/storage/db.py).

Использование:
    cd backend && python scripts/init_db.py
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.storage.db import engine, init_db  # noqa: E402


def main() -> None:
    init_db()
    print(f"Таблицы созданы в {engine.url}")


if __name__ == "__main__":
    main()
