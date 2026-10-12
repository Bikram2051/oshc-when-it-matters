"""Verify a copied demo without credentials, a spending ledger or provider access."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import sys
from datetime import datetime, timezone
from importlib.metadata import version
from pathlib import Path, PurePosixPath


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
        assert at.title[0].value == "NextBest"
        at.button(key="home_coach").click().run()
        assert not at.exception and at.title[0].value == "Journey Coach"
        at.switch_page("pages/1_Journey_Coach.py").run()
        lesson = LESSONS[2]
        at.selectbox(key="jc_moment").select(lesson.moment).run()
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

        at.switch_page("pages/3_Bill_Explainer.py").run()
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
        at.switch_page("pages/4_Dashboard.py").run()
        assert not at.exception and not at.error and not at.warning
        assert at.metric[0].value == "6 of 6"
        assert set(at.dataframe[1].value["Status"]) == {"Not linked here"}
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
    verify_files(root)
    if signature(root / "package_manifest.json")["sha256"] != manifest_sha:
        raise AssertionError("Package manifest changed during the check.")
    report = {"checked_at_utc": datetime.now(timezone.utc).isoformat(),
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
