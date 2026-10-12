"""Run the frozen extractors once on the released evaluation inputs.

Writes one saved output per document and pipeline, including failures, and a
run_record.json with the SHA-256 of every output. It never reads expected
outputs and never overwrites a file. Protocol: docs/prototype/extraction_protocol.md

    python scripts/run_heldout_extraction.py --map MAP.csv --inputs INPUT_DIR --out RUN_DIR
"""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from eval.extraction import ScoringError, load_map, require_private, sha256  # noqa: E402
from oshc import llm  # noqa: E402
from oshc.billexplainer import extract_llm, extract_rules  # noqa: E402
from oshc.billexplainer.read import read_pdf, read_text  # noqa: E402
from oshc.llm_budget import MODEL, Budget, BudgetError  # noqa: E402

PIPELINES = {"rules": extract_rules.extract, "llm": extract_llm.extract}
# Extraction code fixed on 1 October 2026 (PR #11, commit 40e04f8). The run refuses
# any other version so the held-out result describes the frozen extractor.
FROZEN = {
    "oshc/billexplainer": "bff4a9b244c4e046cb821eb0db9ea8afea147de9",
    "oshc/llm.py": "26703721be8f643db481bcfa7ee1913b09cf54af",
    "oshc/llm_budget.py": "30fd228a717ef52e2632057bd674db220538d4e4",
    "oshc/schemas.py": "35a5b18c12ed21862b02df8f41168b486d31e64b",
}
# The most one llm extraction can reserve under the frozen adapter: 12,000 input tokens
# padded to 13,200, plus five times the 3,072 output-token limit, at USD 1 per million.
LLM_MAX_RESERVATION_USD = (13_200 + 5 * 3_072) / 1_000_000
UNAVAILABLE = re.compile(r"LLM extraction unavailable \((\w+)\)")


def _git(*args: str) -> str:
    result = subprocess.run(["git", "-C", str(ROOT), *args], capture_output=True, text=True,
                            check=False)
    if result.returncode != 0:
        raise SystemExit(f"git {' '.join(args)} failed: {result.stderr.strip()}")
    return result.stdout.strip()


def verify_freeze() -> dict:
    for path, expected in FROZEN.items():
        if _git("rev-parse", f"HEAD:{path}") != expected:
            raise SystemExit(f"{path} is not the frozen version. The held-out run is refused.")
    if _git("status", "--porcelain", "--", *FROZEN):
        raise SystemExit("The frozen extraction files have local changes. The held-out run is refused.")
    return {"commit": _git("rev-parse", "HEAD"), "frozen_paths": FROZEN}


def check_live_settings(documents: int) -> dict:
    """Refuse an llm run that could not finish, before any output is written."""
    if os.getenv("OSHC_OFFLINE") != "0" or os.getenv("OSHC_ENABLE_LIVE") != "1":
        raise SystemExit("The llm pipeline makes paid calls: set OSHC_OFFLINE=0 and "
                         "OSHC_ENABLE_LIVE=1 for this run only.")
    if not os.getenv("OSHC_API_KEY"):
        raise SystemExit("Not run: OSHC_API_KEY is not set in .env.")
    if os.getenv("OSHC_MODEL") not in (None, "", MODEL):
        raise SystemExit(f"Not run: OSHC_MODEL must be unset or {MODEL}.")
    try:
        status = Budget().status()
    except BudgetError as error:
        raise SystemExit(f"Not run: {error}") from None
    needed = documents * LLM_MAX_RESERVATION_USD
    if status["blocked_for_review"] or status["remaining"] < needed:
        raise SystemExit(f"Not run: the spending allowance has USD {status['remaining']:.2f} "
                         f"left and this run may reserve up to USD {needed:.2f}.")
    return status


def read_input(path: Path):
    data = path.read_bytes()
    suffix = path.suffix.lower()
    if suffix == ".pdf":
        return read_pdf(data)
    if suffix == ".txt":
        return read_text(data.decode("utf-8-sig"))
    raise ValueError(f"Unsupported input type: {path.name}")


