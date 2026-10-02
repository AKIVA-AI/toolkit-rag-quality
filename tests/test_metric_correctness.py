"""Correctness tests for the @k metrics against their standard definitions.

These cases deliberately use runs that are *shorter* than k, which is where a
metric that normalizes by the number of returned documents (instead of by k)
gives the wrong answer.
"""

from __future__ import annotations

import math

import pytest

from toolkit_rag_quality.retrieval import score_retrieval


def _one(relevant: list[str], retrieved: list[str], k: int) -> dict:
    report = score_retrieval(
        queries=[{"id": "q", "relevant_ids": relevant}],
        retrieved=[{"id": "q", "retrieved_ids": retrieved}],
        k=k,
    )
    return report.per_query[0]


def test_precision_at_k_divides_by_k_not_by_returned_count() -> None:
    # 1 relevant doc returned out of a 5-slot cutoff -> P@5 = 1/5.
    pq = _one(["a", "b", "c"], ["a"], k=5)
    assert pq["precision"] == 1 / 5


def test_precision_at_k_short_run_equals_padded_run() -> None:
    short = _one(["a", "b", "c"], ["a"], k=5)
    padded = _one(["a", "b", "c"], ["a", "x", "y", "z", "w"], k=5)
    assert short["precision"] == padded["precision"]


def test_ndcg_ideal_dcg_uses_min_relevant_and_k() -> None:
    # 3 relevant docs, k=5: IDCG = 1/log2(2) + 1/log2(3) + 1/log2(4).
    pq = _one(["a", "b", "c"], ["a"], k=5)
    idcg = sum(1.0 / math.log2(i + 2) for i in range(3))
    assert math.isclose(pq["ndcg"], 1.0 / idcg, rel_tol=1e-12)
    assert math.isclose(pq["ndcg"], 0.46928, abs_tol=1e-5)


def test_ndcg_short_run_equals_padded_run() -> None:
    short = _one(["a", "b", "c"], ["a"], k=5)
    padded = _one(["a", "b", "c"], ["a", "x", "y", "z", "w"], k=5)
    assert math.isclose(short["ndcg"], padded["ndcg"], rel_tol=1e-12)


def test_ndcg_ideal_capped_at_k_when_more_relevant_than_k() -> None:
    # 5 relevant docs but k=2: a perfect top-2 must score exactly 1.0.
    pq = _one(["a", "b", "c", "d", "e"], ["a", "b"], k=2)
    assert math.isclose(pq["ndcg"], 1.0, rel_tol=1e-12)


@pytest.mark.parametrize("k", [0, -1, -5])
def test_non_positive_k_is_rejected(k: int) -> None:
    with pytest.raises(ValueError, match="k must be a positive integer"):
        _one(["a"], ["a", "b"], k=k)


def test_duplicate_ids_do_not_push_metrics_above_one() -> None:
    pq = _one(["a"], ["a", "a", "a"], k=3)
    for name in ("recall", "precision", "mrr", "ndcg", "ap"):
        assert 0.0 <= pq[name] <= 1.0, name
    assert math.isclose(pq["ndcg"], 1.0, rel_tol=1e-12)
    assert math.isclose(pq["ap"], 1.0, rel_tol=1e-12)
    # Only one distinct relevant doc in the top-3 slots.
    assert math.isclose(pq["precision"], 1 / 3, rel_tol=1e-12)


def test_duplicates_removed_before_cutoff_first_occurrence_wins() -> None:
    # After de-duplication the ranking is [x, a, b]; the second "x" does not
    # consume a top-k slot, so both relevant docs land inside k=3.
    pq = _one(["a", "b"], ["x", "x", "a", "b"], k=3)
    assert pq["retrieved_count"] == 3
    assert pq["hit_count"] == 2
    assert math.isclose(pq["recall"], 1.0, rel_tol=1e-12)
    assert math.isclose(pq["mrr"], 1 / 2, rel_tol=1e-12)
    assert math.isclose(pq["ap"], (1 / 2 + 2 / 3) / 2, rel_tol=1e-12)
    assert pq["duplicates_removed"] == 1
