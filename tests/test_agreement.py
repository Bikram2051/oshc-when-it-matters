import pytest

from oshc.agreement import bootstrap_ci, cohens_kappa, with_ci


def test_perfect_agreement_is_one():
    labels = ["C1", "C2", "C3", "S", "C2", "C4"]
    assert cohens_kappa(labels, labels).kappa == 1.0


def test_chance_level_agreement_is_near_zero():
    a = ["Y", "N"] * 50
    b = ["Y", "Y", "N", "N"] * 25
    assert abs(cohens_kappa(a, b).kappa) < 0.1


def test_systematic_disagreement_is_negative():
    a = ["Y", "Y", "N", "N"]
    b = ["N", "N", "Y", "Y"]
    assert cohens_kappa(a, b).kappa < 0


def test_worked_example_matches_hand_calculation():
    # 20 items: 10 agree Y, 5 agree N, 3 a=Y b=N, 2 a=N b=Y
    a = ["Y"] * 10 + ["N"] * 5 + ["Y"] * 3 + ["N"] * 2
    b = ["Y"] * 10 + ["N"] * 5 + ["N"] * 3 + ["Y"] * 2
    r = cohens_kappa(a, b)
    assert r.observed_agreement == 0.75
    # pY = 13/20 * 12/20 = 0.39 ; pN = 7/20 * 8/20 = 0.14 ; pe = 0.53
    assert r.expected_agreement == 0.53
    assert r.kappa == pytest.approx((0.75 - 0.53) / (1 - 0.53), abs=1e-4)


def test_single_category_raises_rather_than_dividing_by_zero():
    with pytest.raises(ValueError) as err:
        cohens_kappa(["Y"] * 10, ["Y"] * 10)
    assert "undefined" in str(err.value)


def test_mismatched_lengths_are_rejected():
    with pytest.raises(ValueError):
        cohens_kappa(["Y", "N"], ["Y"])


def test_empty_input_is_rejected():
    with pytest.raises(ValueError):
        cohens_kappa([], [])


def test_confidence_interval_brackets_the_point_estimate():
    a = ["Y"] * 10 + ["N"] * 5 + ["Y"] * 3 + ["N"] * 2
    b = ["Y"] * 10 + ["N"] * 5 + ["N"] * 3 + ["Y"] * 2
    r = with_ci(a, b, iterations=500)
    assert r.ci_low <= r.kappa <= r.ci_high


def test_small_n_produces_a_wide_interval():
    """The point of reporting the interval: n=15 cannot support a claim."""
    a = ["C1", "C2", "C3", "C4", "S"] * 3
    b = ["C1", "C2", "C4", "C4", "S"] * 3
    lo, hi = bootstrap_ci(a, b, iterations=500)
    assert hi - lo > 0.25


def test_bootstrap_is_reproducible_under_a_fixed_seed():
    a = ["Y", "N"] * 20
    b = ["Y", "Y", "N", "N"] * 10
    assert bootstrap_ci(a, b, iterations=300) == bootstrap_ci(a, b, iterations=300)


def test_per_category_agreement_is_reported():
    a = ["C1", "C1", "C2", "C2"]
    b = ["C1", "C2", "C2", "C2"]
    r = cohens_kappa(a, b)
    assert r.per_category["C1"] == pytest.approx(1 / 2)


def test_interpretation_band_is_reported():
    labels = ["C1", "C2", "C3", "S"]
    assert cohens_kappa(labels, labels).interpretation() == "almost perfect"