def run(map_path: Path, inputs_dir: Path, out_dir: Path, pipelines: list[str]) -> dict:
    unknown = [name for name in pipelines if name not in PIPELINES]
    if unknown or not pipelines:
        raise SystemExit(f"Choose pipelines from: {', '.join(PIPELINES)}")
    map_path, inputs_dir, out_dir = Path(map_path), Path(inputs_dir), Path(out_dir)
    if out_dir.exists():
        raise SystemExit(f"Not run: {out_dir} already exists. A run is never replaced; "
                         "record a rerun in a new folder with its reason.")
    try:
        for path, label in ((map_path, "The file map"), (inputs_dir, "The inputs folder"),
                            (out_dir, "The run folder")):
            require_private(path, label)
        rows = load_map(map_path)
    except ScoringError as error:
        raise SystemExit(f"Not run: {error}") from None
    if "llm" in pipelines and (os.getenv("OSHC_OFFLINE") != "0" or os.getenv("OSHC_ENABLE_LIVE") != "1"):
        raise SystemExit("The llm pipeline makes paid calls: set OSHC_OFFLINE=0 and "
                         "OSHC_ENABLE_LIVE=1 for this run only.")
    for row in rows:
        path = inputs_dir / row["input_file"]
        if not path.is_file():
            raise SystemExit(f"Not run: missing input {row['input_file']}")
        if sha256(path) != row["input_sha256"]:
            raise SystemExit(f"Not run: {row['input_file']} differs from the file map.")
    freeze = verify_freeze()
    budget_before = check_live_settings(len(rows)) if "llm" in pipelines else None
    out_dir.mkdir(parents=True, exist_ok=False)
    record = {
        "protocol": "docs/prototype/extraction_protocol.md",
        "started_at_utc": datetime.now(timezone.utc).isoformat(),
        "map_sha256": sha256(map_path),
        "documents": len(rows),
        "pipelines": pipelines,
        "code": freeze,
        "environment": {name: os.getenv(name) for name in
                        ("OSHC_OFFLINE", "OSHC_ENABLE_LIVE", "OSHC_MODEL")},
        "failures": {},
        "llm_unavailable": None,
        "outputs": {},
    }
    # Held-out responses are cached in the run folder, never in the committed cache/llm.
    committed_cache = llm.CACHE_DIR
    llm.CACHE_DIR = out_dir.resolve() / "llm_cache" / "v2"
    try:
        for pipeline in pipelines:
            (out_dir / pipeline).mkdir()
            failures, unavailable = 0, Counter()
            for row in rows:
                try:
                    result = PIPELINES[pipeline](read_input(inputs_dir / row["input_file"]))
                    text = result.model_dump_json(indent=2)
                    if pipeline == "llm":
                        for warning in result.warnings:
                            found = UNAVAILABLE.match(warning)
                            if found:
                                unavailable[found.group(1)] += 1
                except Exception as error:  # every failure is recorded, never skipped
                    failures += 1
                    text = json.dumps({"document_id": row["document_id"], "pipeline": pipeline,
                                       "error": f"{type(error).__name__}: {error}"}, indent=2)
                name = f"{pipeline}/{row['document_id']}.json"
                with (out_dir / name).open("x", encoding="utf-8", newline="\n") as handle:
                    handle.write(text + "\n")
                record["outputs"][name] = sha256(out_dir / name)
            record["failures"][pipeline] = failures
            if pipeline == "llm":
                record["llm_unavailable"] = dict(sorted(unavailable.items()))
    finally:
        llm.CACHE_DIR = committed_cache
    record["llm_cache"] = {path.relative_to(out_dir).as_posix(): sha256(path)
                           for path in sorted((out_dir / "llm_cache").rglob("*.json"))}
    record["finished_at_utc"] = datetime.now(timezone.utc).isoformat()
    record["budget"] = {"before": budget_before,
                        "after": Budget().status() if "llm" in pipelines else None}
    with (out_dir / "run_record.json").open("x", encoding="utf-8", newline="\n") as handle:
        json.dump(record, handle, indent=2)
        handle.write("\n")
    return record


def main(argv=None) -> None:
    parser = argparse.ArgumentParser(description="Run the frozen extractors once.")
    parser.add_argument("--map", required=True, type=Path)
    parser.add_argument("--inputs", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path)
    parser.add_argument("--pipelines", default="rules,llm")
    args = parser.parse_args(argv)
    record = run(args.map, args.inputs, args.out,
                 [name.strip() for name in args.pipelines.split(",") if name.strip()])
    print(f"Documents: {record['documents']}; failures: {record['failures']}")
    if record["llm_unavailable"]:
        print(f"llm documents with no values because the call did not complete: "
              f"{record['llm_unavailable']}")
    print("Post this hash in the group chat before the expected outputs are released:")
    print("run_record.json SHA-256", sha256(args.out / "run_record.json"))


if __name__ == "__main__":
    main()
