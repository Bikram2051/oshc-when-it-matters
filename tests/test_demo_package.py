"""Package-boundary tests with synthetic metadata and files, not real invoices."""
import json
import zipfile
from types import SimpleNamespace

import pytest

from scripts import prototype_demo_package as builder
from scripts.prototype_verify_demo import safe_path, signature, verify_files


def test_runtime_inventory_covers_every_local_import():
    required = builder.runtime_imports(builder.ROOT, builder.FILES)
    assert not required - set(builder.FILES), sorted(required - set(builder.FILES))


def test_inventory_includes_current_pages_theme_and_named_evidence():
    assert {
        "oshc/home_ui.py", "oshc/ask_ui.py", "oshc/student_chat.py", "oshc/guardrail.py",
        "oshc/config.py", "oshc/project_progress.py", ".streamlit/config.toml",
        "data/agreement/agreement_2026-10-13.json",
        "docs/prototype/seminar_guardrail_summary_2026-10-05.json",
        "docs/prototype/ask_ui_check.json",
    } <= set(builder.FILES)
    assert len(builder.FILES) == len(set(builder.FILES))
    assert not any("heldout" in name or "data/probes/" in name or "private" in name
                   or name.startswith("seminar/") for name in builder.FILES)
    assert set(builder.SOURCE_HASHES) == {
        "corpus/Medibank_OSHC_Member_Guide.pdf", "corpus/MBS-XML-20260801.XML",
    }


def test_import_discovery_covers_nested_and_package_member_imports(tmp_path):
    for name, text in {
        "oshc/__init__.py": "",
        "oshc/helper.py": "",
        "oshc/other.py": "",
        "oshc/group/__init__.py": "",
        "oshc/group/child.py": "from .. import other\n",
        "app/Home.py": "def later():\n    from oshc.group import child\n    import oshc.helper\n",
    }.items():
        path = tmp_path / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
    assert builder.runtime_imports(tmp_path, ("app/Home.py", "oshc/group/child.py")) == {
        "oshc/__init__.py", "oshc/helper.py", "oshc/group/__init__.py", "oshc/group/child.py",
        "oshc/other.py",
    }


def test_agreement_export_contains_only_validated_aggregate_fields(tmp_path):
    metric = {"kappa": 0.4, "ci_low": 0.2, "ci_high": 0.6, "n": 53,
              "private_extra": "PRIVATE-SENTINEL"}
    record = {"computed_at_utc": "2026-10-13T01:00:00+00:00", "n": 53,
              "results": {"Gap": dict(metric), "Code 1": dict(metric)},
              "coders": ["PRIVATE-SENTINEL"],
              "disagreements": [{"id": "PRIVATE-SENTINEL"}]}
    path = tmp_path / "agreement.json"
    path.write_text(json.dumps(record), encoding="utf-8")
    exported = builder.agreement_payload(path)
    assert b"PRIVATE-SENTINEL" not in exported
    value = json.loads(exported)
    assert set(value) == {"computed_at_utc", "n", "results"}
    assert set(value["results"]) == {"Gap", "Code 1"}
    assert all(set(row) == {"kappa", "ci_low", "ci_high", "n"}
               for row in value["results"].values())
    record["results"]["Gap"]["n"] = 1
    path.write_text(json.dumps(record), encoding="utf-8")
    with pytest.raises(ValueError):
        builder.agreement_payload(path)


def distribution(number="1.0", requires=(), direct=None):
    return SimpleNamespace(version=number, requires=requires, read_text=lambda _: direct)


def test_lock_includes_transitive_extras_and_handles_cycles():
    installed = {
        "a": distribution(requires=("b[extra]>=1", "unused; python_version < '0'")),
        "b": distribution(requires=("a", "c; extra == 'extra'")),
        "c": distribution(),
    }
    assert builder.installed_lock(("a",), installed.__getitem__) == {"a": "1.0", "b": "1.0", "c": "1.0"}


def test_incompatible_installed_dependency_is_rejected():
    with pytest.raises(ValueError, match="does not satisfy"):
        builder.installed_lock(("a>=2",), lambda _: distribution())


