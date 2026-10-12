"""Rehearse authored lessons against the frozen PDF, without provider access."""
import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from streamlit.testing.v1 import AppTest  # noqa: E402
from oshc.coach_lessons import LESSONS, verified_sources  # noqa: E402
from oshc.llm_budget import Budget  # noqa: E402
from oshc.policy_source import SOURCE_SHA256  # noqa: E402
from scripts.prototype_check_policy_source import fingerprints  # noqa: E402


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", default="docs/prototype/coach_ui_check.json")
    output = ROOT / parser.parse_args().out
    if output.exists():
        raise SystemExit("The Coach check report already exists. Keep it for review.")
    if os.getenv("OSHC_OFFLINE") != "1" or os.getenv("OSHC_ENABLE_LIVE") != "0":
        raise SystemExit("Run with OSHC_OFFLINE=1 and OSHC_ENABLE_LIVE=0.")
    budget = Budget()
    before_budget, before_files = budget.status(), fingerprints()
    checks = []
    with patch("oshc.llm._client", side_effect=AssertionError("Unexpected provider access")) as provider:
        sources = verified_sources(ROOT)
        at = AppTest.from_file(str(ROOT / "app/Home.py"), default_timeout=25).run()
        at.button(key="home_coach").click().run()
        assert not at.exception and not at.error
        assert at.title[0].value == "Journey Coach"
        # Pin AppTest's page for subsequent widget reruns after programmatic navigation.
        at.switch_page("pages/1_Journey_Coach.py").run()
        for lesson in LESSONS:
            at.selectbox(key="jc_moment").select(lesson.moment).run()
            assert at.radio(key="jc_choice").value is None
            assert at.button(key="jc_check").disabled
            assert any(text.value == sources[lesson.ident].text for text in at.text)
            wrong = (lesson.correct + 1) % len(lesson.options)
            at.radio(key="jc_choice").set_value(lesson.options[wrong]).run()
            at.button(key="jc_check").click().run()
            assert at.warning and not at.success
            at.radio(key="jc_choice").set_value(lesson.options[lesson.correct]).run()
            at.button(key="jc_check").click().run()
            assert not at.exception and not at.error and at.success
            record = at.session_state["jc_progress"][lesson.ident]
            assert record["first"] == wrong and record["attempts"] == 2 and record["passed"]
            checks.append({"lesson": lesson.ident, "pdf_page": lesson.page,
                           "column": lesson.column, "source_anchors_found": True,
                           "wrong_then_correct_feedback": True, "first_attempt_preserved": True})
            print(f"{lesson.moment}: PASS; source page {lesson.page}, feedback and retry history")

        at.button(key="jc_source").click().run()
        assert not at.exception and not at.error
        assert at.title[0].value == "Navigator"
        assert at.number_input(key="nv_page").value == 28
        assert len(at.image) == 1
        at.switch_page("pages/1_Journey_Coach.py").run()
        assert len(at.session_state["jc_progress"]) == 3
        at.button(key="jc_reset").click().run()
        assert not at.exception and "jc_progress" not in at.session_state
        assert at.radio(key="jc_choice").value is None
        provider.assert_not_called()

    if before_budget != budget.status() or before_files != fingerprints():
        raise AssertionError("A protected file or the spending ledger changed.")
    report = {
        "checked_at_utc": datetime.now(timezone.utc).isoformat(),
        "scope": "Engineering rehearsal of authored lessons; no real learner evaluation.",
        "source_sha256": SOURCE_SHA256, "lesson_checks": checks,
        "home_navigation": True, "navigator_page_handoff": True,
        "progress_reset": True, "progress_storage": "Streamlit session only",
        "learning_effectiveness_measured": False, "additional_api_calls": 0,
        "protected_files_unchanged": True, "budget_unchanged": True,
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("x", encoding="utf-8", newline="\n") as handle:
        json.dump(report, handle, indent=2)
        handle.write("\n")
    print("Home -> Coach -> original source in Navigator: PASS")
    print("Practice reset: PASS")
    print("Additional API calls: 0; protected files and budget unchanged.")
    print("Budget:", json.dumps(budget.status(), indent=2))
    print("Wrote:", output)


if __name__ == "__main__":
    main()
