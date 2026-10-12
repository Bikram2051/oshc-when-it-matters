"""Exercise the Navigator with the actual verified guide, without provider access."""
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
from oshc.llm_budget import Budget  # noqa: E402
from oshc.navigator_ui import PAGE_VIEW, TOPICS  # noqa: E402
from oshc.policy_source import SOURCE_SHA256, build_corpus  # noqa: E402
from scripts.prototype_check_policy_source import fingerprints  # noqa: E402


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", default="docs/prototype/navigator_ui_check.json")
    output = ROOT / parser.parse_args().out
    if output.exists():
        raise SystemExit("The UI report already exists. Keep it for review.")
    if os.getenv("OSHC_OFFLINE") != "1" or os.getenv("OSHC_ENABLE_LIVE") != "0":
        raise SystemExit("Run with OSHC_OFFLINE=1 and OSHC_ENABLE_LIVE=0.")
    budget = Budget()
    before_budget, before_files = budget.status(), fingerprints()
    checks = []
    with patch("oshc.llm._client", side_effect=AssertionError("Unexpected provider access")) as provider:
        chunks = {chunk.chunk_id: chunk for chunk in build_corpus(ROOT).chunks}
        at = AppTest.from_file(str(ROOT / "app/Home.py"), default_timeout=25).run()
        at.switch_page("pages/2_Navigator.py").run()
        assert not at.exception and not at.error
        assert not at.chat_input and not at.text_input and not at.text_area
        for topic in TOPICS:
            at.selectbox(key="nv_topic").select(topic).run()
            assert not at.exception and not at.error
            chunk = chunks[at.selectbox(key="nv_match").value]
            assert any(text.value == chunk.text for text in at.text)
            assert any(f"#page={chunk.page})" in link.value for link in at.markdown)
            assert len(at.image) == 1 and len(at.get("download_button")) == 1
            assert at.image[0].captions == [f"Saved guide: physical PDF page {chunk.page} of 37"]
            checks.append({"topic": topic, "selected_chunk": chunk.chunk_id,
                           "pdf_page": chunk.page, "exact_source_text": True})
            print(f"{topic}: PASS; excerpt and original PDF page {chunk.page}")

        at.selectbox(key="nv_topic").select("Making a claim").run()
        claim_id = next(ident for ident, chunk in chunks.items()
                        if chunk.page == 28 and chunk.column == "right")
        at.selectbox(key="nv_match").select(claim_id).run()
        assert not at.exception and not at.error
        assert any(text.value == chunks[claim_id].text for text in at.text)
        assert any("#page=28)" in link.value for link in at.markdown)
        print("Choosing the claim instructions on page 28: PASS")

        at.radio(key="nv_view").set_value(PAGE_VIEW).run()
        assert at.number_input(key="nv_page").value == 19
        assert any("#page=19)" in link.value for link in at.markdown)
        assert len(at.image) == 1
        at.number_input(key="nv_page").set_value(20).run()
        assert not at.exception and not at.error
        assert any("#page=20)" in link.value for link in at.markdown)
        assert len(at.image) == 1
        provider.assert_not_called()
    if before_budget != budget.status() or before_files != fingerprints():
        raise AssertionError("A protected file or the spending ledger changed.")
    report = {
        "checked_at_utc": datetime.now(timezone.utc).isoformat(),
        "scope": "Source-browser engineering checks, not held-out retrieval or safety evaluation.",
        "source_sha256": SOURCE_SHA256, "topic_checks": checks,
        "claim_instructions_page_28": True, "table_page_19_available": True,
        "adjacent_page_navigation": True, "personal_question_input": False,
        "generated_answers": False, "additional_api_calls": 0,
        "protected_files_unchanged": True, "budget_unchanged": True,
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("x", encoding="utf-8", newline="\n") as handle:
        json.dump(report, handle, indent=2)
        handle.write("\n")
    print("Hospital table and adjacent-page browsing: PASS")
    print("Additional API calls: 0; protected files and budget unchanged.")
    print("Budget:", json.dumps(budget.status(), indent=2))
    print("Wrote:", output)


if __name__ == "__main__":
    main()
