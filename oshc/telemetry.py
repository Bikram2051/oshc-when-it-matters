"""Simple session telemetry stored in SQLite.

Events carry a random per-visit UUID, an event name and a page. They never carry
question text, bill content, names or policy details. ``track`` is the page-level
entry point: a telemetry failure must never interrupt a student flow, so it
swallows storage errors and returns False instead.
"""

from __future__ import annotations

import sqlite3
import uuid
from contextlib import closing
from datetime import UTC, datetime
from pathlib import Path

from oshc.config import EVENTS_DB
from oshc.schemas import Event, EventName

_SCHEMA = """
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


def record(event: Event, db_path: Path | None = None) -> None:
    """Append one event to SQLite."""

    path = Path(db_path or EVENTS_DB)
    path.parent.mkdir(parents=True, exist_ok=True)

    with closing(sqlite3.connect(path)) as db, db:
        db.execute(_SCHEMA)
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


def session_id(state) -> str:
    """Return the random per-visit id held in Streamlit session state."""
    if not isinstance(state.get("telemetry_session_id"), str):
        state["telemetry_session_id"] = str(uuid.uuid4())
    return state["telemetry_session_id"]


def track(state, page: str, name: EventName, *, once_key: str | None = None) -> bool:
    """Record one page event for this visit; never raise into the student flow.

    ``once_key`` makes the event idempotent across Streamlit reruns, which is how
    a page OPEN is counted once per visit rather than once per click.
    """
    if once_key is not None and state.get(once_key):
        return False
    try:
        record(Event(session_id=session_id(state), name=name,
                     at=datetime.now(UTC), page=page))
    except (OSError, sqlite3.Error, ValueError):
        return False
    if once_key is not None:
        state[once_key] = True
    return True


def summary(db_path: Path | None = None) -> dict[str, dict[str, int]]:
    """Count distinct visits per page and event name. Empty when nothing is recorded."""
    path = Path(db_path or EVENTS_DB)
    if not path.is_file():
        return {}
    try:
        with closing(sqlite3.connect(f"file:{path}?mode=ro", uri=True)) as db:
            rows = db.execute(
                "SELECT page, name, COUNT(DISTINCT session_id) FROM events GROUP BY page, name"
            ).fetchall()
    except sqlite3.Error:
        return {}
    counts: dict[str, dict[str, int]] = {}
    for page, name, visits in rows:
        counts.setdefault(page, {})[name] = int(visits)
    return counts
