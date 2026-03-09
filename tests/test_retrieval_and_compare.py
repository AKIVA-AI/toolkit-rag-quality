from __future__ import annotations

import math

from toolkit_rag_quality.compare import CompareBudget, compare_reports
from toolkit_rag_quality.report import RAGReport
from toolkit_rag_quality.retrieval import score_retrieval


def test_score_retrieval_basic() -> None:
    queries = [{"id": "q1", "relevant_ids": ["d1", "d2"]}, {"id": "q2", "relevant_ids": ["d9"]}]
    retrieved = [{"id": "q1", "retrieved_ids": ["d2", "d3"]}, {"id": "q2", "retrieved_ids": ["d9"]}]
    report = score_retrieval(queries=queries, retrieved=retrieved, k=2)
    assert report.summary["queries"] == 2
    assert 0.0 <= float(report.summary["recall_at_k"]) <= 1.0


def test_compare_reports_budget() -> None:
    baseline = RAGReport(summary={"recall_at_k": 1.0}, per_query=[])
    candidate_ok = RAGReport(summary={"recall_at_k": 0.99}, per_query=[])
    candidate_bad = RAGReport(summary={"recall_at_k": 0.90}, per_query=[])
    budget = CompareBudget(max_recall_regression_pct=2.0)
    ok = compare_reports(baseline=baseline, candidate=candidate_ok, budget=budget)
    bad = compare_reports(baseline=baseline, candidate=candidate_bad, budget=budget)
    assert ok["passed"] is True
    assert bad["passed"] is False


def test_score_retrieval_no_relevant_ids() -> None:
    """Query with no relevant_ids should have recall=0, precision=0."""
    queries = [{"id": "q1", "relevant_ids": []}]
    retrieved = [{"id": "q1", "retrieved_ids": ["d1", "d2"]}]
    report = score_retrieval(queries=queries, retrieved=retrieved, k=5)
    pq = report.per_query[0]
    assert pq["recall"] == 0.0
    assert pq["ndcg"] == 0.0
    assert pq["ap"] == 0.0


def test_score_retrieval_all_hits() -> None:
    """All retrieved docs are relevant."""
    queries = [{"id": "q1", "relevant_ids": ["d1", "d2", "d3"]}]
    retrieved = [{"id": "q1", "retrieved_ids": ["d1", "d2", "d3"]}]
    report = score_retrieval(queries=queries, retrieved=retrieved, k=3)
    pq = report.per_query[0]
    assert pq["recall"] == 1.0
    assert pq["precision"] == 1.0
    assert pq["mrr"] == 1.0
    assert abs(pq["ndcg"] - 1.0) < 1e-9
    assert abs(pq["ap"] - 1.0) < 1e-9


def test_score_retrieval_no_hits() -> None:
    """No retrieved docs are relevant."""
    queries = [{"id": "q1", "relevant_ids": ["d1", "d2"]}]
    retrieved = [{"id": "q1", "retrieved_ids": ["d5", "d6"]}]
    report = score_retrieval(queries=queries, retrieved=retrieved, k=5)
    pq = report.per_query[0]
    assert pq["recall"] == 0.0
    assert pq["precision"] == 0.0
    assert pq["mrr"] == 0.0
    assert pq["ndcg"] == 0.0
    assert pq["ap"] == 0.0


def test_score_retrieval_missing_ids_skipped() -> None:
    """Rows without 'id' field are skipped."""
    queries = [{"relevant_ids": ["d1"]}, {"id": "q1", "relevant_ids": ["d1"]}]
    retrieved = [{"retrieved_ids": ["d1"]}, {"id": "q1", "retrieved_ids": ["d1"]}]
    report = score_retrieval(queries=queries, retrieved=retrieved, k=5)
    assert report.summary["queries"] == 1


def test_score_retrieval_empty_retrieved() -> None:
    """Query with no retrieved results."""
    queries = [{"id": "q1", "relevant_ids": ["d1"]}]
    retrieved = [{"id": "q1", "retrieved_ids": []}]
    report = score_retrieval(queries=queries, retrieved=retrieved, k=5)
    pq = report.per_query[0]
    assert pq["recall"] == 0.0
    assert pq["precision"] == 0.0
    assert pq["hit"] is False


