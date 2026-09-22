"""MBS item lookup and descriptor matching.

What this module is for: a student's bill shows a line like "Level B
consultation" and sometimes an item number. Attaching the right MBS descriptor
and schedule fee is what lets oshc.arithmetic compute a percent_of_mbs benefit.
Attaching the WRONG one produces a confident, wrong dollar figure on a bill,
which is the worst failure this prototype can have.

So the contract is deliberately conservative:

  - an exact item number is trusted and wins over the description
  - a description is matched only above MBS_MATCH_FLOOR
  - anything else abstains, and an abstaining result carries no descriptor,
    no item number and no schedule fee, only ABSTAIN_NOTE

Never relax the floor to make a number appear. An abstention is a correct
answer here; a guess is not.

Owner: Bikram Bhattarai. Reviewer: Aayush Khade.
"""

from __future__ import annotations

import csv
import re
import sqlite3
from dataclasses import dataclass, field
from decimal import Decimal
from pathlib import Path

from rapidfuzz import fuzz, process

# Mirrors oshc.config.MBS_MATCH_FLOOR. Kept as a module constant so the matcher
# can be tested without importing app config.
MBS_MATCH_FLOOR = 0.88

ABSTAIN_NOTE = "not an MBS item, check the PDS"
AMBIGUOUS_NOTE = "item number needed, this wording matches more than one MBS item"

# Scorer choice is a safety decision, not a tuning detail.
#
# token_set_ratio was the obvious pick and is wrong here: it returns 100
# whenever the query's tokens are a SUBSET of the candidate's. A bill line
# reading only "Consultation" therefore scored 1.0 against "Level B
# consultation, consulting rooms" and would have attached that item's schedule
# fee to a line that never named a level. token_sort_ratio is symmetric and
# penalises the missing tokens, so a partial line falls below the floor and
# abstains. Measured on the fixture: "Consultation" scores 48.98 by sort and
# 100.00 by set.
#
# Cost of this choice, stated rather than hidden: real bill wording that omits
# words present in the MBS descriptor will abstain rather than match. That is
# the intended direction. The item number path carries the common case, and
# Australian medical invoices normally print the item number.

# Runner-up within this margin of the winner means the wording does not pick
# out one item. One point, because genuine MBS descriptors differ from their
# neighbours by a single token and a wider margin rejects correct matches.
AMBIGUITY_MARGIN = 0.01

REQUIRED_COLUMNS = ("ItemNum", "Description", "ScheduleFee")

_PUNCT = re.compile(r"[^a-z0-9 ]+")
_SPACE = re.compile(r"\s+")


@dataclass(frozen=True)
class MbsRow:
    item_number: str
    description: str
    schedule_fee: Decimal
    category: str | None = None
    captured_on: str | None = None


@dataclass(frozen=True)
class MbsIndex:
    rows: tuple[MbsRow, ...]
    source_file: str
    captured_on: str | None = None
    by_item: dict[str, MbsRow] = field(default_factory=dict)
    by_norm: dict[str, MbsRow] = field(default_factory=dict)

    @property
    def record_count(self) -> int:
        return len(self.rows)


@dataclass(frozen=True)
class MbsMatch:
    """Result of one lookup.

    Invariant, asserted in the constructor: matched is True only when
    descriptor, item_number and schedule_fee are all present.
    """

    matched: bool
    score: float
    item_number: str | None = None
    descriptor: str | None = None
    schedule_fee: Decimal | None = None
    note: str | None = None

    def __post_init__(self) -> None:
        if self.matched:
            missing = [
                name
                for name, value in (
                    ("descriptor", self.descriptor),
                    ("item_number", self.item_number),
                    ("schedule_fee", self.schedule_fee),
                )
                if value is None
            ]
            if missing:
                raise ValueError(f"matched result missing {', '.join(missing)}")
        else:
            if any((self.descriptor, self.item_number, self.schedule_fee)):
                raise ValueError("an abstaining result must carry no MBS detail")


def _abstain(score: float = 0.0) -> MbsMatch:
    return MbsMatch(matched=False, score=score, note=ABSTAIN_NOTE)


def normalise(text: str | None) -> str:
    """Lowercase, strip punctuation, collapse whitespace. Nothing clever."""
    if not text:
        return ""
    return _SPACE.sub(" ", _PUNCT.sub(" ", text.lower())).strip()


def normalise_item_number(raw: str | None) -> str:
    """Reduce an extracted item number to its canonical form.

    Accepts "23", " 23 ", "23.0", "00023", "Item 23", "Item No. 23", "MBS 23".
    Returns "" when the text holds more than one number ("2 x 23"), because
    picking one would be a guess and a guessed item number carries a fee.
    """
    if raw is None:
        return ""
    text = re.sub(r"(\d)\.0+\b", r"\1", str(raw).strip())
    runs = re.findall(r"\d+", text)
    if len(runs) == 1:
        # MBS item numbers are never zero-padded; OCR output sometimes is.
        return runs[0].lstrip("0") or "0"
    if not runs:
        return re.sub(r"[^0-9A-Za-z]", "", text).upper()
    return ""