def test_local_install_is_not_silently_pinned_as_a_public_package():
    with pytest.raises(ValueError, match="needs review"):
        builder.installed_lock(("a",), lambda _: distribution(direct="synthetic metadata"))


@pytest.mark.parametrize("name", ("../outside", "/outside", "C:/outside", "folder\\outside"))
def test_paths_cannot_escape_package(tmp_path, name):
    with pytest.raises(ValueError):
        safe_path(tmp_path, name)


def manifest(root, sealed=True):
    (root / "example.txt").write_text("synthetic example", encoding="utf-8")
    value = {"format": 1, "sealed": sealed, "source_commit": "a" * 40,
             "dependencies": {"demo-lib": "1.0"},
             "files": {"example.txt": signature(root / "example.txt")}}
    builder.write_json(root / "package_manifest.json", value)
    return value


def test_changed_payload_fails_integrity(tmp_path):
    manifest(tmp_path)
    (tmp_path / "example.txt").write_text("changed", encoding="utf-8")
    with pytest.raises(ValueError, match="changed"):
        verify_files(tmp_path)


def test_unlisted_payload_fails_integrity(tmp_path):
    manifest(tmp_path)
    (tmp_path / "unexpected.txt").write_text("extra", encoding="utf-8")
    with pytest.raises(ValueError, match="unlisted"):
        verify_files(tmp_path)


def test_sealing_hashes_the_selected_wheel(tmp_path):
    manifest(tmp_path, sealed=False)
    folder = tmp_path / "wheelhouse"
    folder.mkdir()
    wheel = folder / "demo_lib-1.0-py3-none-any.whl"
    wheel.write_bytes(b"synthetic fixture, not an installable wheel")
    builder.seal(tmp_path)
    value = verify_files(tmp_path)
    assert value["sealed"] is True
    assert signature(wheel)["sha256"] in (tmp_path / "requirements.lock").read_text()


def test_sealing_rejects_a_different_wheel_version(tmp_path):
    manifest(tmp_path, sealed=False)
    folder = tmp_path / "wheelhouse"
    folder.mkdir()
    (folder / "demo_lib-2.0-py3-none-any.whl").write_bytes(b"synthetic fixture")
    with pytest.raises(ValueError, match="Unexpected wheel"):
        builder.seal(tmp_path)


def test_build_copies_only_allowlisted_files(tmp_path, monkeypatch):
    root, output = tmp_path / "source", tmp_path / "export"
    metric = {"kappa": 0.4, "ci_low": 0.2, "ci_high": 0.6, "n": 53}
    agreement = {"computed_at_utc": "2026-10-13T01:00:00+00:00", "n": 53,
                 "results": {"Gap": dict(metric), "Code 1": dict(metric)},
                 "disagreements": [{"id": "PRIVATE-SENTINEL"}]}
    for name, text in {"app/Home.py": "# synthetic app\n", ".env": "SENTINEL",
                       "data/private_runtime/ledger": "SENTINEL",
                       "scripts/prototype_verify_demo.py": "# synthetic verifier\n",
                       "docs/prototype/Start_Demo.ps1": "# synthetic launcher\n",
                       "docs/prototype/demo_package.md": "Synthetic readme\n",
                       builder.AGREEMENT_FILE: json.dumps(agreement)}.items():
        path = root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
    monkeypatch.setattr(builder, "ROOT", root)
    monkeypatch.setattr(builder, "FILES", ("app/Home.py", builder.AGREEMENT_FILE))
    monkeypatch.setattr(builder, "SOURCE_HASHES", {})
    monkeypatch.setattr(builder, "installed_lock", lambda: {"demo-lib": "1.0"})
    monkeypatch.setattr(builder, "git", lambda *args: "\n".join(builder.FILES)
                        if args[0] == "ls-files" else "a" * 40)
    builder.build(output)
    assert not (output / ".env").exists() and not (output / "data/private_runtime").exists()
    assert (output / "app/Home.py").read_bytes() == (root / "app/Home.py").read_bytes()
    assert "PRIVATE-SENTINEL" not in (output / builder.AGREEMENT_FILE).read_text()
    assert "PRIVATE-SENTINEL" in (root / builder.AGREEMENT_FILE).read_text()
    exported = json.loads((output / "package_manifest.json").read_text())
    assert exported["aggregate_only_exports"] == [builder.AGREEMENT_FILE]
    before = signature(output / "package_manifest.json")
    with pytest.raises(ValueError, match="new output"):
        builder.build(output)
    assert signature(output / "package_manifest.json") == before


