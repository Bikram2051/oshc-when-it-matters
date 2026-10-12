"""Scorer and runner checks on synthetic development documents only."""
import copy
import csv
import hashlib
import json
import subprocess
from pathlib import Path

import pytest

from eval import extraction as scorer
from oshc.schemas import ExtractionResult
from scripts import run_heldout_extraction as runner

ROOT = Path(__file__).resolve().parents[1]
GOLD = {
    "document_id": "DEV-001", "family": "dev_example",
    "provider": "Demonstration Clinic", "service_date": "2026-09-01",
    "total_charged": "105.00", "total_benefit": None, "total_gap": None,
    "line_items": [
        {"raw_description": "Short consultation", "item_number": "23", "charged": "90.00",
         "benefit_paid": None, "gap": None},
        {"raw_description": "Administration fee", "item_number": None, "charged": "15.00",
         "benefit_paid": None, "gap": None},
    ],
}
OUTPUT = {
    "extractor": "rules", "source_kind": "pasted_text",
    "provider": "Demonstration Clinic", "service_date": "2026-09-01",
    "total_charged": 105.0, "total_benefit": None, "total_gap": None, "warnings": [],
    "line_items": [
        {"raw_description": "Short consultation", "item_number": "23", "charged": 90.0,
         "benefit_paid": None, "gap": None},
        {"raw_description": "Administration fee", "item_number": None, "charged": 15.0,
         "benefit_paid": None, "gap": None},
    ],
}
PRINTED = 6  # provider, date, total charged, one item number and two line charges


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8", newline="\n")


def case(tmp_path, outputs, gold=GOLD, pipeline="rules"):
    gold_path = tmp_path / "gold" / "DEV-001.json"
    write_json(gold_path, gold)
    inputs = tmp_path / "inputs"
    inputs.mkdir()
    (inputs / "DEV-001.txt").write_text("synthetic\n", encoding="utf-8")
    run_dir = tmp_path / "run"
    record = {"outputs": {}}
    for document_id, output in outputs.items():
        path = run_dir / pipeline / f"{document_id}.json"
        write_json(path, output)
        record["outputs"][f"{pipeline}/{document_id}.json"] = digest(path)
    write_json(run_dir / "run_record.json", record)
    map_path = tmp_path / "map.csv"
    with map_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(scorer.MAP_COLUMNS)
        writer.writerow(["DEV-001", "dev_example", "DEV-001.txt", digest(inputs / "DEV-001.txt"),
                         "DEV-001.json", digest(gold_path)])
    return map_path, tmp_path / "gold", run_dir


def summary(tmp_path, output, gold=GOLD):
    report = scorer.score(*case(tmp_path, {"DEV-001": output}, gold))
    return report["pipelines"]["rules"]


def test_exact_output_scores_one(tmp_path):
    result = summary(tmp_path, OUTPUT)
    assert result["micro"]["f1"] == 1.0
    assert result["micro"]["tp"] == PRINTED
    assert result["invented_values"] == 0
    assert result["document_exact_match"]["count"] == 1
    assert result["per_field"]["total_gap"]["correct_abstentions"] == 1


def test_wrong_amount_is_a_false_positive_and_a_miss(tmp_path):
    output = copy.deepcopy(OUTPUT)
    output["line_items"][0]["charged"] = 95.0
    counts = summary(tmp_path, output)["per_field"]["charged"]
    assert (counts["tp"], counts["fp"], counts["fn"], counts["wrong"]) == (1, 1, 1, 1)


def test_value_where_nothing_is_printed_is_invented(tmp_path):
    output = copy.deepcopy(OUTPUT)
    output["total_gap"] = 15.0
    result = summary(tmp_path, output)
    assert result["invented_values"] == 1
    assert result["per_field"]["total_gap"]["fp"] == 1
    assert result["document_exact_match"]["count"] == 0


def test_missing_and_extra_rows_count_only_recorded_values(tmp_path):
    output = copy.deepcopy(OUTPUT)
    output["line_items"] = [output["line_items"][0],
                            {"raw_description": "Bulk-bill incentive", "item_number": "10990",
                             "charged": 7.0, "benefit_paid": None, "gap": None}]
    result = summary(tmp_path, output)
    assert result["rows"] == {"expected": 2, "output": 2, "matched": 1, "missing": 1, "extra": 1}
    assert result["per_field"]["charged"]["fn"] == 1
    assert result["per_field"]["charged"]["fp"] == 1
    assert result["per_field"]["item_number"]["invented"] == 1
    assert result["per_field"]["item_number"]["correct_abstentions"] == 0


