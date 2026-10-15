"""Fixed local baselines with grouped out-of-fold predictions and no label tuning."""
import argparse
import hashlib
import json
import re
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
from sklearn.metrics import f1_score, accuracy_score
from sklearn.model_selection import StratifiedGroupKFold

from oshc.classifier import SEED, fit_classifier
from oshc.schemas import Code


def assign_groups(rows):
    groups = list(range(len(rows)))
    def root(i):
        while groups[i] != i:
            i = groups[i]
        return i
    normal = lambda text: " ".join(re.findall(r"\w+", text.casefold()))
    for i, row in enumerate(rows):
        for j in range(i):
            if (row.get("group", row.get("thread")) == rows[j].get("group", rows[j].get("thread"))
                    or normal(row["text"]) == normal(rows[j]["text"])):
                groups[root(i)] = root(j)
    return [root(i) for i in range(len(rows))]


def evaluate(dataset, *, bootstrap_iterations=2000):
    source = json.loads(dataset.read_text(encoding="utf-8"))
    rows = [r for r in source["records"] if r["role"] != "Commenter" and not r["anchor"]]
    labels = [r["label"] for r in rows]
    classes = [code.value for code in Code]
    # Union repeated snippets and thread IDs so duplicates cannot cross folds.
    group_ids = assign_groups(rows)
    folds = list(StratifiedGroupKFold(n_splits=5, shuffle=True, random_state=SEED).split(rows, labels, group_ids))
    results = {}
    for step in ("majority", "tfidf_logreg"):
        predicted = [None] * len(rows)
        for train, test in folds:
            assert not ({group_ids[i] for i in train} & {group_ids[i] for i in test})
            model = fit_classifier([rows[i]["text"] for i in train], [labels[i] for i in train], step=step)
            for i in test:
                predicted[i] = model.predict(rows[i]["text"]).value
        rng = np.random.default_rng(SEED)
        ids = sorted(set(group_ids))
        samples = []
        for _ in range(bootstrap_iterations):
            selected = rng.choice(ids, len(ids), replace=True)
            indices = [i for group in selected for i, key in enumerate(group_ids) if key == group]
            samples.append(f1_score([labels[i] for i in indices], [predicted[i] for i in indices],
                                    labels=classes, average="macro", zero_division=0))
        results[step] = {"macro_f1_fixed_seven_classes": float(f1_score(labels, predicted, labels=classes, average="macro", zero_division=0)),
                         "macro_f1_ci95_group_bootstrap": [float(x) for x in np.quantile(samples, [.025, .975])],
                         "accuracy": float(accuracy_score(labels, predicted)),
                         "predictions": [{"id": row["id"], "expected": row["label"], "predicted": guess}
                                         for row, guess in zip(rows, predicted)]}
    paired = [r for r in source["records"] if r["original_second"] is not None and r["role"] != "Commenter"]
    return {"kind": "automated adjudication and grouped classifier development baseline",
            "created_at_utc": datetime.now(timezone.utc).isoformat(),
            "dataset_sha256": hashlib.sha256(dataset.read_bytes()).hexdigest(), "source_hashes": source["sources"],
            "evaluation_code_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
            "classifier_code_sha256": hashlib.sha256((Path(__file__).resolve().parents[1] / "oshc/classifier.py").read_bytes()).hexdigest(),
            "evaluation_revision": "Grouping normalises punctuation; previous report preserved.",
            "n": len(rows), "groups": len(set(group_ids)), "label_counts": dict(Counter(labels)),
            "uncertain_labels": sum(r["uncertain"] for r in rows),
            "original_disagreements": sum(r["original_first"] != r["original_second"] for r in paired) if paired else None,
            "paired_original_label_records": len(paired),
            "adjudicated_records": len(source["records"]), "human_consensus": False,
            "excluded_anchor_ids": source["excluded_anchor_ids"],
            "folds": [{"train_n": len(tr), "test_n": len(te),
                       "test_ids": [rows[i]["id"] for i in te],
                       "missing_training_classes": sorted(set(classes) - {labels[i] for i in tr})}
                      for tr, te in folds], "results": results,
            "review_to_question_shift_gap": None,
            "limitations": ["Derived labels are automated judgments, not reconciled human consensus.",
                            "Historical human kappa remains 0.4173; this does not improve that agreement.",
                            "The available coder-pack file is blank; original disagreement counts come from the separate historical agreement report, not this dataset.",
                            "All seven classes retained in macro-F1, including unsupported rare classes.",
                            "Five folds are grouped; tiny classes cannot be stratified across every fold.",
                            "Bootstrap uses saved out-of-fold predictions; it does not refit models.",
                            "No independently labelled student-question set exists; shift gap unmeasured.",
                            "Embedding and LLM baselines not run; no downloaded model or paid call."]}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    if args.out.exists():
        raise ValueError("Report exists; do not overwrite first scores")
    report = evaluate(args.dataset)
    with args.out.open("x", encoding="utf-8") as h:
        json.dump(report, h, indent=2)
    print(json.dumps({"n": report["n"], "results": {k: {m: v[m] for m in v if m != "predictions"}
                                                   for k, v in report["results"].items()}}, indent=2))


if __name__ == "__main__":
    main()
