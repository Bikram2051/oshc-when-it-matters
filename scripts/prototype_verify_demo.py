"""Verify a copied demo without credentials, a spending ledger or provider access."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import sys
from datetime import UTC, datetime
from importlib.metadata import version
from pathlib import Path, PurePosixPath

REQUIRED_CHECKS = {"home_coach_source_handoff", "three_bill_flows_and_comparisons",
                   "dashboard_scope", "guarded_student_chat", "offline_cache_miss_blocked"}


def signature(path):
    digest = hashlib.sha256()
    size = 0
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
            size += len(block)
    return {"sha256": digest.hexdigest(), "bytes": size}


def safe_path(root, name):
    relative = PurePosixPath(name)
    if not name or "\\" in name or ":" in name or relative.is_absolute() or ".." in relative.parts:
        raise ValueError("Invalid package path.")
    path = root / name
    if path.is_symlink() or not path.resolve().is_relative_to(root.resolve()):
        raise ValueError("Linked or external package file.")
    return path


def verify_files(root, sealed=True):
    manifest = json.loads((root / "package_manifest.json").read_text(encoding="utf-8"))
    if manifest.get("format") != 1 or (sealed and manifest.get("sealed") is not True):
        raise ValueError("The package has not been sealed.")
    for name, expected in manifest["files"].items():
        if signature(safe_path(root, name)) != expected:
            raise ValueError(f"Package file changed: {name}")
    if sealed:
        actual = {p.relative_to(root).as_posix() for p in root.rglob("*") if p.is_file()}
        if actual != set(manifest["files"]) | {"package_manifest.json"}:
            raise ValueError("The package contains missing or unlisted files.")
    return manifest


def environment():
    return {"python": platform.python_version(), "system": platform.system(),
            "machine": platform.machine(), "implementation": platform.python_implementation()}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--integrity-only", action="store_true")
    parser.add_argument("--out", type=Path)
    args = parser.parse_args()
    root = Path(__file__).resolve().parent
    manifest = verify_files(root)
    if environment() != manifest["environment"]:
        raise SystemExit("Use the Python version, OS and architecture recorded in package_manifest.json.")
    for name, expected in manifest["dependencies"].items():
        if version(name) != expected:
            raise SystemExit(f"Installed dependency differs: {name}")
    if not sys.flags.isolated or not sys.dont_write_bytecode or sys.prefix == sys.base_prefix:
        raise SystemExit("Run the packaged virtual-environment Python with -I -B.")
    if (root / ".env").exists() or (root / "data/private_runtime").exists():
        raise SystemExit("Credentials or private runtime files must not be included.")
    if args.integrity_only:
        print("Package integrity and installed versions: PASS")
        return
    if args.out is None or args.out.exists() or args.out.resolve().is_relative_to(root):
        raise SystemExit("Provide a new --out path outside the package folder.")

    os.environ.update(OSHC_OFFLINE="1", OSHC_ENABLE_LIVE="0",
                      OSHC_MODEL="claude-haiku-4-5-20251001",
                      STREAMLIT_BROWSER_GATHER_USAGE_STATS="false")
    for name in ("OSHC_API_KEY", "ANTHROPIC_API_KEY"):
        os.environ.pop(name, None)
    os.chdir(root)
    sys.path.insert(0, str(root))
    from unittest.mock import patch

    from streamlit.testing.v1 import AppTest

    import oshc.llm as adapter
    from oshc.coach_lessons import LESSONS

    if Path(adapter.__file__).resolve().parent != root / "oshc":
        raise AssertionError("The app was imported from outside the copied package.")
    manifest_sha = signature(root / "package_manifest.json")["sha256"]
    checks = {}
    with patch.object(adapter, "_client", side_effect=AssertionError("Provider access attempted")) as provider, \
         patch.object(adapter, "Budget", side_effect=AssertionError("Spending ledger accessed")) as ledger:
        at = AppTest.from_file(str(root / "app/Home.py"), default_timeout=30).run()
        assert not at.exception and not at.error
        assert any("Your OSHC," in item.proto.body for item in at.get("html"))
        at.switch_page("views/1_Journey_Coach.py").run()
        assert not at.exception and at.title[0].value == "Journey Coach"
        lesson = LESSONS[2]
        at.segmented_control(key="jc_moment").select(lesson.moment).run()
        for index in ((lesson.correct + 1) % len(lesson.options), lesson.correct):
            at.radio(key="jc_choice").set_value(lesson.options[index]).run()
            at.button(key="jc_check").click().run()
            assert not at.exception and not at.error
        assert at.success and at.session_state["jc_progress"][lesson.ident]["attempts"] == 2
        at.button(key="jc_source").click().run()
        assert not at.exception and not at.error and at.number_input(key="nv_page").value == 28
        assert len(at.image) == 1
        checks["home_coach_source_handoff"] = True
        print("Home -> Coach -> original PDF page 28: PASS", flush=True)

        at.switch_page("views/3_Bill_Explainer.py").run()
        for label in ("GP visit: text example", "GP visit: PDF example", "GP visit: saved AI reading"):
            at.selectbox(key="be_example").select(label).run()
            at.button(key="be_read").click().run()
            assert not at.exception and not at.error
            assert [m.value for m in at.metric] == ["AUD 105.00", "Not shown", "Not shown"]
            at.toggle(key="be_compare").set_value(True).run()
            at.selectbox(key="be_basis_1").select("Published 100% benefit").run()
            assert not at.exception and not at.error
            assert at.dataframe[1].value.iloc[0]["Illustrative difference"] == "AUD 44.95"
            assert len(at.metric) == 3 and any("Total unavailable" in item.value for item in at.info)
            at.button(key="be_clear").click().run()
            assert not at.exception and not at.metric
            print(label + ": PASS", flush=True)
        checks["three_bill_flows_and_comparisons"] = True
        at.selectbox(key="be_example").select("Paid receipt: dated service lines").run()
        at.button(key="be_read").click().run()
        assert not at.exception and at.metric[0].value == "AUD 245.00"
        retained = at.session_state["be_result"]
        assert "text" not in retained and retained["result"]["provider"] is None
        assert retained["receipt"]["amount_settled"] == 245
        assert retained["receipt"]["balance_remaining"] == 0
        assert retained["result"]["total_benefit"] is None
        at.button(key="be_clear").click().run()
        at.switch_page("views/4_Ask.py").run()
        assert not at.exception and not at.error and at.session_state["ask_history"] == []
        at.button(key="ask_s1").click().run()
        assert not at.exception and not at.error
        assert len(at.session_state["ask_history"]) == 1
        assert at.session_state["ask_history"][0]["response"].status == "answered"
        assert at.session_state["ask_history"][0]["response"].answer
        at.run()
        assert not at.exception and len(at.session_state["ask_history"]) == 1
        at.button(key="ask_clear").click().run()
        # A blocked turn must never open the source, even in the packaged app.
        with patch("oshc.ask_ui.load_source", side_effect=AssertionError("Blocked source access")) as source:
            at.chat_input(key="ask_box").set_value("am I covered for physio").run()
            assert not at.exception and at.error
            response = at.session_state["ask_history"][0]["response"]
            assert response.decision.blocked and not response.hits and not response.safe_to_echo
            source.assert_not_called()
        at.button(key="ask_clear").click().run()
        assert not at.exception and at.session_state["ask_history"] == []
        checks["guarded_student_chat"] = True
        print("Guarded chat -> source passage -> blocked request -> clear: PASS", flush=True)

        at.switch_page("views/5_Dashboard.py").run()
        assert not at.exception and not at.error and not at.warning
        assert at.metric[0].value == "7 of 7"
        assert at.metric[1].value == "1 of 6"
        assert {tab.label for tab in at.tabs} == {"Overview", "Results", "Safety", "Evidence & sources"}
        assert set(at.dataframe[1].value["Status"]) == {"Not linked here", "Recorded result"}
        from oshc.final_results import load_final
        final = load_final(root)
        assert final is not None and final["classifier_n"] == 53
        release = json.loads((root / "docs/prototype/release_summary_2026-10-15.json").read_text(encoding="utf-8"))
        for row in release["runtime_files"]:
            assert signature(root / row["path"])["sha256"] == row["sha256"]
        assert final["release_chat"]["refusal_recall"]["n"] == 24
        assert any(m.label == "Unseen false refusals" for m in at.metric)
        assert any(m.label == "Development refusal recall" for m in at.metric)
        assert any(m.label == "TF-IDF + logistic regression" for m in at.metric)
        checks["dashboard_scope"] = True
        try:
            adapter.complete("Packaged offline cache miss check", max_tokens=16)
        except adapter.CacheMiss:
            pass
        else:
            raise AssertionError("Expected an offline cache miss.")
        provider.assert_not_called()
        ledger.assert_not_called()
        checks["offline_cache_miss_blocked"] = True
    assert set(checks) == REQUIRED_CHECKS
    verify_files(root)
    if signature(root / "package_manifest.json")["sha256"] != manifest_sha:
        raise AssertionError("Package manifest changed during the check.")
    report = {"checked_at_utc": datetime.now(UTC).isoformat(),
              "scope": "Fresh-environment demo integration check; not independent accuracy evaluation.",
              "source_commit": manifest["source_commit"], "environment": environment(),
              "manifest_sha256": manifest_sha, "checks": checks,
              "provider_calls": 0, "ledger_accesses": 0, "package_files_unchanged": True}
    with args.out.open("x", encoding="utf-8", newline="\n") as handle:
        json.dump(report, handle, indent=2)
        handle.write("\n")
    print("Fresh-environment demo: PASS; no provider calls or spending-ledger access.")
    print("Wrote:", args.out)


if __name__ == "__main__":
    main()