def test_row_order_does_not_matter(tmp_path):
    output = copy.deepcopy(OUTPUT)
    output["line_items"].reverse()
    assert summary(tmp_path, output)["micro"]["f1"] == 1.0


def test_recorded_failure_misses_every_printed_value(tmp_path):
    result = summary(tmp_path, {"document_id": "DEV-001", "pipeline": "rules", "error": "X"})
    assert result["status"]["failed"] == 1
    assert (result["micro"]["tp"], result["micro"]["fn"]) == (0, PRINTED)
    assert result["micro"]["f1"] == 0.0


def test_empty_result_is_reported_separately(tmp_path):
    output = {**OUTPUT, "provider": None, "service_date": None, "total_charged": None,
              "line_items": []}
    result = summary(tmp_path, output)
    assert result["status"]["empty"] == 1
    assert result["micro"]["fn"] == PRINTED


def test_date_and_money_formats_compare_by_value(tmp_path):
    output = copy.deepcopy(OUTPUT)
    output["service_date"] = "01/09/2026"
    output["line_items"][0]["charged"] = "90"
    assert summary(tmp_path, output)["micro"]["f1"] == 1.0


def test_description_is_reported_but_not_in_the_headline(tmp_path):
    output = copy.deepcopy(OUTPUT)
    output["line_items"][0]["raw_description"] = "Short consult"
    result = summary(tmp_path, output)
    assert result["micro"]["f1"] == 1.0
    assert result["descriptions"] == {"matched_rows": 2, "correct": 1, "rate": 0.5}


def test_changed_expected_output_is_refused(tmp_path):
    map_path, gold_dir, run_dir = case(tmp_path, {"DEV-001": OUTPUT})
    write_json(gold_dir / "DEV-001.json", {**GOLD, "total_gap": "0.00"})
    with pytest.raises(scorer.ScoringError, match="differs from the file map"):
        scorer.score(map_path, gold_dir, run_dir)


def test_output_changed_after_the_run_is_refused(tmp_path):
    map_path, gold_dir, run_dir = case(tmp_path, {"DEV-001": OUTPUT})
    write_json(run_dir / "rules" / "DEV-001.json", {**OUTPUT, "total_gap": 1.0})
    with pytest.raises(scorer.ScoringError, match="run_record"):
        scorer.score(map_path, gold_dir, run_dir)


def test_invalid_expected_value_is_refused(tmp_path):
    gold = copy.deepcopy(GOLD)
    gold["line_items"][0]["charged"] = "ninety"
    with pytest.raises(scorer.ScoringError, match="Unreadable expected value"):
        scorer.score(*case(tmp_path, {"DEV-001": OUTPUT}, gold))


def test_report_is_written_once(tmp_path):
    map_path, gold_dir, run_dir = case(tmp_path, {"DEV-001": OUTPUT})
    report = tmp_path / "report.json"
    args = ["--map", str(map_path), "--gold", str(gold_dir), "--outputs", str(run_dir),
            "--report", str(report)]
    scorer.main(args)
    assert json.loads(report.read_text())["pipelines"]["rules"]["micro"]["f1"] == 1.0
    with pytest.raises(SystemExit, match="already exists"):
        scorer.main(args)


def test_map_rejects_duplicates_and_bad_hashes(tmp_path):
    path = tmp_path / "map.csv"
    row = ["A-1", "f", "a.txt", "0" * 64, "a.json", "0" * 64]
    with path.open("w", newline="") as handle:
        csv.writer(handle).writerows([scorer.MAP_COLUMNS, row, row])
    with pytest.raises(scorer.ScoringError, match="Duplicate"):
        scorer.load_map(path)
    with path.open("w", newline="") as handle:
        csv.writer(handle).writerows([scorer.MAP_COLUMNS, row[:3] + ["abc"] + row[4:]])
    with pytest.raises(scorer.ScoringError, match="SHA-256"):
        scorer.load_map(path)


