"""Compare two coders and report agreement honestly.

    python scripts/compute_kappa.py --master oshc-master-data-v7-final.xlsx \
        --pack coder_pack_minhaj.xlsx --second-coder Minhaj

Reports Cohen's kappa for Gap and for Code 1, each with a bootstrap confidence
interval, percentage agreement, per-category agreement, and the full list of
disagreements for reconciliation.

It refuses to compute when the two record sets differ, when a label falls
outside the permitted set, or when rows are unfilled. A kappa produced from a
partly filled pack is worse than no kappa, because it looks like evidence.

Owner: Bikram Bhattarai.
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import openpyxl

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from oshc.agreement import with_ci  # noqa: E402

CODES = {"C1", "C2", "C3", "C4", "C5", "C6", "S"}
GAPS = {"Y", "N"}


def read_master(path: Path) -> dict[str, dict]:
    rows = list(openpyxl.load_workbook(path, data_only=True)["Review Coding"].iter_rows(values_only=True))
    h = [str(x).strip() if x else "" for x in rows[0]]
    i = {n: h.index(n) for n in h}
    out = {}
    for r in rows[1:]:
        rid = r[i["Review ID"]]
        if not rid:
            continue
        out[str(rid).strip()] = {
            "code1": str(r[i["Code 1"]] or "").strip(),
            "gap": str(r[i["Gap"]] or "").strip(),
            "snippet": str(r[i["Snippet"]] or "").strip(),
        }
    return out


def read_pack(path: Path) -> dict[str, dict]:
    rows = list(openpyxl.load_workbook(path, data_only=True)["Coding"].iter_rows(values_only=True))
    h = [str(x).strip() if x else "" for x in rows[0]]
    i = {n: h.index(n) for n in h}
    out = {}
    for r in rows[1:]:
        rid = str(r[i["Review ID"]] or "").strip()
        if not rid or rid.startswith("EXAMPLE"):
            continue
        out[rid] = {"code1": str(r[i["Code 1"]] or "").strip(),
                    "gap": str(r[i["Gap"]] or "").strip()}
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--master", required=True)
    ap.add_argument("--pack", required=True)
    ap.add_argument("--second-coder", default="Coder 2")
    ap.add_argument("--out", default="data/agreement")
    args = ap.parse_args()

    master = read_master(Path(args.master))
    pack = read_pack(Path(args.pack))

    problems = []
    missing = [k for k in pack if k not in master]
    if missing:
        problems.append(f"{len(missing)} pack ID(s) not in the master: {', '.join(missing[:5])}")
    unfilled = [k for k, v in pack.items() if not v["code1"] or not v["gap"]]
    if unfilled:
        problems.append(f"{len(unfilled)} row(s) not coded: {', '.join(unfilled[:5])}")
    bad = [f"{k}={v['code1']}" for k, v in pack.items() if v["code1"] and v["code1"] not in CODES]
    bad += [f"{k}={v['gap']}" for k, v in pack.items() if v["gap"] and v["gap"] not in GAPS]
    if bad:
        problems.append(f"label(s) outside the permitted set: {', '.join(bad[:5])}")
    if problems:
        print("refusing to compute:")
        for p in problems:
            print("  -", p)
        return 1

    ids = sorted(pack)
    a_code = [master[i]["code1"] for i in ids]
    b_code = [pack[i]["code1"] for i in ids]
    a_gap = [master[i]["gap"] for i in ids]
    b_gap = [pack[i]["gap"] for i in ids]

    results = {}
    for name, a, b in (("Gap", a_gap, b_gap), ("Code 1", a_code, b_code)):
        try:
            r = with_ci(a, b)
        except ValueError as e:
            print(f"{name}: {e}")
            continue
        results[name] = r
        print(f"--- {name} ---")
        print(f"  n                  : {r.n}")
        print(f"  agreement          : {r.observed_agreement:.1%}")
        print(f"  expected by chance : {r.expected_agreement:.1%}")
        print(f"  kappa              : {r.kappa:.3f}  95% CI [{r.ci_low:.3f}, {r.ci_high:.3f}]")
        print(f"  reading            : {r.interpretation()}")
        weak = {k: v for k, v in (r.per_category or {}).items() if v < 0.7}
        if weak:
            print(f"  weakest categories : {', '.join(f'{k} {v:.0%}' for k, v in sorted(weak.items()))}")
        print()

    disagreements = [
        {"id": i, "bikram_code1": master[i]["code1"], f"{args.second_coder}_code1": pack[i]["code1"],
         "bikram_gap": master[i]["gap"], f"{args.second_coder}_gap": pack[i]["gap"],
         "snippet": master[i]["snippet"][:160]}
        for i in ids
        if master[i]["code1"] != pack[i]["code1"] or master[i]["gap"] != pack[i]["gap"]
    ]
    print(f"{len(disagreements)} record(s) to reconcile.")

    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).isoformat(timespec="seconds")
    (out_dir / f"agreement_{stamp[:10]}.json").write_text(json.dumps({
        "computed_at_utc": stamp,
        "coders": ["Bikram", args.second_coder],
        "n": len(ids),
        "results": {k: {kk: vv for kk, vv in v.__dict__.items()} for k, v in results.items()},
        "disagreements": disagreements,
    }, indent=2, default=str, ensure_ascii=False), encoding="utf-8")
    print(f"written to {out_dir}/agreement_{stamp[:10]}.json")
    print()
    print("Report kappa with its interval and n, never the point estimate alone.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
