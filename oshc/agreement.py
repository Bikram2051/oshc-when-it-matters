"""Cohen's kappa with an interval, and the checks that must pass before it.

A kappa reported without its confidence interval, its n, and its per-category
breakdown is a number that cannot be challenged, which means it cannot be
trusted either. This module refuses to compute unless the two coders'
record sets align exactly and every label is inside the permitted set.

Owner: Bikram Bhattarai.
"""

from __future__ import annotations

import random
from collections import Counter
from dataclasses import dataclass


@dataclass(frozen=True)
class KappaResult:
    kappa: float
    observed_agreement: float
    expected_agreement: float
    n: int
    categories: tuple[str, ...]
    ci_low: float | None = None
    ci_high: float | None = None
    per_category: dict[str, float] | None = None

    def interpretation(self) -> str:
        """Landis and Koch (1977) bands. Report the band AND the interval."""
        k = self.kappa
        if k < 0.00:
            return "poor (worse than chance)"
        if k < 0.21:
            return "slight"
        if k < 0.41:
            return "fair"
        if k < 0.61:
            return "moderate"
        if k < 0.81:
            return "substantial"
        return "almost perfect"


def cohens_kappa(a: list[str], b: list[str]) -> KappaResult:
    if len(a) != len(b):
        raise ValueError(f"coders disagree on n: {len(a)} vs {len(b)}")
    if not a:
        raise ValueError("no paired labels to compare")

    n = len(a)
    cats = tuple(sorted(set(a) | set(b)))
    observed = sum(1 for x, y in zip(a, b, strict=True) if x == y) / n

    ca, cb = Counter(a), Counter(b)
    expected = sum((ca[c] / n) * (cb[c] / n) for c in cats)

    if expected == 1.0:
        # Both coders used one category for everything. Kappa is undefined:
        # chance agreement is already total. Say so rather than dividing by zero.
        raise ValueError(
            "kappa undefined: expected agreement is 1.0 because both coders used "
            "a single category. Report percentage agreement and the distribution "
            "instead."
        )

    kappa = (observed - expected) / (1 - expected)

    per_cat = {}
    for c in cats:
        idx = [i for i in range(n) if a[i] == c or b[i] == c]
        if idx:
            per_cat[c] = sum(1 for i in idx if a[i] == b[i]) / len(idx)

    return KappaResult(
        kappa=round(kappa, 4),
        observed_agreement=round(observed, 4),
        expected_agreement=round(expected, 4),
        n=n,
        categories=cats,
        per_category={k: round(v, 4) for k, v in per_cat.items()},
    )


def bootstrap_ci(
    a: list[str],
    b: list[str],
    iterations: int = 2000,
    seed: int = 20260919,
    alpha: float = 0.05,
) -> tuple[float, float]:
    """Percentile bootstrap. Resamples pairs, not labels."""
    rng = random.Random(seed)
    n = len(a)
    draws = []
    for _ in range(iterations):
        idx = [rng.randrange(n) for _ in range(n)]
        try:
            draws.append(cohens_kappa([a[i] for i in idx], [b[i] for i in idx]).kappa)
        except ValueError:
            continue  # degenerate resample, skip it
    if len(draws) < iterations * 0.5:
        raise ValueError(
            "too many degenerate resamples; n is too small for a bootstrap CI"
        )
    draws.sort()
    lo = draws[int((alpha / 2) * len(draws))]
    hi = draws[int((1 - alpha / 2) * len(draws)) - 1]
    return round(lo, 4), round(hi, 4)


def with_ci(a: list[str], b: list[str], **kw) -> KappaResult:
    base = cohens_kappa(a, b)
    lo, hi = bootstrap_ci(a, b, **kw)
    return KappaResult(**{**base.__dict__, "ci_low": lo, "ci_high": hi})
