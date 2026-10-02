"""Cross-validation of the @k metrics against trec_eval reference values.

The EXPECTED numbers below were produced by pytrec_eval (package
``pytrec-eval-terrier`` 0.5.10, a Python binding of NIST trec_eval) on
2026-09-26, then hard-coded here so CI does not need pytrec_eval installed.

How they were generated:

* qrels: every id in ``QRELS[q]`` has relevance 1.
* run: ``RUN[q]`` truncated to K, scored ``100 - rank`` so trec_eval ranks the
  documents in list order. The run is truncated before evaluation because
  trec_eval's ``recip_rank`` has no cutoff.
* measures: ``P_5``, ``recall_5``, ``ndcg_cut_5``, ``map_cut_5``,
  ``recip_rank`` and ``success_5``, mapped to this toolkit's ``precision``,
  ``recall``, ``ndcg``, ``ap``, ``mrr`` and ``hit``.

To regenerate, install ``pytrec-eval-terrier`` and evaluate the same qrels and
run with ``pytrec_eval.RelevanceEvaluator(qrels, measures).evaluate(run)``.
"""

from __future__ import annotations

import math

import pytest

from toolkit_rag_quality.retrieval import score_retrieval

K = 5

QRELS: dict[str, list[str]] = {
    "q1": ["d1", "d3", "d7"],
    "q2": ["d2"],
    "q3": ["d1", "d2", "d3", "d4", "d5", "d6"],
    "q4": ["a", "b"],
    "q5": ["a"],
    "q6": ["a", "b", "c"],
}

RUN: dict[str, list[str]] = {
    "q1": ["d1", "d2", "d3", "d4", "d5", "d6", "d7"],  # d7 falls outside the cutoff
    "q2": ["d9", "d8", "d2"],  # short run, hit at rank 3
    "q3": ["d6", "x", "d5", "y", "d4"],  # more relevant docs than k
    "q4": ["z"],  # no hits
    "q5": ["x", "y", "z", "w", "v", "a"],  # only hit is at rank 6
    "q6": ["c"],  # single-document run
}

EXPECTED: dict[str, dict[str, float]] = {
    "q1": {
        "precision": 0.4,
        "recall": 0.6666666666666666,
        "ndcg": 0.7039180890341347,
        "ap": 0.5555555555555555,
        "mrr": 1.0,
        "hit": 1.0,
    },
    "q2": {
        "precision": 0.2,
        "recall": 1.0,
        "ndcg": 0.5,
        "ap": 0.3333333333333333,
        "mrr": 0.3333333333333333,
        "hit": 1.0,
    },
    "q3": {
        "precision": 0.6,
        "recall": 0.5,
        "ndcg": 0.639945385422766,
        "ap": 0.37777777777777777,
        "mrr": 1.0,
        "hit": 1.0,
    },
    "q4": {"precision": 0.0, "recall": 0.0, "ndcg": 0.0, "ap": 0.0, "mrr": 0.0, "hit": 0.0},
    "q5": {"precision": 0.0, "recall": 0.0, "ndcg": 0.0, "ap": 0.0, "mrr": 0.0, "hit": 0.0},
    "q6": {
        "precision": 0.2,
        "recall": 0.3333333333333333,
        "ndcg": 0.46927872602275644,
        "ap": 0.3333333333333333,
        "mrr": 1.0,
        "hit": 1.0,
    },
}

SUMMARY_KEYS = {
    "precision": "precision_at_k",
    "recall": "recall_at_k",
    "ndcg": "ndcg_at_k",
    "ap": "map_at_k",
    "mrr": "mrr_at_k",
    "hit": "hit_rate_at_k",
}


def _report():
    return score_retrieval(
        queries=[{"id": q, "relevant_ids": ids} for q, ids in QRELS.items()],
        retrieved=[{"id": q, "retrieved_ids": ids} for q, ids in RUN.items()],
        k=K,
    )


@pytest.mark.parametrize("qid", sorted(EXPECTED))
def test_per_query_metrics_match_trec_eval(qid: str) -> None:
    per_query = {row["id"]: row for row in _report().per_query}
    row = per_query[qid]
    for metric, expected in EXPECTED[qid].items():
        actual = float(row[metric])
        assert math.isclose(actual, expected, rel_tol=1e-9, abs_tol=1e-12), (
            f"{qid}.{metric}: got {actual}, trec_eval {expected}"
        )


def test_macro_averages_match_trec_eval() -> None:
    summary = _report().summary
    for metric, key in SUMMARY_KEYS.items():
        expected = sum(EXPECTED[q][metric] for q in EXPECTED) / len(EXPECTED)
        assert math.isclose(float(summary[key]), expected, rel_tol=1e-9, abs_tol=1e-12), key