def test_build_rejects_a_missing_local_import_before_creating_output(tmp_path, monkeypatch):
    root, output = tmp_path / "source", tmp_path / "export"
    for name, text in {"app/Home.py": "from oshc.helper import main\n",
                       "oshc/__init__.py": "", "oshc/helper.py": "def main(): pass\n"}.items():
        path = root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
    monkeypatch.setattr(builder, "ROOT", root)
    monkeypatch.setattr(builder, "FILES", ("app/Home.py",))
    with pytest.raises(ValueError, match="Runtime imports missing"):
        builder.build(output)
    assert not output.exists()


def test_archive_requires_matching_fresh_environment_proof(tmp_path):
    package = tmp_path / "package"
    package.mkdir()
    manifest(package)
    proof = tmp_path / "proof.json"
    proof.write_text(json.dumps({"manifest_sha256": "wrong"}), encoding="utf-8")
    with pytest.raises(ValueError, match="proof does not match"):
        builder.archive(package, proof)
    assert not (tmp_path / "NextBest-demo.zip").exists()


def test_archive_contains_only_verified_package_files(tmp_path, monkeypatch):
    package = tmp_path / "package"
    package.mkdir()
    value = manifest(package)
    root = tmp_path / "repo"
    (root / "docs/prototype").mkdir(parents=True)
    monkeypatch.setattr(builder, "ROOT", root)
    proof = tmp_path / "proof.json"
    builder.write_json(proof, {
        "manifest_sha256": signature(package / "package_manifest.json")["sha256"],
        "source_commit": value["source_commit"], "provider_calls": 0, "ledger_accesses": 0,
        "package_files_unchanged": True,
        "checks": dict.fromkeys(("home_coach_source_handoff", "three_bill_flows_and_comparisons",
                                 "dashboard_scope", "guarded_student_chat",
                                 "offline_cache_miss_blocked"), True),
    })
    builder.archive(package, proof)
    target = tmp_path / "NextBest-demo.zip"
    with zipfile.ZipFile(target) as bundle:
        assert bundle.testzip() is None
        assert set(bundle.namelist()) == {"NextBest-demo/example.txt", "NextBest-demo/package_manifest.json"}
    report = json.loads((root / "docs/prototype/demo_package_check.json").read_text())
    assert report["archive_sha256"] == signature(target)["sha256"]


def test_new_archive_report_preserves_previous_evidence(tmp_path, monkeypatch):
    package = tmp_path / "package"
    package.mkdir()
    value = manifest(package)
    root = tmp_path / "repo"
    report_folder = root / "docs/prototype"
    report_folder.mkdir(parents=True)
    legacy = report_folder / "demo_package_check.json"
    legacy.write_bytes(b"PREVIOUS-EVIDENCE")
    monkeypatch.setattr(builder, "ROOT", root)
    proof = tmp_path / "proof.json"
    builder.write_json(proof, {
        "manifest_sha256": signature(package / "package_manifest.json")["sha256"],
        "source_commit": value["source_commit"], "provider_calls": 0, "ledger_accesses": 0,
        "package_files_unchanged": True, "checks": dict.fromkeys(builder.REQUIRED_CHECKS, True),
    })
    report = report_folder / "demo_package_final_check.json"
    builder.archive(package, proof, report=report)
    assert legacy.read_bytes() == b"PREVIOUS-EVIDENCE"
    assert json.loads(report.read_text())["archive_sha256"] == signature(
        tmp_path / "NextBest-demo.zip")["sha256"]
