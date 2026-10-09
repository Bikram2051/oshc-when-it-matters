"""Score saved bill-extraction outputs against the custodian's expected outputs.

The rules are fixed in docs/prototype/extraction_protocol.md. This module reads
saved files only. It never runs an extractor and never reads generator parameters.

    python -m eval.extraction --map MAP.csv --gold GOLD_DIR --outputs RUN_DIR --report REPORT.json

The custodian checks the expected outputs and the file map before release with:

    python -m eval.extraction --check --map MAP.csv --gold GOLD_DIR --inputs INPUT_DIR
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import random
import re
import subprocess
from datetime import datetime, timezone
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PIPELINES = ("rules", "llm")
DOC_FIELDS = ("provider", "service_date", "total_charged", "total_benefit", "total_gap")
LINE_FIELDS = ("item_number", "charged", "benefit_paid", "gap")
MONEY_FIELDS = frozenset({"total_charged", "total_benefit", "total_gap", "charged", "benefit_paid", "gap"})
MAP_COLUMNS = ("document_id", "family", "input_file", "input_sha256", "gold_file", "gold_sha256")
DATE_FORMATS = ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y")
BOOTSTRAP_RESAMPLES = 2000
BOOTSTRAP_SEED = 2026
CENT = Decimal("0.01")
SAFE_ID = re.compile(r"[A-Za-z0-9_-]{1,64}")
SAFE_FILE = re.compile(r"[A-Za-z0-9_.-]{1,128}")
INPUT_TYPES = (".pdf", ".txt")
HEX64 = re.compile(r"[0-9a-f]{64}")


class ScoringError(ValueError):
    """The files do not meet the protocol. Nothing is scored."""


class _Invalid:
    """An output value that could not be read. It never equals an expected value."""

    def __init__(self, raw):
        self.raw = raw

    def __eq__(self, other):
        return False

    __hash__ = None


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def require_private(path: Path, label: str) -> None:
    """Held-out files stay outside the repository or in a folder git ignores."""
    resolved = Path(path).resolve()
    if resolved != ROOT and ROOT not in resolved.parents:
        return
    try:
        ignored = subprocess.run(
            ["git", "-C", str(ROOT), "check-ignore", "-q", "--",
             resolved.relative_to(ROOT).as_posix()],
            capture_output=True, check=False).returncode == 0
    except OSError:
        ignored = False
    if not ignored:
        raise ScoringError(f"{label} is inside the repository in a folder git does not ignore. "
                           "Keep held-out files outside the repository or under data/heldout/.")


def _money(value):
    if isinstance(value, bool):
        raise TypeError("not an amount")
    amount = Decimal(str(value).strip())
    if not amount.is_finite():
        raise ValueError("not an amount")
    return amount.quantize(CENT, rounding=ROUND_HALF_UP)


def _date(value):
    text = str(value).strip()
    for pattern in DATE_FORMATS:
        try:
            return datetime.strptime(text, pattern).date()
        except ValueError:
            continue
    raise ValueError("not a date")


def _text(value):
    return " ".join(str(value).split()).casefold()


def _item(value):
    return "".join(str(value).split()).casefold()


def normalise(field: str, value, *, strict: bool):
    """Return the comparable form of a field value; None means nothing recorded."""
    if value is None:
        return None
    try:
        if field in MONEY_FIELDS:
            return _money(value)
        if field == "service_date":
            return _date(value)
        result = _item(value) if field == "item_number" else _text(value)
        return result or None
    except (ValueError, InvalidOperation, TypeError) as error:
        if strict:
            raise ScoringError(f"Unreadable expected value for {field}: {value!r}") from error
        return _Invalid(value)


def _record(source: dict, *, strict: bool) -> dict:
    lines = source.get("line_items")
    if not isinstance(lines, list):
        if strict:
            raise ScoringError("line_items must be a list.")
        lines = []
    record = {name: normalise(name, source.get(name), strict=strict) for name in DOC_FIELDS}
    rows = []
    for line in lines:
        if not isinstance(line, dict):
            if strict:
                raise ScoringError("Each line item must be an object.")
            continue
        row = {name: normalise(name, line.get(name), strict=strict) for name in LINE_FIELDS}
        row["raw_description"] = normalise("raw_description", line.get("raw_description"), strict=strict)
        rows.append(row)
    record["line_items"] = rows
    return record


def load_map(path: Path) -> list[dict]:
    with Path(path).open(newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        if set(reader.fieldnames or ()) != set(MAP_COLUMNS):
            raise ScoringError("File map columns must be: " + ", ".join(MAP_COLUMNS))
        rows = []
        for row in reader:
            if None in row:
                raise ScoringError("A file map row has more cells than there are columns.")
            rows.append({key: (value or "").strip() for key, value in row.items()})
    if not rows:
        raise ScoringError("The file map lists no documents.")
    seen = set()
    for row in rows:
        if not SAFE_ID.fullmatch(row["document_id"]):
            raise ScoringError(f"Unsafe document_id: {row['document_id']!r}")
        for column in ("input_file", "gold_file"):
            if not SAFE_FILE.fullmatch(row[column]) or row[column].startswith("."):
                raise ScoringError(f"{column} for {row['document_id']} must be a plain file name.")
        if Path(row["input_file"]).suffix.lower() not in INPUT_TYPES:
            raise ScoringError(f"Input for {row['document_id']} must be .pdf or .txt.")
        if row["document_id"] in seen:
            raise ScoringError(f"Duplicate document_id: {row['document_id']}")
        seen.add(row["document_id"])
        for column in ("input_sha256", "gold_sha256"):
            row[column] = row[column].lower()
            if not HEX64.fullmatch(row[column]):
                raise ScoringError(f"{column} for {row['document_id']} is not a SHA-256 value.")
        if not row["family"]:
            raise ScoringError(f"Missing family for {row['document_id']}.")
    return rows


def load_gold(path: Path, row: dict) -> dict:
    try:
        source = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, ValueError) as error:
        raise ScoringError(f"Unreadable expected output: {path.name}") from error
    if not isinstance(source, dict):
        raise ScoringError(f"Expected output is not an object: {path.name}")
    missing = (set(DOC_FIELDS) | {"document_id", "family", "line_items"}) - source.keys()
    if missing:
        raise ScoringError(f"{path.name} is missing: {', '.join(sorted(missing))}")
    if source["document_id"] != row["document_id"] or source["family"] != row["family"]:
        raise ScoringError(f"{path.name} does not match its file map row.")
    for line in source["line_items"] if isinstance(source["line_items"], list) else []:
        if isinstance(line, dict):
            absent = (set(LINE_FIELDS) | {"raw_description"}) - line.keys()
            if absent:
                raise ScoringError(f"A line item in {path.name} is missing: {', '.join(sorted(absent))}")
    return _record(source, strict=True)


def load_output(path: Path):
    """Return the comparable output, or None for a recorded failure."""
    try:
        source = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    if not isinstance(source, dict) or "error" in source:
        return None
    return _record(source, strict=False)


def _empty_counts() -> dict:
    return {"tp": 0, "fp": 0, "fn": 0, "invented": 0, "wrong": 0, "missed": 0, "correct_abstentions": 0}


def _tally(counts: dict, expected, output) -> None:
    if expected is None and output is None:
        counts["correct_abstentions"] += 1
    elif expected is None:
        counts["fp"] += 1
        counts["invented"] += 1
    elif output is None:
        counts["fn"] += 1
        counts["missed"] += 1
    elif expected == output:
        counts["tp"] += 1
    else:
        counts["fp"] += 1
        counts["fn"] += 1
        counts["wrong"] += 1


def _agreement(expected_row: dict, output_row: dict) -> int:
    names = LINE_FIELDS + ("raw_description",)
    return sum(1 for name in names
               if expected_row[name] is not None and expected_row[name] == output_row[name])


def _assign(scores: list) -> list:
    """Maximum-total one-to-one assignment (Hungarian algorithm); returns (row, column) pairs."""
    n, m = len(scores), len(scores[0])
    transpose = n > m
    if transpose:
        scores = [list(column) for column in zip(*scores, strict=True)]
        n, m = m, n
    top = max(max(row) for row in scores)
    cost = [[top - value for value in row] for row in scores]
    u, v, p, way = [0] * (n + 1), [0] * (m + 1), [0] * (m + 1), [0] * (m + 1)
    for i in range(1, n + 1):
        p[0], j0 = i, 0
        minv, used = [math.inf] * (m + 1), [False] * (m + 1)
        while True:
            used[j0] = True
            i0, delta, j1 = p[j0], math.inf, 0
            for j in range(1, m + 1):
                if not used[j]:
                    current = cost[i0 - 1][j - 1] - u[i0] - v[j]
                    if current < minv[j]:
                        minv[j], way[j] = current, j0
                    if minv[j] < delta:
                        delta, j1 = minv[j], j
            for j in range(m + 1):
                if used[j]:
                    u[p[j]] += delta
                    v[j] -= delta
                else:
                    minv[j] -= delta
            j0 = j1
            if p[j0] == 0:
                break
        while j0:
            j1 = way[j0]
            p[j0] = p[j1]
            j0 = j1
    pairs = [(p[j] - 1, j - 1) for j in range(1, m + 1) if p[j]]
    return sorted((c, r) for r, c in pairs) if transpose else sorted(pairs)


def match_rows(expected_rows: list, output_rows: list):
    """One-to-one matching that maximises agreeing fields; zero-agreement pairs stay unmatched."""
    if not expected_rows or not output_rows:
        return [], list(range(len(expected_rows))), list(range(len(output_rows)))
    scores = [[_agreement(e, o) for o in output_rows] for e in expected_rows]
    pairs = [(r, c) for r, c in _assign(scores) if scores[r][c] > 0]
    used_e = {r for r, _ in pairs}
    used_o = {c for _, c in pairs}
    return (pairs, [i for i in range(len(expected_rows)) if i not in used_e],
            [j for j in range(len(output_rows)) if j not in used_o])


EMPTY_OUTPUT = {**{name: None for name in DOC_FIELDS}, "line_items": []}


def score_document(expected: dict, output: dict | None) -> dict:
    output = output or EMPTY_OUTPUT
    fields = {name: _empty_counts() for name in DOC_FIELDS + LINE_FIELDS}
    for name in DOC_FIELDS:
        _tally(fields[name], expected[name], output[name])
    pairs, missing, extra = match_rows(expected["line_items"], output["line_items"])
    correct_descriptions = 0
    for e, o in pairs:
        for name in LINE_FIELDS:
            _tally(fields[name], expected["line_items"][e][name], output["line_items"][o][name])
        if expected["line_items"][e]["raw_description"] == output["line_items"][o]["raw_description"]:
            correct_descriptions += 1
    # An unmatched row was not abstained on, so only recorded values are counted.
    for e in missing:
        for name in LINE_FIELDS:
            if expected["line_items"][e][name] is not None:
                _tally(fields[name], expected["line_items"][e][name], None)
    for o in extra:
        for name in LINE_FIELDS:
            if output["line_items"][o][name] is not None:
                _tally(fields[name], None, output["line_items"][o][name])
    return {
        "fields": fields,
        "rows": {"expected": len(expected["line_items"]), "output": len(output["line_items"]),
                 "matched": len(pairs), "missing": len(missing), "extra": len(extra)},
        "descriptions": {"matched": len(pairs), "correct": correct_descriptions},
        "exact_match": all(c["fp"] == 0 and c["fn"] == 0 for c in fields.values()),
    }


def _prf(tp: int, fp: int, fn: int) -> dict:
    def ratio(a, b):
        return round(a / b, 4) if b else None
    return {"precision": ratio(tp, tp + fp), "recall": ratio(tp, tp + fn),
            "f1": ratio(2 * tp, 2 * tp + fp + fn)}


def bootstrap_f1(document_totals: list, resamples: int = BOOTSTRAP_RESAMPLES,
                 seed: int = BOOTSTRAP_SEED):
    """95% percentile interval for micro F1, resampling whole documents."""
    if not document_totals:
        return None
    rng = random.Random(seed)
    n = len(document_totals)
    values = []
    for _ in range(resamples):
        tp = fp = fn = 0
        for _ in range(n):
            a, b, c = document_totals[rng.randrange(n)]
            tp, fp, fn = tp + a, fp + b, fn + c
        if 2 * tp + fp + fn:
            values.append(2 * tp / (2 * tp + fp + fn))
    if not values:
        return None
    values.sort()
    pick = lambda q: values[round(q * (len(values) - 1))]  # noqa: E731
    return [round(pick(0.025), 4), round(pick(0.975), 4)]


def wilson(successes: int, n: int, z: float = 1.959963984540054):
    if n == 0:
        return None
    p = successes / n
    denominator = 1 + z * z / n
    centre = (p + z * z / (2 * n)) / denominator
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / denominator
    return [round(max(0.0, centre - half), 4), round(min(1.0, centre + half), 4)]


def _totals(fields: dict):
    return (sum(c["tp"] for c in fields.values()), sum(c["fp"] for c in fields.values()),
            sum(c["fn"] for c in fields.values()))


def summarise(scored: list) -> dict:
    """scored: (map row, status, document score) for one pipeline."""
    per_field = {name: _empty_counts() for name in DOC_FIELDS + LINE_FIELDS}
    rows = {"expected": 0, "output": 0, "matched": 0, "missing": 0, "extra": 0}
    families, totals = {}, []
    exact = correct_descriptions = matched = 0
    status_counts = {"ok": 0, "empty": 0, "failed": 0}
    for row, status, result in scored:
        status_counts[status] += 1
        for name, counts in result["fields"].items():
            for key, value in counts.items():
                per_field[name][key] += value
        for key in rows:
            rows[key] += result["rows"][key]
        document_total = _totals(result["fields"])
        totals.append(document_total)
        families.setdefault(row["family"], []).append(document_total)
        exact += result["exact_match"]
        matched += result["descriptions"]["matched"]
        correct_descriptions += result["descriptions"]["correct"]
    tp, fp, fn = _totals(per_field)
    n = len(scored)
    return {
        "documents": n,
        "status": status_counts,
        "micro": {"tp": tp, "fp": fp, "fn": fn, **_prf(tp, fp, fn), "f1_ci95": bootstrap_f1(totals)},
        "invented_values": sum(c["invented"] for c in per_field.values()),
        "document_exact_match": {"count": exact, "rate": round(exact / n, 4) if n else None,
                                 "ci95": wilson(exact, n)},
        "per_field": {name: {**counts, **_prf(counts["tp"], counts["fp"], counts["fn"])}
                      for name, counts in per_field.items()},
        "per_family": {family: {"documents": len(values),
                                **_prf(*map(sum, zip(*values, strict=True))),
                                "f1_ci95": bootstrap_f1(values)}
                       for family, values in sorted(families.items())},
        "rows": rows,
        "descriptions": {"matched_rows": matched, "correct": correct_descriptions,
                         "rate": round(correct_descriptions / matched, 4) if matched else None},
    }


def _status(output: dict | None) -> str:
    if output is None:
        return "failed"
    if not output["line_items"] and all(output[name] is None for name in DOC_FIELDS):
        return "empty"
    return "ok"


def load_expected(rows: list, gold_dir: Path) -> dict:
    expected = {}
    for row in rows:
        path = Path(gold_dir) / row["gold_file"]
        if not path.is_file():
            raise ScoringError(f"Missing expected output: {row['gold_file']}")
        if sha256(path) != row["gold_sha256"]:
            raise ScoringError(f"Expected output differs from the file map: {row['gold_file']}")
        expected[row["document_id"]] = load_gold(path, row)
    return expected


def check_handoff(map_path: Path, gold_dir: Path, inputs_dir: Path | None = None) -> int:
    """Custodian check before release: every expected output and every hash in the map."""
    map_path, gold_dir = Path(map_path), Path(gold_dir)
    for path, label in ((map_path, "The file map"), (gold_dir, "The expected outputs folder")):
        require_private(path, label)
    rows = load_map(map_path)
    if inputs_dir is not None:
        require_private(inputs_dir, "The inputs folder")
        for row in rows:
            path = Path(inputs_dir) / row["input_file"]
            if not path.is_file():
                raise ScoringError(f"Missing input: {row['input_file']}")
            if sha256(path) != row["input_sha256"]:
                raise ScoringError(f"Input differs from the file map: {row['input_file']}")
    load_expected(rows, gold_dir)
    return len(rows)


def score(map_path: Path, gold_dir: Path, outputs_dir: Path) -> dict:
    map_path, gold_dir, outputs_dir = Path(map_path), Path(gold_dir), Path(outputs_dir)
    for path, label in ((map_path, "The file map"), (gold_dir, "The expected outputs folder"),
                        (outputs_dir, "The run folder")):
        require_private(path, label)
    rows = load_map(map_path)
    record_path = outputs_dir / "run_record.json"
    if not record_path.is_file():
        raise ScoringError("run_record.json is missing from the outputs folder.")
    run_record = json.loads(record_path.read_text(encoding="utf-8"))
    recorded = run_record.get("outputs", {})
    expected = load_expected(rows, gold_dir)
    pipelines = [name for name in PIPELINES if (outputs_dir / name).is_dir()]
    if not pipelines:
        raise ScoringError("No pipeline outputs found.")
    report = {
        "protocol": "docs/prototype/extraction_protocol.md",
        "scored_at_utc": datetime.now(timezone.utc).isoformat(),
        "map_sha256": sha256(map_path),
        "run_record_sha256": sha256(record_path),
        "documents": len(rows),
        "families": {family: sum(r["family"] == family for r in rows)
                     for family in sorted({r["family"] for r in rows})},
        "pipelines": {},
    }
    for pipeline in pipelines:
        scored = []
        for row in rows:
            name = f"{pipeline}/{row['document_id']}.json"
            path = outputs_dir / name
            if not path.is_file():
                raise ScoringError(f"Missing output: {name}")
            if recorded.get(name) != sha256(path):
                raise ScoringError(f"Output differs from run_record.json: {name}")
            output = load_output(path)
            scored.append((row, _status(output), score_document(expected[row["document_id"]], output)))
        report["pipelines"][pipeline] = summarise(scored)
    return report


def main(argv=None) -> None:
    parser = argparse.ArgumentParser(description="Score saved extraction outputs once.")
    parser.add_argument("--map", required=True, type=Path)
    parser.add_argument("--gold", required=True, type=Path)
    parser.add_argument("--outputs", type=Path)
    parser.add_argument("--report", type=Path)
    parser.add_argument("--check", action="store_true",
                        help="custodian: check the expected outputs and the file map, then stop")
    parser.add_argument("--inputs", type=Path, help="with --check: also check the input hashes")
    args = parser.parse_args(argv)
    if args.check:
        try:
            count = check_handoff(args.map, args.gold, args.inputs)
        except ScoringError as error:
            raise SystemExit(f"Not ready: {error}") from None
        print(f"{count} expected outputs follow the protocol and match the file map.")
        print("Post this hash in the group chat when the inputs and the file map are sent:")
        print("File map SHA-256", sha256(args.map))
        return
    if args.outputs is None or args.report is None:
        parser.error("--outputs and --report are required unless --check is given")
    if args.report.exists():
        raise SystemExit(f"Not scored: {args.report} already exists. The first result is never "
                         "replaced; record a rescore under a new name with its reason.")
    try:
        report = score(args.map, args.gold, args.outputs)
    except ScoringError as error:
        raise SystemExit(f"Not scored: {error}") from None
    with args.report.open("x", encoding="utf-8", newline="\n") as handle:
        json.dump(report, handle, indent=2, default=str)
        handle.write("\n")
    for pipeline, summary in report["pipelines"].items():
        micro = summary["micro"]
        print(f"{pipeline}: F1 {micro['f1']} (95% CI {micro['f1_ci95']}), "
              f"invented values {summary['invented_values']}, status {summary['status']}")
    print("Report:", args.report, "SHA-256", sha256(args.report))


if __name__ == "__main__":
    main()
