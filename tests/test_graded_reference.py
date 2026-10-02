"""Graded relevance cross-checked against trec_eval reference values.

The EXPECTED numbers were produced by pytrec_eval (``pytrec-eval-terrier``
0.5.10, a Python binding of NIST trec_eval) on 2026-09-26 and hard-coded so CI
does not need pytrec_eval.

How they were generated:

* qrels: ``QRELS`` as given (integer grades, including 0 and -1).
* run: ``RUN_SCORES`` as given, ordered the trec_eval way (score descending,
  ties by doc id descending) and truncated to the top K, because trec_eval's
  ``recip_rank`` has no cutoff.
* ``pytrec_eval.RelevanceEvaluator(QRELS, measures, relevance_level=L)`` with
  measures ``P_5``, ``recall_5``, ``ndcg_cut_5``, ``map_cut_5``,
  ``recip_rank`` and ``success_5``, for L = 1 and L = 2.

What this pins down: nDCG uses the grade as a linear gain and ignores the
relevance level; negative grades give no gain; a query whose judgments are
all below the relevance level is still scored (as zero, except nDCG); tied
scores in a TREC run are broken by doc id, descending.
"""

from __future__ import annotations

import math
from pathlib import Path

import pytest

from toolkit_rag_quality.formats import read_trec_run
from toolkit_rag_quality.retrieval import score_run

K = 5

QRELS: dict[str, dict[str, int]] = {
    "g1": {"a": 3, "b": 2, "c": 1, "d": 0},
    "g2": {"a": 1, "b": 2, "z": -1},
    "g3": {"a": 0, "b": 0},
    "g4": {"a": 2, "b": 1},
    "g5": {"d1": 3, "d2": 3, "d3": 2, "d4": 2, "d5": 1, "d6": 1, "d7": 1},
    "g6": {"a": 1},
}

RUN_SCORES: dict[str, dict[str, float]] = {
    "g1": {"d": 5.0, "c": 4.0, "b": 3.0, "a": 2.0, "x": 1.0},
    "g2": {"z": 3.0, "a": 2.0, "b": 1.0},
    "g3": {"a": 1.0},
    "g4": {"a": 1.0, "b": 1.0, "c": 1.0},  # all tied
    "g5": {"d7": 9.0, "x": 8.5, "d1": 8.0, "d5": 7.0, "d3": 6.0, "d2": 5.0, "d4": 4.0},
    "g6": {"q": 2.0, "r": 2.0, "a": 2.0},  # all tied
}

#: trec_eval's document order for RUN_SCORES (printed by the generator).
TREC_ORDER: dict[str, list[str]] = {
    "g1": ["d", "c", "b", "a", "x"],
    "g2": ["z", "a", "b"],
    "g3": ["a"],
    "g4": ["c", "b", "a"],
    "g5": ["d7", "x", "d1", "d5", "d3", "d2", "d4"],
    "g6": ["r", "q", "a"],
}

