"""Join existing coding records with separately saved automated adjudication.

Read-only workbook analysis; raw snippets and joined records stay outside the repo.
"""
import argparse
import csv
import hashlib
import json
from pathlib import Path
import openpyxl


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--master", type=Path, required=True)
    p.add_argument("--pack", type=Path, required=True)
    p.add_argument("--decisions", type=Path, required=True)
    p.add_argument("--out", type=Path, required=True)
    a = p.parse_args()
    if a.out.exists():
        raise ValueError("Frozen dataset already exists")
    decisions = {r["record_id"]: r for r in csv.DictReader(a.decisions.open(), delimiter="\t")}
    wb = openpyxl.load_workbook(a.master, data_only=True)
    values = list(wb["Review Coding"].values)
    records = [dict(zip(values[0], row)) for row in values[1:] if row[0]]
    pack = openpyxl.load_workbook(a.pack, data_only=True)
    anchors = [str(row[2]) for row in pack["Read me first"].values
               if row[0] in {"C1", "C2", "C3", "C4", "C5", "C6", "S"} and row[2]]
    values = list(pack["Coding"].values)
    second = {str(r[0]): dict(zip(values[0], r)) for r in values[1:] if r[0]}
    output, excluded = [], []
    for r in records:
        ident = r["Review ID"]
        if not str(r["Analysis Status"]).startswith("Included"):
            continue
        if ident not in decisions:
            raise ValueError(f"Missing decision for {ident}")
        d = decisions[ident]
        text = str(r["Snippet"]).strip()
        anchor = any(text.startswith(x) or x.startswith(text) for x in anchors)
        if anchor:
            excluded.append(ident)
        output.append({"id": ident, "group": str(r["Thread ID"] or ident),
                       "text": text, "role": r["Speaker Role"], "anchor": anchor,
                       "label": d["code1"], "gap": "N" if d["code1"] == "S" else "Y",
                       "uncertain": d["uncertain"] == "true", "rationale": d["rationale"],
                       "original_first": r["Code 1"], "original_second": second.get(ident, {}).get("Code 1")})
    payload = {"provenance": "automated adjudication, not human consensus",
               "sources": {p.name: digest(p) for p in (a.master, a.pack, a.decisions)},
               "excluded_anchor_ids": excluded, "records": output}
    with a.out.open("x", encoding="utf-8") as h:
        json.dump(payload, h, indent=2)
    print(json.dumps({"rows": len(output), "anchor_ids": excluded, "sha256": digest(a.out)}))


if __name__ == "__main__":
    main()
