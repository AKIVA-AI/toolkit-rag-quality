"""Paired significance tests for per-query metric differences.

Both tests take the per-query scores of a baseline and a candidate over the
same queries, in the same order, and test whether the mean difference
(candidate - baseline) is zero. They are two-sided and dependency-free.

* :func:`paired_t_test` is the paired Student t-test (``scipy.stats.ttest_rel``).
* :func:`paired_permutation_test` is Fisher's paired randomization test: each
  query's difference keeps its size and gets a random sign. With at most
  ``EXACT_MAX_N`` queries every sign pattern is enumerated, as
  ``scipy.stats.permutation_test(..., permutation_type="samples")`` does
  when ``n_resamples >= 2**n``; beyond that, ``n_resamples`` random patterns
  are drawn from a seeded generator, so results are reproducible.

The p-values are validated against SciPy in ``tests/test_stats.py``.
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass

#: Largest number of queries for which the permutation test is exact (2**n patterns).
EXACT_MAX_N = 16

_EPS = 3e-16
_TINY = 1e-300


def _betacf(a: float, b: float, x: float) -> float:
    """Continued fraction for the incomplete beta function (modified Lentz)."""
    qab = a + b
    qap = a + 1.0
    qam = a - 1.0
    c = 1.0
    d = 1.0 - qab * x / qap
    if abs(d) < _TINY:
        d = _TINY
    d = 1.0 / d
    h = d
    for m in range(1, 1000):
        m2 = 2 * m
        aa = m * (b - m) * x / ((qam + m2) * (a + m2))
        d = 1.0 + aa * d
        if abs(d) < _TINY:
            d = _TINY
        c = 1.0 + aa / c
        if abs(c) < _TINY:
            c = _TINY
        d = 1.0 / d
        h *= d * c
        aa = -(a + m) * (qab + m) * x / ((a + m2) * (qap + m2))
        d = 1.0 + aa * d
        if abs(d) < _TINY:
            d = _TINY
        c = 1.0 + aa / c
        if abs(c) < _TINY:
            c = _TINY
        d = 1.0 / d
        delta = d * c
        h *= delta
        if abs(delta - 1.0) < _EPS:
            return h
    raise ArithmeticError("incomplete beta continued fraction did not converge")


def betainc(a: float, b: float, x: float) -> float:
    """Regularized incomplete beta function I_x(a, b) (``scipy.special.betainc``)."""
    if a <= 0 or b <= 0:
        raise ValueError("a and b must be positive")
    if x <= 0.0:
        return 0.0
    if x >= 1.0:
        return 1.0
    log_front = (
        math.lgamma(a + b) - math.lgamma(a) - math.lgamma(b) + a * math.log(x) + b * math.log1p(-x)
    )
    front = math.exp(log_front)
    if x < (a + 1.0) / (a + b + 2.0):
        return front * _betacf(a, b, x) / a
    return 1.0 - front * _betacf(b, a, 1.0 - x) / b


def t_two_sided_p(t: float, df: float) -> float:
    """Two-sided p-value of Student's t: P(|T| >= |t|) with ``df`` degrees of freedom."""
    if df <= 0:
        raise ValueError("df must be positive")
    if math.isinf(t):
        return 0.0
    return betainc(df / 2.0, 0.5, df / (df + t * t))


@dataclass(frozen=True)
class PairedTest:
    """Result of a paired test. ``statistic`` is t for the t-test and the mean
    difference for the permutation test. ``p_value`` is None when the test is
    undefined (fewer than two queries)."""

    test: str
    n: int
    mean_diff: float
    statistic: float | None
    p_value: float | None
    exact: bool = False
    n_resamples: int = 0

    def to_dict(self) -> dict[str, object]:
        return {
            "test": self.test,
            "n": self.n,
            "mean_diff": self.mean_diff,
            "statistic": self.statistic,
            "p_value": self.p_value,
            "exact": self.exact,
            "n_resamples": self.n_resamples,
        }


