from __future__ import annotations

from dataclasses import dataclass

from .report import RAGReport


@dataclass(frozen=True)
class CompareBudget:
    max_recall_regression_pct: float = 2.0


def compare_reports(*, baseline: RAGReport, candidate: RAGReport, budget: CompareBudget) -> dict:
    base = float(baseline.summary.get("recall_at_k", 0.0))
    cand = float(candidate.summary.get("recall_at_k", 0.0))

    if base <= 0:
        passed = cand > 0
        return {
            "passed": passed,
            "reason": "no_baseline_recall" if passed else "no_baseline_recall_and_candidate_zero",
            "baseline_recall_at_k": base,
            "candidate_recall_at_k": cand,
            "recall_regression_pct": None,
        }

    regression_pct = ((base - cand) / base) * 100.0
    passed = regression_pct <= budget.max_recall_regression_pct
    return {
        "passed": passed,
        "reason": "ok" if passed else "recall_regression",
        "baseline_recall_at_k": base,
        "candidate_recall_at_k": cand,
        "recall_regression_pct": regression_pct,
        "max_recall_regression_pct": budget.max_recall_regression_pct,
    }
