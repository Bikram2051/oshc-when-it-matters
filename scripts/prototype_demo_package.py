"""Allowlisted Windows demo export. No provider or held-out access."""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import zipfile
from importlib.metadata import distribution
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from packaging.requirements import Requirement  # noqa: E402
from packaging.utils import canonicalize_name, parse_wheel_filename  # noqa: E402
from scripts.prototype_verify_demo import environment, signature, safe_path, verify_files  # noqa: E402

ROOT_PACKAGES = ("streamlit==1.64.0", "pydantic==2.13.5", "pymupdf==1.28.2",
                 "rank-bm25==0.2.2", "python-dotenv==1.2.3")
FILES = (
    "app/Home.py", "app/pages/1_Journey_Coach.py", "app/pages/2_Navigator.py",
    "app/pages/3_Bill_Explainer.py", "app/pages/4_Dashboard.py",
    "oshc/__init__.py", "oshc/billexplainer/__init__.py",
    "oshc/schemas.py", "oshc/llm.py", "oshc/llm_budget.py", "oshc/policy_source.py",
    "oshc/policy_search.py", "oshc/navigator_ui.py", "oshc/coach_lessons.py",
    "oshc/coach_ui.py", "oshc/evidence_dashboard.py", "oshc/dashboard_ui.py",
    "oshc/billexplainer/read.py", "oshc/billexplainer/extract_rules.py",
    "oshc/billexplainer/extract_llm.py", "oshc/billexplainer/mbs_reference.py",
    "oshc/billexplainer/ui.py", "data/demo_dev/rules_reader_example.txt",
    "data/demo_dev/rules_reader_example.pdf", "data/demo_dev/llm_reader_example.txt",
    "corpus/MANIFEST.csv", "corpus/Medibank_OSHC_Member_Guide.pdf",
    "corpus/MBS-XML-20260801.XML",
    "cache/llm/v2/79edc78aed0b2db4131b17dd5ff136e5e14f94371f7acdcc998e0ec85f8e4134.json",
) + tuple(f"docs/prototype/{name}_check.json" for name in (
    "bill_ui", "mbs_reference", "mbs_source", "policy_source", "navigator_ui", "coach_ui", "dashboard_ui"))
SOURCE_HASHES = {
    "corpus/Medibank_OSHC_Member_Guide.pdf": "6ca7151567ee2b61f8e6b50340c297d50deb249a013f055ef38f50ed07ec87c7",
    "corpus/MBS-XML-20260801.XML": "c5c04792cbdc7017589b4453aa4506f26b6cfcbfeaee3b0d6c866a8050b06565",
}


def write_json(path, value, mode="x"):
    with path.open(mode, encoding="utf-8", newline="\n") as handle:
        json.dump(value, handle, indent=2, sort_keys=True)
        handle.write("\n")


def installed_lock(roots=ROOT_PACKAGES, lookup=distribution):
    pending = [Requirement(value) for value in roots]
    locked, expanded = {}, set()
    while pending:
        request = pending.pop()
        name = canonicalize_name(request.name)
        if request.url:
            raise ValueError(f"Direct URL dependency needs review: {name}")
        item = lookup(name)
        if item.read_text("direct_url.json"):
            raise ValueError(f"Local, VCS or direct installation needs review: {name}")
        if request.specifier and not request.specifier.contains(item.version, prereleases=True):
            raise ValueError(f"Installed version does not satisfy a requirement: {name}")
        locked[name] = item.version
        for extra in {"", *request.extras}:
            if (name, extra) in expanded:
                continue
            expanded.add((name, extra))
            for text in item.requires or ():
                child = Requirement(text)
                if child.marker is None or child.marker.evaluate({"extra": extra}):
                    pending.append(child)
    return dict(sorted(locked.items()))


def git(*args):
    result = subprocess.run(["git", *args], cwd=ROOT, capture_output=True, text=True)
    if result.returncode:
        raise ValueError("Git check failed: " + result.stderr.strip())
    return result.stdout.strip()