def load_mbs_csv(path: str | Path, column_map: dict[str, str] | None = None) -> list[MbsRow]:
    """Read an MBS export into rows.

    column_map renames the export's own headers onto REQUIRED_COLUMNS, because
    the official download has changed its column names before. A missing
    required column raises rather than silently producing an empty table.
    """
    path = Path(path)
    rows: list[MbsRow] = []
    with open(path, newline="", encoding="utf-8-sig") as fh:
        lines = [ln for ln in fh if not ln.lstrip().startswith("#")]
    reader = csv.DictReader(lines)
    headers = [column_map.get(h, h) if column_map else h for h in (reader.fieldnames or [])]
    missing = [c for c in REQUIRED_COLUMNS if c not in headers]
    if missing:
        raise ValueError(
            f"{path.name} is missing required column(s): {', '.join(missing)}. "
            f"Found: {', '.join(headers) or 'none'}. Pass column_map to rename them."
        )
    for raw in reader:
        row = {column_map.get(k, k) if column_map else k: v for k, v in raw.items()}
        item = normalise_item_number(row.get("ItemNum"))
        desc = (row.get("Description") or "").strip()
        fee_raw = (row.get("ScheduleFee") or "").replace("$", "").replace(",", "").strip()
        if not item or not desc or not fee_raw:
            continue
        rows.append(
            MbsRow(
                item_number=item,
                description=desc,
                schedule_fee=Decimal(fee_raw),
                category=(row.get("Category") or None),
                captured_on=(row.get("CapturedOn") or None),
            )
        )
    return rows


def build_index(rows: list[MbsRow], source_file: str | Path = "") -> MbsIndex:
    by_item = {r.item_number: r for r in rows}
    by_norm = {normalise(r.description): r for r in rows}
    captured = next((r.captured_on for r in rows if r.captured_on), None)
    name = str(source_file) or (rows and "mbs_fixture.csv" or "")
    return MbsIndex(
        rows=tuple(rows),
        source_file=name,
        captured_on=captured,
        by_item=by_item,
        by_norm=by_norm,
    )


def match(
    index: MbsIndex,
    description: str | None = None,
    item_number: str | None = None,
    floor: float = MBS_MATCH_FLOOR,
) -> MbsMatch:
    """Resolve one bill line to an MBS row, or abstain."""
    key = normalise_item_number(item_number)
    if key and key in index.by_item:
        row = index.by_item[key]
        return MbsMatch(
            matched=True,
            score=1.0,
            item_number=row.item_number,
            descriptor=row.description,
            schedule_fee=row.schedule_fee,
        )

    norm = normalise(description)
    if not norm or not index.by_norm:
        return _abstain()

    candidates = list(index.by_norm.keys())
    hits = process.extract(norm, candidates, scorer=fuzz.token_sort_ratio, limit=2)
    if not hits:
        return _abstain()

    best, raw_score, _ = hits[0]
    score = round(raw_score / 100.0, 4)
    if score < floor:
        return _abstain(score)

    if len(hits) > 1:
        runner_up = round(hits[1][1] / 100.0, 4)
        if score - runner_up < AMBIGUITY_MARGIN:
            return MbsMatch(matched=False, score=score, note=AMBIGUOUS_NOTE)

    row = index.by_norm[best]
    return MbsMatch(
        matched=True,
        score=score,
        item_number=row.item_number,
        descriptor=row.description,
        schedule_fee=row.schedule_fee,
    )


def to_sqlite(rows: list[MbsRow], db_path: str | Path) -> int:
    """Write rows to SQLite. Returns the row count written."""
    db_path = Path(db_path)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(db_path)
    try:
        con.execute("DROP TABLE IF EXISTS mbs_items")
        con.execute(
            """CREATE TABLE mbs_items (
                   item_number TEXT PRIMARY KEY,
                   description TEXT NOT NULL,
                   description_norm TEXT NOT NULL,
                   schedule_fee TEXT NOT NULL,
                   category TEXT,
                   captured_on TEXT
               )"""
        )
        con.executemany(
            "INSERT OR REPLACE INTO mbs_items VALUES (?,?,?,?,?,?)",
            [
                (
                    r.item_number,
                    r.description,
                    normalise(r.description),
                    str(r.schedule_fee),
                    r.category,
                    r.captured_on,
                )
                for r in rows
            ],
        )
        con.commit()
        return con.execute("SELECT COUNT(*) FROM mbs_items").fetchone()[0]
    finally:
        con.close()


def from_sqlite(db_path: str | Path) -> MbsIndex:
    con = sqlite3.connect(db_path)
    try:
        cur = con.execute(
            "SELECT item_number, description, schedule_fee, category, captured_on FROM mbs_items"
        )
        rows = [
            MbsRow(
                item_number=i,
                description=d,
                schedule_fee=Decimal(f),
                category=c,
                captured_on=o,
            )
            for i, d, f, c, o in cur.fetchall()
        ]
    finally:
        con.close()
    return build_index(rows, source_file=str(db_path))
