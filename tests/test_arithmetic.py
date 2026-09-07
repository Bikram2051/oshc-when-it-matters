"""Tests written before the implementation. Money code.

If a test here fails, the answer is never to relax the test.
"""
from decimal import Decimal

import pytest

from oshc.arithmetic import expected_benefit, gap, _money
from oshc.schemas import BenefitRule


def rule(basis, value):
    return BenefitRule(
        category="test", description="test", benefit_basis=basis,
        value=value, pds_page="p.1", captured_on="2026-09-07",
    )


def test_percent_of_charge():
    assert expected_benefit(rule("percent_of_charge", 80), 100.00) == Decimal("80.00")


def test_percent_of_mbs_uses_schedule_fee_not_charge():
    got = expected_benefit(rule("percent_of_mbs", 100), charged=95.00, schedule_fee=41.20)
    assert got == Decimal("41.20")


def test_percent_of_mbs_abstains_without_schedule_fee():
    assert expected_benefit(rule("percent_of_mbs", 100), charged=95.00) is None


def test_fixed_benefit():
    assert expected_benefit(rule("fixed", 25.00), 90.00) == Decimal("25.00")


def test_benefit_never_exceeds_charge():
    assert expected_benefit(rule("fixed", 500.00), 90.00) == Decimal("90.00")


def test_no_rule_abstains():
    assert expected_benefit(None, 100.00) is None


def test_explicit_abstain_rule_abstains():
    assert expected_benefit(rule("abstain", None), 100.00) is None


def test_gap_is_charge_minus_benefit():
    assert gap(95.00, Decimal("41.20")) == Decimal("53.80")


def test_gap_unknown_when_benefit_unknown():
    assert gap(95.00, None) is None


def test_gap_never_negative():
    assert gap(40.00, Decimal("50.00")) == Decimal("0.00")


def test_rounding_is_half_up_at_cents():
    assert _money(41.205) == Decimal("41.21")


@pytest.mark.parametrize("charged,pct,expected", [
    (89.95, 85, "76.46"),
    (0.00, 85, "0.00"),
    (33.33, 100, "33.33"),
])
def test_percent_cases(charged, pct, expected):
    assert expected_benefit(rule("percent_of_charge", pct), charged) == Decimal(expected)
