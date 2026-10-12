"""Package-boundary tests with synthetic metadata and files, not real invoices."""
import json
import zipfile
from types import SimpleNamespace

import pytest

from scripts import prototype_demo_package as builder
from scripts.prototype_verify_demo import safe_path, signature, verify_files


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
    for name, text in {"app/Home.py": "# synthetic app\n", ".env": "SENTINEL",
                       "data/private_runtime/ledger": "SENTINEL",
                       "scripts/prototype_verify_demo.py": "# synthetic verifier\n",
                       "docs/prototype/Start_Demo.ps1": "# synthetic launcher\n",
                       "docs/prototype/demo_package.md": "Synthetic readme\n"}.items():
        path = root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
    monkeypatch.setattr(builder, "ROOT", root)
    monkeypatch.setattr(builder, "FILES", ("app/Home.py",))
    monkeypatch.setattr(builder, "SOURCE_HASHES", {})
    monkeypatch.setattr(builder, "installed_lock", lambda: {"demo-lib": "1.0"})
    monkeypatch.setattr(builder, "git", lambda *args: "app/Home.py" if args[0] == "ls-files" else "a" * 40)
    builder.build(output)
    assert not (output / ".env").exists() and not (output / "data/private_runtime").exists()
    assert (output / "app/Home.py").read_bytes() == (root / "app/Home.py").read_bytes()
    before = signature(output / "package_manifest.json")
    with pytest.raises(ValueError, match="new output"):
        builder.build(output)
    assert signature(output / "package_manifest.json") == before


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
                                 "dashboard_scope", "offline_cache_miss_blocked"), True),
    })
    builder.archive(package, proof)
    target = tmp_path / "NextBest-demo.zip"
    with zipfile.ZipFile(target) as bundle:
        assert bundle.testzip() is None
        assert set(bundle.namelist()) == {"NextBest-demo/example.txt", "NextBest-demo/package_manifest.json"}
    report = json.loads((root / "docs/prototype/demo_package_check.json").read_text())
    assert report["archive_sha256"] == signature(target)["sha256"]
