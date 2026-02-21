from __future__ import annotations

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