def test_custodian_check_catches_problems_before_release(tmp_path, capsys):
    map_path, gold_dir, _ = case(tmp_path, {"DEV-001": OUTPUT})
    inputs = tmp_path / "inputs"
    assert scorer.check_handoff(map_path, gold_dir, inputs) == 1
    scorer.main(["--check", "--map", str(map_path), "--gold", str(gold_dir), "--inputs", str(inputs)])
    assert "File map SHA-256 " + digest(map_path) in capsys.readouterr().out
    (inputs / "DEV-001.txt").write_text("changed\n", encoding="utf-8")
    with pytest.raises(scorer.ScoringError, match="Input differs"):
        scorer.check_handoff(map_path, gold_dir, inputs)
    gold = copy.deepcopy(GOLD)
    gold["line_items"][0]["charged"] = "$90.00"
    map_path, gold_dir, _ = case(tmp_path / "second", {"DEV-001": OUTPUT}, gold)
    with pytest.raises(SystemExit, match="Not ready: Unreadable expected value"):
        scorer.main(["--check", "--map", str(map_path), "--gold", str(gold_dir)])


def test_map_accepts_plain_file_names_only(tmp_path):
    path = tmp_path / "map.csv"
    for input_file, message in (("../a.txt", "plain file name"), ("a.docx", ".pdf or .txt")):
        with path.open("w", newline="") as handle:
            csv.writer(handle).writerows([scorer.MAP_COLUMNS,
                                          ["A-1", "f", input_file, "0" * 64, "a.json", "0" * 64]])
        with pytest.raises(scorer.ScoringError, match=message):
            scorer.load_map(path)


def test_intervals_are_deterministic_and_bounded():
    totals = [(5, 1, 0), (4, 0, 2), (6, 0, 0), (3, 2, 2)]
    first = scorer.bootstrap_f1(totals)
    assert first == scorer.bootstrap_f1(totals)
    assert 0.0 <= first[0] <= first[1] <= 1.0
    assert scorer.wilson(0, 10) == [0.0, 0.2775]
    assert scorer.wilson(10, 10) == [0.7225, 1.0]


# Runner -------------------------------------------------------------------

DEV_TEXT = ROOT / "data/demo_dev/rules_reader_example.txt"


def runner_case(tmp_path, input_hash=None):
    inputs = tmp_path / "inputs"
    inputs.mkdir()
    (inputs / "DEV-001.txt").write_bytes(DEV_TEXT.read_bytes())
    gold_path = tmp_path / "gold" / "DEV-001.json"
    write_json(gold_path, GOLD)
    map_path = tmp_path / "map.csv"
    with map_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(scorer.MAP_COLUMNS)
        writer.writerow(["DEV-001", "dev_example", "DEV-001.txt",
                         input_hash or digest(inputs / "DEV-001.txt"),
                         "DEV-001.json", digest(gold_path)])
    return map_path, inputs, tmp_path / "gold"


@pytest.fixture
def unfrozen(monkeypatch):
    monkeypatch.setattr(runner, "verify_freeze", lambda: {"commit": "development test"})


def test_llm_pipeline_needs_explicit_live_settings(tmp_path, monkeypatch, unfrozen):
    monkeypatch.setenv("OSHC_OFFLINE", "1")
    monkeypatch.setenv("OSHC_ENABLE_LIVE", "0")
    map_path, inputs, _ = runner_case(tmp_path)
    with pytest.raises(SystemExit, match="paid calls"):
        runner.run(map_path, inputs, tmp_path / "run", ["llm"])
    assert not (tmp_path / "run").exists()


def test_changed_input_is_refused_before_any_output(tmp_path, unfrozen):
    map_path, inputs, _ = runner_case(tmp_path, input_hash="0" * 64)
    with pytest.raises(SystemExit, match="differs from the file map"):
        runner.run(map_path, inputs, tmp_path / "run", ["rules"])
    assert not (tmp_path / "run").exists()


def test_run_then_score_end_to_end_and_never_overwrite(tmp_path, unfrozen):
    map_path, inputs, gold_dir = runner_case(tmp_path)
    record = runner.run(map_path, inputs, tmp_path / "run", ["rules"])
    assert record["failures"] == {"rules": 0}
    assert set(record["outputs"]) == {"rules/DEV-001.json"}
    report = scorer.score(map_path, gold_dir, tmp_path / "run")
    assert report["pipelines"]["rules"]["micro"]["f1"] == 1.0
    with pytest.raises(SystemExit, match="already exists"):
        runner.run(map_path, inputs, tmp_path / "run", ["rules"])


