"""Final evidence never forwards arbitrary report text or trusts changed bytes."""
import json
import shutil
from pathlib import Path
from oshc.final_results import FILES, load_final

ROOT = Path(__file__).resolve().parents[1]


def test_manifest_mismatch_suppresses_results(tmp_path):
    for path in [*FILES.values(), "docs/prototype/final_results_manifest.json"]:
        target = tmp_path / path
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / path, target)
    selected = load_final(tmp_path)
    assert selected and "outcomes" not in repr(selected) and "predictions" not in repr(selected)
    path = tmp_path / FILES["current"]
    data = json.loads(path.read_text())
    data["chat"]["refusal_recall"]["k"] = 0
    path.write_text(json.dumps(data))
    assert load_final(tmp_path) is None