def test_score_retrieval_query_not_in_retrieved() -> None:
    """Query ID not present in retrieved map."""
    queries = [{"id": "q1", "relevant_ids": ["d1"]}]
    retrieved = [{"id": "q2", "retrieved_ids": ["d1"]}]
    report = score_retrieval(queries=queries, retrieved=retrieved, k=5)
    pq = report.per_query[0]
    assert pq["retrieved_count"] == 0
    assert pq["recall"] == 0.0


def test_score_retrieval_ndcg_known_value() -> None:
    """NDCG for a known ranking: relevant at position 2 out of 2 retrieved, 1 relevant total."""
    queries = [{"id": "q1", "relevant_ids": ["d1"]}]
    retrieved = [{"id": "q1", "retrieved_ids": ["d2", "d1"]}]
    report = score_retrieval(queries=queries, retrieved=retrieved, k=2)
    pq = report.per_query[0]
    # Ideal: d1 at position 1 -> IDCG = 1/log2(2) = 1.0
    # Actual: d1 at position 2 -> DCG = 1/log2(3)
    expected_ndcg = (1.0 / math.log2(3)) / (1.0 / math.log2(2))
    assert abs(pq["ndcg"] - expected_ndcg) < 1e-9


def test_score_retrieval_map_known_value() -> None:
    """MAP for a known ranking: 2 relevant, found at positions 1 and 3."""
    queries = [{"id": "q1", "relevant_ids": ["d1", "d3"]}]
    retrieved = [{"id": "q1", "retrieved_ids": ["d1", "d2", "d3"]}]
    report = score_retrieval(queries=queries, retrieved=retrieved, k=3)
    pq = report.per_query[0]
    # AP = (1/1 + 2/3) / 2 = (1.0 + 0.6667) / 2 = 0.8333
    expected_ap = (1.0 / 1 + 2.0 / 3) / 2
    assert abs(pq["ap"] - expected_ap) < 1e-4


def test_score_retrieval_summary_contains_ndcg_and_map() -> None:
    """Summary should include ndcg_at_k and map_at_k fields."""
    queries = [{"id": "q1", "relevant_ids": ["d1"]}]
    retrieved = [{"id": "q1", "retrieved_ids": ["d1"]}]
    report = score_retrieval(queries=queries, retrieved=retrieved, k=5)
    assert "ndcg_at_k" in report.summary
    assert "map_at_k" in report.summary


def test_compare_reports_zero_baseline() -> None:
    """Compare with zero baseline recall."""
    baseline = RAGReport(summary={"recall_at_k": 0.0}, per_query=[])
    candidate = RAGReport(summary={"recall_at_k": 0.5}, per_query=[])
    budget = CompareBudget(max_recall_regression_pct=2.0)
    result = compare_reports(baseline=baseline, candidate=candidate, budget=budget)
    assert result["passed"] is True
    assert result["reason"] == "no_baseline_recall"


def test_compare_reports_both_zero() -> None:
    """Compare when both baseline and candidate have zero recall."""
    baseline = RAGReport(summary={"recall_at_k": 0.0}, per_query=[])
    candidate = RAGReport(summary={"recall_at_k": 0.0}, per_query=[])
    budget = CompareBudget(max_recall_regression_pct=2.0)
    result = compare_reports(baseline=baseline, candidate=candidate, budget=budget)
    assert result["passed"] is False
    assert result["reason"] == "no_baseline_recall_and_candidate_zero"


def test_compare_reports_improvement() -> None:
    """Candidate better than baseline should pass."""
    baseline = RAGReport(summary={"recall_at_k": 0.5}, per_query=[])
    candidate = RAGReport(summary={"recall_at_k": 0.8}, per_query=[])
    budget = CompareBudget(max_recall_regression_pct=2.0)
    result = compare_reports(baseline=baseline, candidate=candidate, budget=budget)
    assert result["passed"] is True
    assert result["recall_regression_pct"] < 0  # negative = improvement
