"""Shared test isolation."""
import pytest

import oshc.telemetry as telemetry


@pytest.fixture(autouse=True)
def isolated_events(tmp_path, monkeypatch):
    """Keep page telemetry from UI tests out of the repository's data folder."""
    path = tmp_path / "events.sqlite"
    monkeypatch.setattr(telemetry, "EVENTS_DB", path)
    return path
