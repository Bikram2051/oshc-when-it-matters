"""MBS matcher tests. Written before the implementation.

This module decides whether a line on a student's bill gets an MBS descriptor
attached. A wrong descriptor produces a wrong benefit figure, so most of the
behaviour tested here is about WHEN TO REFUSE, not when to match.

Owner: Bikram Bhattarai. Reviewer: Aayush Khade.
"""

import dataclasses
from pathlib import Path

import pytest

from oshc.billexplainer.mbs import (
    ABSTAIN_NOTE,
    MBS_MATCH_FLOOR,
    build_index,
    load_mbs_csv,
    match,
    normalise,
)

FIXTURE = Path(__file__).resolve().parent.parent / "data" / "mbs" / "mbs_fixture.csv"


@pytest.fixture(scope="module")
def index():
    return build_index(load_mbs_csv(FIXTURE), source_file=str(FIXTURE))


# --- item number path -------------------------------------------------------


def test_exact_item_number_matches_with_full_confidence(index):
    m = match(index, item_number="99023", description="anything at all")
    assert m.matched is True
    assert m.score == 1.0
    assert m.item_number == "99023"
    assert m.schedule_fee is not None


def test_item_number_wins_over_a_conflicting_description(index):
    m = match(index, item_number="99023", description="hospital bed day charge")
    assert m.item_number == "99023"
    assert m.matched is True


def test_unknown_item_number_falls_back_to_description(index):
    m = match(index, item_number="00000", description="Level B consultation, consulting rooms")
    assert m.matched is True
    assert m.item_number == "99023"


def test_item_number_is_normalised_before_lookup(index):
    assert match(index, item_number=" 99023 ", description="").matched is True
    assert match(index, item_number="99023.0", description="").matched is True
    assert match(index, item_number="0099023", description="").matched is True
    assert match(index, item_number="Item 99023", description="").matched is True
    assert match(index, item_number="Item No. 99023", description="").matched is True


def test_two_numbers_in_the_item_field_abstain_rather_than_pick_one(index):
    """'2 x 99023' could be a quantity and an item. Picking either is a guess."""
    m = match(index, item_number="2 x 99023", description="")
    assert m.matched is False
    assert m.schedule_fee is None


# --- description path -------------------------------------------------------


def test_close_description_matches_above_the_floor(index):
    m = match(index, description="level b consultation consulting rooms")
    assert m.matched is True
    assert m.score >= MBS_MATCH_FLOOR


def test_distant_description_abstains(index):
    m = match(index, description="Shared ward accommodation, 3 bed days")
    assert m.matched is False
    assert m.descriptor is None
    assert m.note == ABSTAIN_NOTE


def test_score_just_below_the_floor_abstains(index):
    m = match(index, description="Level B consultation, consulting rooms", floor=1.01)
    assert m.matched is False
    assert m.note == ABSTAIN_NOTE


def test_empty_description_abstains_rather_than_raising(index):
    for value in ("", "   ", None):
        m = match(index, description=value)
        assert m.matched is False
        assert m.note == ABSTAIN_NOTE


# --- invariants that protect the benefit figure ----------------------------


def test_an_unmatched_result_never_carries_a_descriptor_or_fee(index):
    m = match(index, description="consumables and dressings")
    assert m.matched is False
    assert m.descriptor is None
    assert m.schedule_fee is None
    assert m.item_number is None


def test_a_matched_result_always_carries_a_fee(index):
    m = match(index, description="Level B consultation, consulting rooms")
    assert m.matched is True
    assert m.schedule_fee is not None and m.schedule_fee > 0


def test_result_is_immutable(index):
    m = match(index, item_number="99023", description="")
    with pytest.raises(dataclasses.FrozenInstanceError):
        m.matched = False


def test_score_is_always_a_fraction(index):
    for desc in ("Level B consultation", "bed day", "", "pathology episode"):
        assert 0.0 <= match(index, description=desc).score <= 1.0


# --- normalisation ----------------------------------------------------------


@pytest.mark.parametrize(
    "raw,expected",
    [
        ("  Level   B  CONSULTATION ", "level b consultation"),
        ("Pathology - episode (out of hospital)", "pathology episode out of hospital"),
        ("Consult,  Level  B.", "consult level b"),
    ],
)
def test_normalise_strips_case_punctuation_and_runs_of_space(raw, expected):
    assert normalise(raw) == expected


# --- loader -----------------------------------------------------------------


def test_loader_rejects_a_file_missing_a_required_column(tmp_path):
    bad = tmp_path / "bad.csv"
    bad.write_text("ItemNum,Description\n1,no fee column here\n", encoding="utf-8")
    with pytest.raises(ValueError) as err:
        load_mbs_csv(bad)
    assert "ScheduleFee" in str(err.value)


def test_loader_records_capture_provenance(index):
    assert index.source_file.endswith("mbs_fixture.csv")
    assert index.record_count == 4
    assert index.captured_on == "2026-09-19"


def test_index_is_built_from_every_row(index):
    assert len(index.rows) == index.record_count


# --- over-matching guards ---------------------------------------------------
# These exist because token_set_ratio scores a subset at 1.0. Found by manual
# probing after the first suite went green, not by the suite itself.


def test_a_bare_generic_line_does_not_inherit_a_specific_item(index):
    """'Consultation' must not silently become Level B and pick up its fee."""
    for vague in (
        "Consultation",
        "consult",
        "Doctor's fee",
        "Medical service",
        "consultation, consulting rooms",
    ):
        m = match(index, description=vague)
        assert m.matched is False, f"over-matched on: {vague!r}"
        assert m.schedule_fee is None


def test_wording_matching_two_items_equally_abstains_with_a_useful_note():
    """A tie above the floor must abstain and say why, not pick the first row."""
    from decimal import Decimal

    from oshc.billexplainer.mbs import AMBIGUOUS_NOTE, MbsRow

    tied = build_index(
        [
            MbsRow("99901", "physiotherapy session type a", Decimal("60.00")),
            MbsRow("99902", "physiotherapy session type b", Decimal("95.00")),
        ],
        source_file="tied.csv",
    )
    m = match(tied, description="physiotherapy session type")
    assert m.matched is False
    assert m.note == AMBIGUOUS_NOTE
    assert m.schedule_fee is None


def test_a_fully_specified_line_still_matches_the_right_level(index):
    b = match(index, description="Level B consultation, consulting rooms")
    c = match(index, description="Level C consultation, consulting rooms")
    assert b.matched and c.matched
    assert b.item_number == "99023"
    assert c.item_number == "99036"
    assert b.schedule_fee != c.schedule_fee
