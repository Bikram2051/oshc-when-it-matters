"""Freeze outputs on a separately authored synthetic handoff before loading truth."""
from __future__ import annotations
import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from eval.extraction import load_map, require_private, score, sha256
from oshc.billexplainer.extract_document import extract as current
from oshc.billexplainer.extract_rules import extract as baseline
from oshc.billexplainer.read import read_pdf, read_text


def save(path, value):
    with path.open("x", encoding="utf-8") as handle:
        json.dump(value, handle, indent=2)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--handoff", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    args = parser.parse_args()
    require_private(args.handoff, "handoff")
    require_private(args.out, "outputs")
    if args.out.exists() or args.report.exists():
        raise SystemExit("Use new paths. First outcomes are never overwritten.")
    rows = load_map(args.handoff / "filemap.csv")
    paths = ["oshc/billexplainer/extract_document.py", "oshc/billexplainer/extract_rules.py",
             "oshc/billexplainer/read.py", "oshc/schemas.py", "eval/extraction.py"]
    freeze = {p: sha256(ROOT / p) for p in paths}
    args.out.mkdir(parents=True)
    save(args.out / "implementation_freeze.json", freeze)
    for name, extractor in (("frozen_baseline", baseline), ("current_prototype", current)):
        destination = args.out / name
        (destination / "rules").mkdir(parents=True)
        outputs, failures = {}, 0
        for row in rows:
            path = args.handoff / "inputs" / row["input_file"]
            if sha256(path) != row["input_sha256"]:
                raise ValueError("Input hash mismatch")
            try:
                bill = read_pdf(path) if path.suffix == ".pdf" else read_text(path.read_text(encoding="utf-8"))
                result = extractor(bill).model_dump(mode="json")
            except Exception as error:
                result = {"error_type": type(error).__name__, "line_items": []}
                failures += 1
            target = destination / "rules" / (row["document_id"] + ".json")
            save(target, result)
            outputs["rules/" + target.name] = sha256(target)
        save(destination / "run_record.json", {"created_at_utc": datetime.now(timezone.utc).isoformat(),
             "outputs": outputs, "source_hashes": freeze, "pipeline": name, "exceptions": failures,
             "map_sha256": sha256(args.handoff / "filemap.csv")})
    # Truth is first read after BOTH sets of outputs have been saved and hashed.
    if freeze != {p: sha256(ROOT / p) for p in paths}:
        raise ValueError("Implementation changed during evaluation")
    report = {
        "kind": "new separately authored automated synthetic evaluation",
        "historical_human_heldout": False,
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "source_hashes": freeze, "documents": len(rows), "provider_calls": 0,
        "paid_llm_pipeline": "not run; offline only",
        "limitations": ["Synthetic layouts; no real-patient accuracy claim.",
            "Automated custodian authored truth without reading extractor code.",
            "Historical exposed family parameters were not used.",
            "Privacy minimisation is tested separately; extraction scoring precedes UI minimisation."],
        "results": {name: score(args.handoff / "filemap.csv", args.handoff / "truth", args.out / name)
                    for name in ("frozen_baseline", "current_prototype")},
    }
    save(args.report, report)
    print(json.dumps({name: value["pipelines"]["rules"]["micro"]
                      for name, value in report["results"].items()}, indent=2))


if __name__ == "__main__":
    main()