def _diffs(baseline: list[float], candidate: list[float]) -> list[float]:
    if len(baseline) != len(candidate):
        raise ValueError("baseline and candidate must have the same number of queries")
    return [float(c) - float(b) for b, c in zip(baseline, candidate, strict=True)]


def paired_t_test(baseline: list[float], candidate: list[float]) -> PairedTest:
    """Two-sided paired t-test of candidate - baseline.

    Matches ``scipy.stats.ttest_rel`` except in two degenerate cases where
    SciPy returns NaN or infinity: when every difference is identical, the
    p-value here is 1.0 if the differences are all zero, and 0.0 otherwise
    (with ``statistic`` None).
    """
    d = _diffs(baseline, candidate)
    n = len(d)
    mean = sum(d) / n if n else 0.0
    if n < 2:
        return PairedTest("t-test", n, mean, None, None)
    var = sum((x - mean) ** 2 for x in d) / (n - 1)
    if var <= 0.0 or all(x == d[0] for x in d):
        return PairedTest("t-test", n, mean, 0.0 if mean == 0 else None, 1.0 if mean == 0 else 0.0)
    t = mean / math.sqrt(var / n)
    return PairedTest("t-test", n, mean, t, t_two_sided_p(t, n - 1))


def _chunk_tables(d: list[float], width: int = 8) -> list[list[float]]:
    """For each chunk of ``width`` differences, the signed sum for every sign pattern."""
    tables: list[list[float]] = []
    for start in range(0, len(d), width):
        chunk = d[start : start + width]
        sums = [0.0]
        for x in chunk:
            sums = [s + x for s in sums] + [s - x for s in sums]
        tables.append(sums)
    return tables


def paired_permutation_test(
    baseline: list[float],
    candidate: list[float],
    *,
    n_resamples: int = 10000,
    seed: int = 0,
) -> PairedTest:
    """Two-sided paired randomization (sign-flip) test on the mean difference.

    The two-sided p-value is ``min(1, 2 * min(P(null <= obs), P(null >= obs)))``,
    SciPy's definition. With ``n <= EXACT_MAX_N`` every one of the ``2**n``
    sign patterns is used (exact). Otherwise ``n_resamples`` random patterns
    are drawn and each one-sided p-value is ``(count + 1) / (n_resamples + 1)``,
    as SciPy does for a randomized test.
    """
    if n_resamples < 1:
        raise ValueError("n_resamples must be positive")
    d = _diffs(baseline, candidate)
    n = len(d)
    if n < 2:
        return PairedTest("permutation", n, sum(d) / n if n else 0.0, None, None)
    observed = sum(d)
    tol = 1e-12 * max(1.0, sum(abs(x) for x in d))
    tables = _chunk_tables(d)

    if n <= EXACT_MAX_N:
        null = [0.0]
        for table in tables:
            null = [s + t for s in null for t in table]
        total = len(null)
        greater = sum(1 for s in null if s >= observed - tol)
        less = sum(1 for s in null if s <= observed + tol)
        p = min(1.0, 2.0 * min(greater, less) / total)
        return PairedTest("permutation", n, observed / n, observed / n, p, True, total)

    # Seeded PRNG for reproducible resampling, not for security.
    rng = random.Random(seed)  # nosec B311
    widths = [int(math.log2(len(t))) for t in tables]
    greater = less = 0
    for _ in range(n_resamples):
        s = 0.0
        for table, w in zip(tables, widths, strict=True):
            s += table[rng.getrandbits(w)]
        if s >= observed - tol:
            greater += 1
        if s <= observed + tol:
            less += 1
    p_greater = (greater + 1) / (n_resamples + 1)
    p_less = (less + 1) / (n_resamples + 1)
    p = min(1.0, 2.0 * min(p_greater, p_less))
    return PairedTest("permutation", n, observed / n, observed / n, p, False, n_resamples)
