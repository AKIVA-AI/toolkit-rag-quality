"""The compare gate must fail on any headline-metric regression, not only recall."""

from __future__ import annotations

from toolkit_rag_quality.compare import CompareBudget, compare_reports
from toolkit_rag_quality.report import RAGReport

BASE = {
    "k": 5,
    "queries": 2,
    "hit_rate_at_k": 1.0,
    "recall_at_k": 0.8,
    "precision_at_k": 0.4,
    "mrr_at_k": 0.9,
    "ndcg_at_k": 0.85,
    "map_at_k": 0.7,
}


def _report(summary: dict, ids: list[str] | None = None) -> RAGReport:
    per = [{"id": q} for q in (ids or [])]
    return RAGReport(summary=summary, per_query=per)


def test_precision_ndcg_mrr_collapse_with_recall_held_fails() -> None:
    cand = dict(BASE, precision_at_k=0.1, ndcg_at_k=0.3, mrr_at_k=0.2)
    result = compare_reports(
        baseline=_report(BASE), candidate=_report(cand), budget=CompareBudget()
    )
    assert result["passed"] is False
    assert result["reason"] == "metric_regression"
    assert set(result["failed_metrics"]) == {"precision_at_k", "ndcg_at_k", "mrr_at_k"}
    assert result["metrics"]["recall_at_k"]["passed"] is True


def test_identical_reports_pass() -> None:
    result = compare_reports(
        baseline=_report(BASE), candidate=_report(dict(BASE)), budget=CompareBudget()
    )
    assert result["passed"] is True
    assert result["reason"] == "ok"
    assert result["failed_metrics"] == []


def test_separate_budget_for_non_recall_metrics() -> None:
    cand = dict(BASE, ndcg_at_k=0.85 * 0.95)  # 5% nDCG regression
    loose = compare_reports(
        baseline=_report(BASE),
        candidate=_report(cand),
        budget=CompareBudget(max_recall_regression_pct=2.0, max_regression_pct=10.0),
    )
    strict = compare_reports(
        baseline=_report(BASE),
        candidate=_report(cand),
        budget=CompareBudget(max_recall_regression_pct=2.0),
    )
    assert loose["passed"] is True
    assert strict["passed"] is False


def test_metric_missing_from_candidate_fails() -> None:
    cand = {key: v for key, v in BASE.items() if key != "ndcg_at_k"}
    result = compare_reports(
        baseline=_report(BASE), candidate=_report(cand), budget=CompareBudget()
    )
    assert result["passed"] is False
    assert "ndcg_at_k" in result["failed_metrics"]


def test_different_k_fails() -> None:
    result = compare_reports(
        baseline=_report(BASE), candidate=_report(dict(BASE, k=10)), budget=CompareBudget()
    )
    assert result["passed"] is False
    assert result["reason"] == "k_mismatch"


def test_different_relevance_level_fails() -> None:
    result = compare_reports(
        baseline=_report(dict(BASE, relevance_level=1)),
        candidate=_report(dict(BASE, relevance_level=2)),
        budget=CompareBudget(),
    )
    assert result["passed"] is False
    assert result["reason"] == "relevance_level_mismatch"


def test_different_query_sets_fail() -> None:
    result = compare_reports(
        baseline=_report(BASE, ["q1", "q2"]),
        candidate=_report(dict(BASE), ["q1", "q3"]),
        budget=CompareBudget(),
    )
    assert result["passed"] is False
    assert result["reason"] == "query_set_mismatch"


def test_different_query_counts_fail() -> None:
    result = compare_reports(
        baseline=_report(BASE), candidate=_report(dict(BASE, queries=3)), budget=CompareBudget()
    )
    assert result["passed"] is False
    assert result["reason"] == "query_set_mismatch"
