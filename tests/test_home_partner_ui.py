"""Home journey, deep links and the partner page: no provider, no student text."""
from pathlib import Path
from unittest.mock import Mock

import pytest
from streamlit.testing.v1 import AppTest

import oshc.llm as adapter
from oshc.coach_lessons import LESSONS
from oshc.home_ui import journey_stops
from oshc.partner_ui import link_rows
from oshc.ui_style import TEAM

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(autouse=True)
def no_provider(monkeypatch):
    provider = Mock(side_effect=AssertionError("Unexpected provider access"))
    monkeypatch.setattr(adapter, "_client", provider)
    yield
    provider.assert_not_called()


def test_journey_runs_in_student_order_and_links_each_moment():
    stops = journey_stops()
    assert [stop[0] for stop in stops] == [*(lesson.moment for lesson in LESSONS),
                                           "Seeing a doctor", "Holding a bill"]
    assert [stop[3] for stop in stops[:3]] == [{"moment": "before-you-arrive"},
                                               {"moment": "settling-in"},
                                               {"moment": "before-an-appointment"}]
    assert stops[3][3] == {"task": "gp"}


def test_home_is_links_not_buttons_and_shows_emergency_numbers():
    at = AppTest.from_file(str(ROOT / "app/Home.py"), default_timeout=15).run()
    assert not at.exception and not at.error
    assert not at.button, "Home navigates with links so each one can be shared or opened in a tab"
    html = " ".join(item.proto.body for item in at.get("html"))
    assert "<strong>000</strong>" in html and "1800&nbsp;022&nbsp;222" in html
    assert html.count("<h1") == 1 and "Your OSHC," in html
    assert not any("Project dashboard" in item.value for item in at.markdown)


def test_sidebar_credits_the_team_under_the_logo():
    at = AppTest.from_file(str(ROOT / "app/Home.py"), default_timeout=15).run()
    html = " ".join(item.proto.body for item in at.sidebar.get("html"))
    for name, role in TEAM:
        assert name in html and role in html
    for logo in ("logo.svg", "mark.svg"):
        svg = (ROOT / "app/static/brand" / logo).read_text(encoding="utf-8")
        assert 'aria-label="OSHC When It Matters"' in svg and "#D50032" in svg


def test_partner_links_cover_every_moment_with_relative_paths():
    rows = link_rows()
    assert [row[2] for row in rows] == [
        "/Journey_Coach?moment=before-you-arrive",
        "/Journey_Coach?moment=settling-in",
        "/Journey_Coach?moment=before-an-appointment",
        "/Navigator?task=gp",
        "/Bill_Explainer",
        "/Ask",
    ]
    assert all(row[2].startswith("https://oshc.example") for row in link_rows("https://oshc.example"))


def test_partner_page_renders_links_and_content_free_measures(isolated_events):
    at = AppTest.from_file(str(ROOT / "app/Home.py"), default_timeout=15).run()
    at.switch_page("views/6_Partners.py").run()
    assert not at.exception and not at.error
    assert at.title[0].value == "For partners"
    links = next(item.value for item in at.markdown if "moment=before-you-arrive" in item.value)
    assert "task=gp" in links and "Offer letter or pre-departure email" in links
    labels = {metric.label: metric.value for metric in at.metric}
    assert labels == {"Coach visits": "0", "Started a scenario": "0",
                      "Answered correctly": "0", "Read a bill": "0"}


@pytest.mark.parametrize("slug,service", [("gp", "GP appointment"), ("pharmacy", "Pharmacy"),
                                          ("claim", "Making a claim")])
def test_navigator_deep_link_opens_the_named_task(slug, service):
    at = AppTest.from_file(str(ROOT / "app/Home.py"), default_timeout=15)
    at.query_params["task"] = slug
    at.run()
    at.switch_page("views/2_Navigator.py").run()
    assert not at.exception
    assert at.selectbox(key="nv_service").value == service
