"""Simple session telemetry stored in SQLite."""

from __future__ import annotations

import sqlite3

from oshc.config import EVENTS_DB
from oshc.schemas import Event


def record(event: Event) -> None:
    """Append one event to SQLite."""

    EVENTS_DB.parent.mkdir(parents=True, exist_ok=True)

    with sqlite3.connect(EVENTS_DB) as db:
        db.execute(
            """
            CREATE TABLE IF NOT EXISTS events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL,
                name TEXT NOT NULL,
                at TEXT NOT NULL,
                page TEXT NOT NULL,
                code TEXT,
                detail TEXT
            )
            """
        )

        db.execute(
            """
            INSERT INTO events (
                session_id,
                name,
                at,
                page,
                code,
                detail
            )
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                event.session_id,
                event.name.value,
                event.at.isoformat(),
                event.page,
                event.code.value if event.code else None,
                event.detail,
            ),
        )
