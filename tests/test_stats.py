"""Paired significance tests validated against SciPy.

Reference values were computed with SciPy 1.18.1 (NumPy 2.x) on 2026-09-26
and hard-coded so CI does not need SciPy:

* ``scipy.special.betainc(a, b, x)``
* ``2 * scipy.stats.t.sf(abs(t), df)``
* ``scipy.stats.ttest_rel(candidate, baseline)``
* ``scipy.stats.permutation_test((candidate, baseline), mean(x - y),
  permutation_type="samples", alternative="two-sided", n_resamples=np.inf)``
  (exact), and with ``n_resamples=199999, random_state=1`` for the 40-query
  randomized case.
"""

from __future__ import annotations

import math

import pytest

from toolkit_rag_quality.stats import (
    betainc,
    paired_permutation_test,
    paired_t_test,
    t_two_sided_p,
)

BETAINC = [
    (0.5, 0.5, 0.3, 0.36901011956554536),
    (2.0, 3.0, 0.4, 0.5247999999999999),
    (5.0, 0.5, 0.9, 0.3166429150200122),
    (10.0, 0.5, 0.99, 0.6579281751567845),
    (0.5, 0.5, 0.999, 0.9798649583666235),
    (1.5, 20.0, 0.05, 0.44342120168569027),
    (149.5, 0.5, 0.97, 0.002567124501872944),
]

T_TWO_SIDED = [
    (0.0, 5, 1.0),
    (1.0, 1, 0.5000000000000001),
    (2.0, 7, 0.08561932856297605),
    (-2.5, 19, 0.02174041116839744),
    (3.7, 299, 0.00025656048790663173),
    (10.0, 3, 0.0021283990584141503),
    (0.3, 1000, 0.7642395041672441),
]

N8 = (
    [0.2, 0.5, 0.9, 0.4, 0.7, 0.3, 0.8, 0.6],
    [0.3, 0.4, 0.95, 0.4, 0.5, 0.1, 0.85, 0.35],
)
N12 = (
    [0.324, 0.151, 0.651, 0.072, 0.536, 0.366, 0.058, 0.507, 0.037, 0.434, 0.07, 0.091],
    [0.324, 0.0, 0.701, 0.0, 0.436, 0.416, 0.0, 0.557, 0.087, 0.434, 0.0, 0.0],
)
N40 = (
    [0.047, 0.858, 0.29, 0.144, 0.118, 0.308, 0.816, 0.181, 0.582, 0.639,
     0.372, 0.548, 0.063, 0.06, 0.206, 0.68, 0.428, 0.314, 0.586, 0.453,
     0.3, 0.794, 0.699, 0.244, 0.574, 0.525, 0.875, 0.729, 0.288, 0.98,
     0.118, 0.418, 0.757, 0.152, 0.489, 0.039, 0.668, 0.765, 0.573, 0.875],
    [0.0, 1.0, 0.086, 0.0, 0.0, 0.346, 0.936, 0.083, 0.515, 0.553,
     0.267, 0.301, 0.301, 0.008, 0.134, 0.785, 0.372, 0.246, 0.458, 0.435,
     0.299, 0.789, 0.668, 0.126, 0.536, 0.634, 0.877, 0.645, 0.068, 0.999,
     0.284, 0.192, 0.797, 0.021, 0.327, 0.071, 0.91, 0.474, 0.587, 0.911],
)  # fmt: skip

TTEST_REL = {  # (t, p) from scipy.stats.ttest_rel(candidate, baseline)
    "n8": (N8, -1.4286230627501744, 0.1961764507307272),
    "n12": (N12, -1.3989716704939927, 0.18938061100584508),
    "n40": (N40, -1.923273382719698, 0.061768493744141235),
}

PERM_EXACT = {  # (mean diff, p, number of sign patterns)
    "n8": (N8, -0.06875, 0.234375, 256),
    "n12": (N12, -0.028500000000000008, 0.193359375, 4096),
}


@pytest.mark.parametrize(("a", "b", "x", "expected"), BETAINC)
def test_betainc_matches_scipy(a: float, b: float, x: float, expected: float) -> None:
    assert math.isclose(betainc(a, b, x), expected, rel_tol=1e-12, abs_tol=1e-15)


@pytest.mark.parametrize(("t", "df", "expected"), T_TWO_SIDED)
def test_t_two_sided_p_matches_scipy(t: float, df: int, expected: float) -> None:
    assert math.isclose(t_two_sided_p(t, df), expected, rel_tol=1e-9)


@pytest.mark.parametrize("name", sorted(TTEST_REL))
def test_paired_t_test_matches_scipy_ttest_rel(name: str) -> None:
    (base, cand), t, p = TTEST_REL[name]
    result = paired_t_test(base, cand)
    assert result.statistic is not None and result.p_value is not None
    assert math.isclose(result.statistic, t, rel_tol=1e-12)
    assert math.isclose(result.p_value, p, rel_tol=1e-9)
    assert result.n == len(base)


@pytest.mark.parametrize("name", sorted(PERM_EXACT))
def test_exact_permutation_test_matches_scipy(name: str) -> None:
    (base, cand), mean, p, patterns = PERM_EXACT[name]
    result = paired_permutation_test(base, cand)
    assert result.exact is True
    assert result.n_resamples == patterns
    assert math.isclose(result.mean_diff, mean, rel_tol=1e-12)
    assert result.p_value == p  # exact enumeration: identical, not approximately equal


def test_randomized_permutation_test_is_close_to_scipy_and_reproducible() -> None:
    base, cand = N40
    first = paired_permutation_test(base, cand, n_resamples=10000, seed=0)
    again = paired_permutation_test(base, cand, n_resamples=10000, seed=0)
    assert first.exact is False
    assert first.p_value == again.p_value
    assert first.p_value is not None
    # SciPy, 199999 resamples: 0.06223. Monte Carlo error at 10000 resamples is ~0.005.
    assert abs(first.p_value - 0.06223) < 0.01


def test_identical_scores_are_not_significant() -> None:
    scores = [0.1, 0.5, 0.9]
    assert paired_t_test(scores, scores).p_value == 1.0
    assert paired_permutation_test(scores, scores).p_value == 1.0


def test_constant_shift_t_test_is_documented_edge_case() -> None:
    # SciPy returns t = -inf, p = 0 here; this implementation reports p = 0
    # and no statistic, so the JSON report never contains infinity.
    result = paired_t_test([1.0, 2.0, 3.0], [0.5, 1.5, 2.5])
    assert result.statistic is None
    assert result.p_value == 0.0


def test_fewer_than_two_queries_has_no_p_value() -> None:
    assert paired_t_test([0.5], [0.4]).p_value is None
    assert paired_permutation_test([0.5], [0.4]).p_value is None


def test_length_mismatch_is_an_error() -> None:
    with pytest.raises(ValueError):
        paired_t_test([0.1, 0.2], [0.1])