EXPECTED: dict[int, dict[str, dict[str, float]]] = {
    1: {
        "g1": {
            "ap": 0.6388888888888888,
            "hit": 1.0,
            "mrr": 0.5,
            "ndcg": 0.6138273133441086,
            "precision": 0.6,
            "recall": 1.0,
        },
        "g2": {
            "ap": 0.5833333333333333,
            "hit": 1.0,
            "mrr": 0.5,
            "ndcg": 0.6199062332840657,
            "precision": 0.4,
            "recall": 1.0,
        },
        "g3": {"ap": 0.0, "hit": 0.0, "mrr": 0.0, "ndcg": 0.0, "precision": 0.0, "recall": 0.0},
        "g4": {
            "ap": 0.5833333333333333,
            "hit": 1.0,
            "mrr": 0.5,
            "ndcg": 0.6199062332840657,
            "precision": 0.4,
            "recall": 1.0,
        },
        "g5": {
            "ap": 0.45952380952380956,
            "hit": 1.0,
            "mrr": 1.0,
            "ndcg": 0.5187487285795699,
            "precision": 0.8,
            "recall": 0.5714285714285714,
        },
        "g6": {
            "ap": 0.3333333333333333,
            "hit": 1.0,
            "mrr": 0.3333333333333333,
            "ndcg": 0.5,
            "precision": 0.2,
            "recall": 1.0,
        },
    },
    2: {
        "g1": {
            "ap": 0.41666666666666663,
            "hit": 1.0,
            "mrr": 0.3333333333333333,
            "ndcg": 0.6138273133441086,
            "precision": 0.4,
            "recall": 1.0,
        },
        "g2": {
            "ap": 0.3333333333333333,
            "hit": 1.0,
            "mrr": 0.3333333333333333,
            "ndcg": 0.6199062332840657,
            "precision": 0.2,
            "recall": 1.0,
        },
        "g3": {"ap": 0.0, "hit": 0.0, "mrr": 0.0, "ndcg": 0.0, "precision": 0.0, "recall": 0.0},
        "g4": {
            "ap": 0.3333333333333333,
            "hit": 1.0,
            "mrr": 0.3333333333333333,
            "ndcg": 0.6199062332840657,
            "precision": 0.2,
            "recall": 1.0,
        },
        "g5": {
            "ap": 0.18333333333333335,
            "hit": 1.0,
            "mrr": 0.3333333333333333,
            "ndcg": 0.5187487285795699,
            "precision": 0.4,
            "recall": 0.5,
        },
        "g6": {"ap": 0.0, "hit": 0.0, "mrr": 0.0, "ndcg": 0.5, "precision": 0.0, "recall": 0.0},
    },
}


@pytest.fixture()
def trec_run_file(tmp_path: Path) -> Path:
    lines = []
    for qid, docs in RUN_SCORES.items():
        # Rank column deliberately wrong: trec_eval ignores it and so must we.
        lines.extend(f"{qid} Q0 {doc} 1 {score} tag" for doc, score in docs.items())
    path = tmp_path / "run.trec"
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def test_trec_run_ranking_matches_trec_eval_tie_breaking(trec_run_file: Path) -> None:
    assert read_trec_run(trec_run_file) == TREC_ORDER


@pytest.mark.parametrize("level", [1, 2])
@pytest.mark.parametrize("qid", sorted(QRELS))
def test_graded_per_query_metrics_match_trec_eval(
    trec_run_file: Path, level: int, qid: str
) -> None:
    report = score_run(qrels=QRELS, run=read_trec_run(trec_run_file), k=K, relevance_level=level)
    row = {r["id"]: r for r in report.per_query}[qid]
    for metric, expected in EXPECTED[level][qid].items():
        actual = float(row[metric])
        assert math.isclose(actual, expected, rel_tol=1e-9, abs_tol=1e-12), (
            f"level {level} {qid}.{metric}: got {actual}, trec_eval {expected}"
        )


@pytest.mark.parametrize("level", [1, 2])
def test_graded_macro_averages_match_trec_eval(trec_run_file: Path, level: int) -> None:
    summary = score_run(
        qrels=QRELS, run=read_trec_run(trec_run_file), k=K, relevance_level=level
    ).summary
    keys = {
        "precision": "precision_at_k",
        "recall": "recall_at_k",
        "ndcg": "ndcg_at_k",
        "ap": "map_at_k",
        "mrr": "mrr_at_k",
        "hit": "hit_rate_at_k",
    }
    exp = EXPECTED[level]
    for metric, key in keys.items():
        expected = sum(exp[q][metric] for q in exp) / len(exp)
        assert math.isclose(float(summary[key]), expected, rel_tol=1e-9, abs_tol=1e-12), key
    assert summary["queries"] == len(QRELS)
    # g3 has only grade-0 judgments; at level 2, g6 (grade 1 only) joins it.
    assert summary["queries_without_relevant"] == (1 if level == 1 else 2)
