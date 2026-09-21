"""Freeze one coder's labels and publish a hash.

    python scripts/freeze_labels.py --workbook oshc-master-data-v7-final.xlsx --coder Bikram

Why this exists: blind double coding is only blind if the first pass is
provably fixed before the second coder starts. A hash published in the team
channel, before Minhaj submits his pass, is that proof. Without it "we coded
independently" is an assertion, and kappa rests on an assertion.

Writes data/freeze/<coder>_<date>.json and prints the SHA-256 to post.
This script does not read, alter or reveal any label values to anyone. It only
fingerprints them.

Owner: Bikram Bhattarai.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

import openpyxl

FIELDS = ("Review ID", "Code 1", "Code 2", "Gap")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--workbook", required=True)
    ap.add_argument("--sheet", default="Review Coding")
    ap.add_argument("--coder", required=True, help="value in the Coder column to freeze")
    ap.add_argument("--out", default="data/freeze")
    args = ap.parse_args()

    wb = openpyxl.load_workbook(args.workbook, data_only=True)
    if args.sheet not in wb.sheetnames:
        print(f"error: no sheet named {args.sheet!r}. Found: {', '.join(wb.sheetnames)}")
        return 1
    rows = list(wb[args.sheet].iter_rows(values_only=True))
    header = [str(h).strip() if h else "" for h in rows[0]]
    missing = [f for f in FIELDS + ("Coder",) if f not in header]
    if missing:
        print(f"error: sheet is missing column(s): {', '.join(missing)}")
        return 1
    idx = {name: header.index(name) for name in FIELDS + ("Coder",)}

    labels = []
    for r in rows[1:]:
        if str(r[idx["Coder"]]).strip() != args.coder:
            continue
        labels.append({f: ("" if r[idx[f]] is None else str(r[idx[f]]).strip()) for f in FIELDS})

    if not labels:
        coders = sorted({str(r[idx["Coder"]]).strip() for r in rows[1:] if r[idx["Coder"]]})
        print(f"error: no rows with Coder == {args.coder!r}. Present: {', '.join(coders)}")
        return 1

    uncoded = [l["Review ID"] for l in labels if not l["Code 1"]]
    if uncoded:
        print(f"refusing to freeze: {len(uncoded)} row(s) have no Code 1, "
              f"first few: {', '.join(uncoded[:5])}")
        return 1

    labels.sort(key=lambda d: d["Review ID"])
    canonical = json.dumps(labels, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    digest = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")

    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)
    out = out_dir / f"{args.coder.lower()}_{now[:10]}.json"
    out.write_text(json.dumps({
        "coder": args.coder,
        "workbook": Path(args.workbook).name,
        "sheet": args.sheet,
        "frozen_at_utc": now,
        "record_count": len(labels),
        "sha256": digest,
        "labels": labels,
    }, indent=2, ensure_ascii=False), encoding="utf-8")

    print(f"coder        : {args.coder}")
    print(f"records      : {len(labels)}")
    print(f"frozen at    : {now}")
    print(f"sha256       : {digest}")
    print(f"written to   : {out}")
    print()
    print("Post the sha256, the record count and the timestamp in the team channel now.")
    print("Do not post the file. The hash is the proof; the labels are the thing being proved.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
