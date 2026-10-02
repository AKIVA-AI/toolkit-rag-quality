"""Regression gate: compare a candidate retrieval report against a baseline.

For every gated metric the gate checks the relative drop of the mean against
a budget. When both reports carry per-query rows it also:

* diffs every query (which queries got worse, better, or stayed the same);
* runs a paired significance test on each metric's per-query scores
  (randomization test by default, or the paired t-test);
* with ``alpha`` set, fails a metric only when its drop is over budget *and*
  statistically significant at ``alpha``, so noise on a small query set does
  not break the build.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any

from .report import RAGReport
from .stats import PairedTest, paired_permutation_test, paired_t_test

#: Summary metrics the gate checks, when present in the baseline report.
GATED_METRICS: tuple[str, ...] = (
    "recall_at_k",
    "precision_at_k",
    "ndcg_at_k",
    "mrr_at_k",
    "map_at_k",
    "hit_rate_at_k",
)

#: Per-query field behind each summary metric.
PER_QUERY_FIELD: dict[str, str] = {
    "recall_at_k": "recall",
    "precision_at_k": "precision",
    "ndcg_at_k": "ndcg",
    "mrr_at_k": "mrr",
    "map_at_k": "ap",
    "hit_rate_at_k": "hit",
}

_ALIASES: dict[str, str] = {
    **{v: k for k, v in PER_QUERY_FIELD.items()},
    "map": "map_at_k",
    "hit_rate": "hit_rate_at_k",
    **{k: k for k in GATED_METRICS},
}

SIGNIFICANCE_TESTS: tuple[str, ...] = ("permutation", "t-test")


def metric_name(name: str) -> str:
    """Resolve a metric name or alias (``ndcg``, ``ndcg_at_k``, ``ap``, ``map``...)."""
    key = name.strip().lower()
    if key not in _ALIASES:
        raise ValueError(f"unknown metric {name!r}; expected one of {', '.join(GATED_METRICS)}")
    return _ALIASES[key]


@dataclass(frozen=True)
class CompareBudget:
    """Allowed relative regression, in percent of the baseline value.

    ``max_recall_regression_pct`` applies to ``recall_at_k``.
    ``max_regression_pct`` applies to every other gated metric; when it is
    ``None`` the recall budget is used for all metrics. ``per_metric``
    overrides both for named metrics; a value of ``None`` there means the
    metric is reported but not gated.
    """

    max_recall_regression_pct: float = 2.0
    max_regression_pct: float | None = None
    per_metric: Mapping[str, float | None] = field(default_factory=dict)

    def for_metric(self, metric: str) -> float | None:
        if metric in self.per_metric:
            return self.per_metric[metric]
        if metric == "recall_at_k" or self.max_regression_pct is None:
            return self.max_recall_regression_pct
        return self.max_regression_pct


def _query_ids(report: RAGReport) -> set[str]:
    return {str(row.get("id")) for row in report.per_query if isinstance(row, dict)}


def _rows_by_id(report: RAGReport) -> dict[str, dict[str, Any]]:
    return {str(r.get("id")): r for r in report.per_query if isinstance(r, dict)}


def _value(row: dict[str, Any], field_name: str) -> float:
    value = row.get(field_name)
    if isinstance(value, bool):
        return 1.0 if value else 0.0
    if isinstance(value, (int, float)):
        return float(value)
    raise ValueError(f"query {row.get('id')!r} has no numeric {field_name!r}")


def per_query_diff(
    baseline: RAGReport, candidate: RAGReport, metrics: tuple[str, ...] = GATED_METRICS
) -> list[dict[str, Any]]:
    """One row per query (baseline order): each metric's baseline, candidate and delta."""
    cand_rows = _rows_by_id(candidate)
    rows: list[dict[str, Any]] = []
    for qid, base_row in _rows_by_id(baseline).items():
        cand_row = cand_rows[qid]
        row: dict[str, Any] = {"id": qid}
        for metric in metrics:
            f = PER_QUERY_FIELD[metric]
            if f not in base_row or f not in cand_row:
                continue
            b, c = _value(base_row, f), _value(cand_row, f)
            row[f] = {"baseline": b, "candidate": c, "delta": c - b}
        rows.append(row)
    return rows


def _significance(
    diff: list[dict[str, Any]], metric: str, test: str, n_resamples: int, seed: int
) -> tuple[PairedTest, PairedTest] | None:
    f = PER_QUERY_FIELD[metric]
    pairs = [(r[f]["baseline"], r[f]["candidate"]) for r in diff if f in r]
    if len(pairs) != len(diff) or not pairs:
        return None
    base = [p[0] for p in pairs]
    cand = [p[1] for p in pairs]
    t = paired_t_test(base, cand)
    perm = paired_permutation_test(base, cand, n_resamples=n_resamples, seed=seed)
    return (perm, t) if test == "permutation" else (t, perm)


