"""Session telemetry: counts visits and events, never content, and never breaks a page."""
import sqlite3
from datetime import datetime, timezone

import pytest

import oshc.telemetry as telemetry
from oshc.schemas import Event, EventName


def rows(path):
    with sqlite3.connect(path) as db:
        return db.execute("SELECT session_id, name, page, code, detail FROM events").fetchall()


def test_record_appends_one_row(isolated_events):
    telemetry.record(Event(session_id="s1", name=EventName.OPEN,
                           at=datetime.now(timezone.utc), page="coach"))
    assert rows(isolated_events) == [("s1", "open", "coach", None, None)]


def test_track_once_key_counts_a_page_open_once_per_visit(isolated_events):
    state = {}
    assert telemetry.track(state, "coach", EventName.OPEN, once_key="opened")
    assert not telemetry.track(state, "coach", EventName.OPEN, once_key="opened")
    assert len(rows(isolated_events)) == 1


def test_session_id_is_random_and_stable_within_a_visit():
    first, second = {}, {}
    assert telemetry.session_id(first) == telemetry.session_id(first)
    assert telemetry.session_id(first) != telemetry.session_id(second)


def test_storage_failure_never_raises_into_the_page(monkeypatch):
    def broken(*args, **kwargs):
        raise sqlite3.OperationalError("read-only")
    monkeypatch.setattr(telemetry, "record", broken)
    state = {}
    assert telemetry.track(state, "navigator", EventName.OPEN, once_key="opened") is False
    assert "opened" not in state


def test_rows_hold_no_free_text(isolated_events):
    state = {}
    telemetry.track(state, "explainer", EventName.DECODE_RUN)
    session, name, page, code, detail = rows(isolated_events)[0]
    assert (name, page, code, detail) == ("decode_run", "explainer", None, None)
    assert len(session) == 36


def test_summary_counts_distinct_visits(isolated_events):
    a, b = {}, {}
    for state in (a, b):
        telemetry.track(state, "coach", EventName.OPEN, once_key="o")
        telemetry.track(state, "coach", EventName.SCENARIO_START)
    telemetry.track(a, "coach", EventName.SCENARIO_START)
    telemetry.track(a, "coach", EventName.SCENARIO_COMPLETE)
    assert telemetry.summary(isolated_events) == {
        "coach": {"open": 2, "scenario_start": 2, "scenario_complete": 1}}


def test_summary_is_empty_without_a_database(tmp_path):
    assert telemetry.summary(tmp_path / "missing.sqlite") == {}


@pytest.mark.parametrize("page", ["coach", "navigator", "explainer"])
def test_pages_are_valid_event_pages(isolated_events, page):
    assert telemetry.track({}, page, EventName.OPEN)
