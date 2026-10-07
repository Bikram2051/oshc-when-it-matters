import csv
from pathlib import Path


def test_page_17_85_percent_categories_are_present():
    path = Path("data/rules/benefit_rules.csv")

    with path.open(newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))

    rules = {row["category"]: row for row in rows}

    assert rules["radiology_out_of_hospital"]["value"] == "85"
    assert rules["allied_health_out_of_hospital"]["value"] == "85"