def compare_reports(
    *,
    baseline: RAGReport,
    candidate: RAGReport,
    budget: CompareBudget,
    alpha: float | None = None,
    test: str = "permutation",
    n_resamples: int = 10000,
    seed: int = 0,
    primary_metric: str = "ndcg_at_k",
    top_n: int = 10,
) -> dict[str, Any]:
    """Fail when a gated metric in the baseline regresses beyond its budget.

    The gate also fails when the two reports were computed at a different k or
    relevance level, or over different query sets, because their numbers are
    then not comparable. A metric that is in the baseline but missing from the
    candidate fails.

    With ``alpha`` set, a metric over budget fails only when the paired
    ``test`` finds the per-query change significant (p < alpha). If the
    reports have no per-query rows the significance test cannot run and the
    call raises ``ValueError``. With fewer than two queries there is no
    p-value, and a metric over budget fails.

    The result's ``per_query_diff`` lists every query's baseline, candidate
    and delta for each metric.
    """
    if test not in SIGNIFICANCE_TESTS:
        raise ValueError(f"test must be one of {', '.join(SIGNIFICANCE_TESTS)}, got {test!r}")
    if alpha is not None and not 0.0 < alpha < 1.0:
        raise ValueError(f"alpha must be between 0 and 1, got {alpha!r}")
    primary_metric = metric_name(primary_metric)

    base_sum = baseline.summary
    cand_sum = candidate.summary
    base_recall = float(base_sum.get("recall_at_k", 0.0))
    cand_recall = float(cand_sum.get("recall_at_k", 0.0))

    result: dict[str, Any] = {
        "passed": False,
        "reason": "",
        "failed_metrics": [],
        "metrics": {},
        "baseline_recall_at_k": base_recall,
        "candidate_recall_at_k": cand_recall,
        "recall_regression_pct": None,
        "max_recall_regression_pct": budget.max_recall_regression_pct,
        "max_regression_pct": budget.for_metric("precision_at_k"),
        "alpha": alpha,
        "test": test,
        "queries_compared": 0,
        "per_query": {},
        "most_regressed": [],
        "per_query_diff": [],
    }

    if "k" in base_sum and "k" in cand_sum and base_sum["k"] != cand_sum["k"]:
        result["reason"] = "k_mismatch"
        return result
    level_differs = (
        "relevance_level" in base_sum
        and "relevance_level" in cand_sum
        and base_sum["relevance_level"] != cand_sum["relevance_level"]
    )
    if level_differs:
        result["reason"] = "relevance_level_mismatch"
        return result
    count_differs = (
        "queries" in base_sum
        and "queries" in cand_sum
        and base_sum["queries"] != cand_sum["queries"]
    )
    both_have_rows = bool(baseline.per_query and candidate.per_query)
    ids_differ = both_have_rows and (_query_ids(baseline) != _query_ids(candidate))
    if count_differs or ids_differ:
        result["reason"] = "query_set_mismatch"
        return result

    if base_recall <= 0 and cand_recall <= 0:
        result["reason"] = "no_baseline_recall_and_candidate_zero"
        return result

    diff = per_query_diff(baseline, candidate) if both_have_rows else []
    if alpha is not None and not diff:
        raise ValueError(
            "a significance gate (alpha) needs per-query rows in both reports; "
            "re-run `score` to produce them"
        )
    result["queries_compared"] = len(diff)

    metrics: dict[str, dict[str, Any]] = {}
    failed: list[str] = []
    for name in GATED_METRICS:
        if name not in base_sum:
            continue
        base = float(base_sum[name])
        allowed = budget.for_metric(name)
        if name not in cand_sum:
            metrics[name] = {"baseline": base, "candidate": None, "passed": False}
            failed.append(name)
            continue
        cand = float(cand_sum[name])
        pct = ((base - cand) / base) * 100.0 if base > 0 else None
        over_budget = allowed is not None and pct is not None and pct > allowed
        entry: dict[str, Any] = {
            "baseline": base,
            "candidate": cand,
            "regression_pct": pct,
            "max_regression_pct": allowed,
            "gated": allowed is not None,
            "over_budget": over_budget,
            "p_value": None,
            "significant": None,
        }
        sig = _significance(diff, name, test, n_resamples, seed) if diff else None
        if sig is not None:
            chosen, other = sig
            entry["p_value"] = chosen.p_value
            entry["p_value_" + other.test.replace("-", "_")] = other.p_value
            entry["mean_delta"] = chosen.mean_diff
            if alpha is not None:
                entry["significant"] = chosen.p_value is None or chosen.p_value < alpha
        ok = not over_budget
        if over_budget and alpha is not None and entry["significant"] is False:
            ok = True  # over budget, but not distinguishable from noise at alpha
        entry["passed"] = ok
        metrics[name] = entry
        if not ok:
            failed.append(name)

    if diff:
        for metric in GATED_METRICS:
            f = PER_QUERY_FIELD[metric]
            deltas = [r[f]["delta"] for r in diff if f in r]
            if deltas:
                result["per_query"][metric] = {
                    "worse": sum(1 for d in deltas if d < 0),
                    "better": sum(1 for d in deltas if d > 0),
                    "unchanged": sum(1 for d in deltas if d == 0),
                }
        f = PER_QUERY_FIELD[primary_metric]
        worst = sorted(
            (r for r in diff if f in r and r[f]["delta"] < 0), key=lambda r: r[f]["delta"]
        )
        result["most_regressed"] = [
            {"id": r["id"], "metric": primary_metric, "delta": r[f]["delta"]} for r in worst[:top_n]
        ]
        result["per_query_diff"] = diff

    result["metrics"] = metrics
    result["failed_metrics"] = failed
    if "recall_at_k" in metrics:
        result["recall_regression_pct"] = metrics["recall_at_k"].get("regression_pct")
    result["passed"] = not failed
    if failed:
        result["reason"] = "metric_regression"
    elif base_recall <= 0:
        result["reason"] = "no_baseline_recall"
    else:
        result["reason"] = "ok"
    return result
