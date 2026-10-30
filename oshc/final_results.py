"""Select numeric fields from final reports; never expose per-record content."""
import hashlib
import json
import math
from pathlib import Path

FILES = {
    "current": "docs/prototype/current_evaluation_final_2026-10-15.json",
    "bills": "docs/prototype/bill_evaluation_2026-10-14.json",
    "classifier": "docs/prototype/classifier_summary_2026-10-15.json",
    "release": "docs/prototype/release_summary_2026-10-15.json",
}


def load_final(root: Path):
    manifest_path = root / "docs/prototype/final_results_manifest.json"
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        records = {}
        for key, relative in FILES.items():
            path = root / relative
            if path.stat().st_size > 1_000_000:
                return None
            raw = path.read_bytes()
            if hashlib.sha256(raw).hexdigest() != manifest[relative]:
                return None
            records[key] = json.loads(raw)
        def number(value):
            if type(value) not in (int, float) or not math.isfinite(value) or not 0 <= value <= 1:
                raise ValueError("Invalid metric")
            return float(value)
        def metric(row):
            if type(row["n"]) is not int or type(row["k"]) is not int or not 0 <= row["k"] <= row["n"] or row["n"] <= 0:
                raise ValueError("Invalid count")
            rate = number(row["rate"])
            if abs(rate - row["k"] / row["n"]) > 1e-6:
                raise ValueError("Inconsistent metric")
            lo, hi = [number(v) for v in row["ci95"]]
            if not lo <= rate <= hi:
                raise ValueError("Invalid interval")
            return {"rate": rate, "n": row["n"], "k": row["k"], "ci95": [lo, hi]}
        current = records["current"]
        if current["independent_unseen_evaluation"] is not False:
            return None
        release = records["release"]
        if release["independent_of_implementation"] is not True or release["human_assessment"] is not False:
            return None
        return {"chat": {key: metric(current["chat"][key]) for key in
                         ("refusal_recall", "false_refusal_rate", "emergency_recall")},
                "retrieval": metric(current["retrieval"]["hit_at_5"]),
                "bill_f1": number(records["bills"]["results"]["current_prototype"]["pipelines"]["rules"]["micro"]["f1"]),
                "bill_n": records["bills"]["documents"],
                "classifier": {key: number(row["macro_f1_fixed_seven_classes"])
                               for key, row in records["classifier"]["results"].items()},
                "classifier_n": records["classifier"]["n"],
                "release_chat": {key: metric(release["chat"][key]) for key in
                                 ("refusal_recall", "false_refusal_rate", "emergency_recall")},
                "independent_retrieval": metric(release["retrieval"]["hit_at_5"]),
                "independent_retrieval_mrr": number(release["retrieval"]["mrr_at_5"]),
                "all_50_retrieval": metric(release["retrieval"]["all_50_hit_at_5"])}
    except (OSError, ValueError, KeyError, TypeError):
        return None