def build(out):
    if out.exists() or out.is_relative_to(ROOT):
        raise ValueError("Choose a new output folder outside the repository.")
    git("diff", "--exit-code", "HEAD", "--", *FILES)
    tracked = set(git("ls-files", "--", *FILES).splitlines())
    if set(FILES) - set(SOURCE_HASHES) - tracked:
        raise ValueError("A required runtime file is not tracked. Review the inventory first.")
    pins = installed_lock()
    originals = {}
    for name in FILES:
        path = safe_path(ROOT, name)
        originals[name] = signature(path)
        if name in SOURCE_HASHES and originals[name]["sha256"] != SOURCE_HASHES[name]:
            raise ValueError(f"Frozen source hash differs: {name}")
    extras = {
        "verify_demo.py": (ROOT / "scripts/prototype_verify_demo.py").read_bytes(),
        "Start_Demo.ps1": (ROOT / "docs/prototype/Start_Demo.ps1").read_bytes(),
        "README.md": (ROOT / "docs/prototype/demo_package.md").read_bytes(),
        "requirements.versions.txt": ("\n".join(f"{name}=={value}" for name, value in pins.items()) + "\n").encode(),
    }
    out.mkdir(parents=True, exist_ok=False)
    for name in FILES:
        destination = out / name
        destination.parent.mkdir(parents=True, exist_ok=True)
        with destination.open("xb") as handle:
            handle.write((ROOT / name).read_bytes())
        if signature(destination) != originals[name]:
            raise ValueError(f"File changed while copying: {name}")
    for name, value in extras.items():
        with (out / name).open("xb") as handle:
            handle.write(value)
    manifest = {"format": 1, "sealed": False, "source_commit": git("rev-parse", "HEAD"),
                "environment": environment(), "dependencies": pins,
                "files": {name: signature(out / name) for name in (*FILES, *extras)}}
    write_json(out / "package_manifest.json", manifest)
    print(f"Copied {len(manifest['files'])} allowlisted files; pinned {len(pins)} runtime distributions.")
    print("Excluded: credentials, private ledger, virtual environments and held-out data.")


def seal(out):
    manifest = verify_files(out, sealed=False)
    if manifest["sealed"]:
        raise ValueError("This package is already sealed.")
    wheels = {}
    folder = out / "wheelhouse"
    if not folder.is_dir():
        raise ValueError("Download the wheels before sealing.")
    for path in folder.iterdir():
        if not path.is_file() or path.suffix != ".whl" or path.is_symlink():
            raise ValueError("Unexpected wheelhouse entry.")
        name, number, _, _ = parse_wheel_filename(path.name)
        name = canonicalize_name(name)
        if name in wheels or manifest["dependencies"].get(name) != str(number):
            raise ValueError(f"Unexpected wheel or duplicate version: {name}")
        wheels[name] = path
    if set(wheels) != set(manifest["dependencies"]):
        raise ValueError("The wheelhouse does not cover every locked dependency.")
    lines = []
    for name, number in manifest["dependencies"].items():
        path = wheels[name]
        info = signature(path)
        manifest["files"][path.relative_to(out).as_posix()] = info
        lines.append(f"{name}=={number} --hash=sha256:{info['sha256']}")
    with (out / "requirements.lock").open("x", encoding="utf-8", newline="\n") as handle:
        handle.write("\n".join(lines) + "\n")
    manifest["files"]["requirements.lock"] = signature(out / "requirements.lock")
    manifest["sealed"] = True
    write_json(out / "package_manifest.json", manifest, "w")
    verify_files(out)
    print(f"Sealed package with {len(wheels)} locally saved, SHA-256-pinned wheels.")


def archive(out, proof):
    manifest = verify_files(out)
    record = json.loads(proof.read_text(encoding="utf-8"))
    required = {"home_coach_source_handoff", "three_bill_flows_and_comparisons",
                "dashboard_scope", "offline_cache_miss_blocked"}
    if (record.get("manifest_sha256") != signature(out / "package_manifest.json")["sha256"]
            or record.get("source_commit") != manifest["source_commit"]
            or record.get("environment") != manifest.get("environment")
            or set(record.get("checks", {})) != required
            or not all(value is True for value in record["checks"].values())
            or type(record.get("provider_calls")) is not int or record["provider_calls"] != 0
            or type(record.get("ledger_accesses")) is not int or record["ledger_accesses"] != 0
            or record.get("package_files_unchanged") is not True):
        raise ValueError("Fresh-environment proof does not match this sealed package.")
    target = out.parent / "NextBest-demo.zip"
    report = ROOT / "docs/prototype/demo_package_check.json"
    receipt = target.with_suffix(".zip.sha256")
    if target.exists() or report.exists() or receipt.exists():
        raise ValueError("An archive or evidence report already exists. Preserve it for review.")
    with zipfile.ZipFile(target, "x", compression=zipfile.ZIP_DEFLATED) as bundle:
        for name in sorted({*manifest["files"], "package_manifest.json"}):
            bundle.write(out / name, f"NextBest-demo/{name}")
    info = signature(target)
    with receipt.open("x", encoding="ascii") as handle:
        handle.write(f"{info['sha256']}  {target.name}\n")
    record.update(archive_sha256=info["sha256"], archive_bytes=info["bytes"],
                  runtime_distributions=len(manifest["dependencies"]),
                  packaged_files=len(manifest["files"]) + 1)
    write_json(report, record)
    print("Archive:", target)
    print("SHA-256:", info["sha256"])
    print("Evidence:", report)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("action", choices=("build", "seal", "archive"))
    parser.add_argument("--out", required=True, type=Path)
    parser.add_argument("--proof", type=Path)
    args = parser.parse_args()
    out = args.out.resolve()
    if args.action == "build":
        build(out)
    elif args.action == "seal":
        seal(out)
    elif args.proof:
        archive(out, args.proof)
    else:
        raise ValueError("Archive requires --proof.")


if __name__ == "__main__":
    main()