def test_failure_is_recorded_not_skipped(tmp_path, monkeypatch, unfrozen):
    def broken(source):
        raise RuntimeError("synthetic failure")
    monkeypatch.setitem(runner.PIPELINES, "rules", broken)
    map_path, inputs, _ = runner_case(tmp_path)
    record = runner.run(map_path, inputs, tmp_path / "run", ["rules"])
    assert record["failures"] == {"rules": 1}
    saved = json.loads((tmp_path / "run/rules/DEV-001.json").read_text())
    assert saved["error"] == "RuntimeError: synthetic failure"


class FakeBudget:
    remaining = 5.0

    def status(self):
        return {"remaining": self.remaining, "blocked_for_review": False}


@pytest.fixture
def live(monkeypatch):
    monkeypatch.setenv("OSHC_OFFLINE", "0")
    monkeypatch.setenv("OSHC_ENABLE_LIVE", "1")
    monkeypatch.setenv("OSHC_API_KEY", "test-only")
    monkeypatch.delenv("OSHC_MODEL", raising=False)
    monkeypatch.setattr(runner, "Budget", FakeBudget)


def test_llm_responses_stay_in_the_run_folder(tmp_path, monkeypatch, unfrozen, live):
    committed = runner.llm.CACHE_DIR
    used = []

    def fake_llm(source):  # stands in for a paid call; nothing leaves this machine
        used.append(runner.llm.CACHE_DIR)
        runner.llm.CACHE_DIR.mkdir(parents=True, exist_ok=True)
        (runner.llm.CACHE_DIR / "response.json").write_text("{}\n", encoding="utf-8")
        return ExtractionResult(extractor="llm", source_kind="pasted_text", line_items=[],
                                warnings=["LLM extraction unavailable (ProviderError); "
                                          + "no bill values returned."])
    monkeypatch.setitem(runner.PIPELINES, "llm", fake_llm)
    map_path, inputs, _ = runner_case(tmp_path)
    record = runner.run(map_path, inputs, tmp_path / "run", ["llm"])
    assert used == [(tmp_path / "run").resolve() / "llm_cache" / "v2"]
    assert runner.llm.CACHE_DIR == committed
    assert set(record["llm_cache"]) == {"llm_cache/v2/response.json"}
    assert record["llm_unavailable"] == {"ProviderError": 1}


def test_llm_run_that_could_not_finish_is_refused(tmp_path, monkeypatch, unfrozen, live):
    monkeypatch.setattr(FakeBudget, "remaining", 0.01)
    map_path, inputs, _ = runner_case(tmp_path)
    with pytest.raises(SystemExit, match="spending allowance"):
        runner.run(map_path, inputs, tmp_path / "run", ["llm"])
    monkeypatch.delenv("OSHC_API_KEY")
    with pytest.raises(SystemExit, match="OSHC_API_KEY"):
        runner.run(map_path, inputs, tmp_path / "run", ["llm"])
    assert not (tmp_path / "run").exists()


def test_heldout_files_stay_out_of_tracked_folders(tmp_path, unfrozen):
    if subprocess.run(["git", "-C", str(ROOT), "check-ignore", "-q", "data/heldout/x"],
                      capture_output=True, check=False).returncode != 0:
        pytest.skip("No git checkout with the held-out ignore rule.")
    scorer.require_private(tmp_path, "A folder outside the repository")
    scorer.require_private(ROOT / "data/heldout/run-1", "An ignored folder")
    with pytest.raises(scorer.ScoringError, match="does not ignore"):
        scorer.require_private(ROOT / "docs/heldout-run", "A tracked folder")
    map_path, inputs, _ = runner_case(tmp_path)
    with pytest.raises(SystemExit, match="does not ignore"):
        runner.run(map_path, inputs, ROOT / "docs/heldout-run", ["rules"])
    assert not (ROOT / "docs/heldout-run").exists()


def test_extraction_code_is_still_the_frozen_version():
    try:
        commit = subprocess.run(["git", "-C", str(ROOT), "rev-parse", "HEAD"],
                                capture_output=True, text=True, check=True).stdout
    except (OSError, subprocess.CalledProcessError):
        pytest.skip("No git metadata in this copy.")
    assert commit
    for path, expected in runner.FROZEN.items():
        actual = subprocess.run(["git", "-C", str(ROOT), "rev-parse", f"HEAD:{path}"],
                                capture_output=True, text=True, check=False).stdout.strip()
        assert actual == expected, (
            f"{path} changed after the 1 October freeze. No extraction changes until the "
            "held-out run is recorded (docs/prototype/extraction_protocol.md).")
