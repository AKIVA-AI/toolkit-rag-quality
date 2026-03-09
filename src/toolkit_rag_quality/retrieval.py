from __future__ import annotations

import math
from typing import Any

from .report import RAGReport


def _as_str_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [str(x) for x in value]
    return [str(value)]


def _mrr(relevant: set[str], retrieved: list[str]) -> float:
    for i, doc_id in enumerate(retrieved, start=1):
        if doc_id in relevant:
            return 1.0 / i
    return 0.0


def _dcg(relevant: set[str], retrieved: list[str]) -> float:
    """Compute Discounted Cumulative Gain for a single query."""
    total = 0.0
    for i, doc_id in enumerate(retrieved):
        if doc_id in relevant:
            total += 1.0 / math.log2(i + 2)  # i+2 because i is 0-based, DCG uses 1-based rank
    return total


def _ndcg(relevant: set[str], retrieved: list[str]) -> float:
    """Compute Normalized Discounted Cumulative Gain for a single query.

    Returns 0.0 when no relevant documents exist.
    """
    if not relevant:
        return 0.0
    dcg = _dcg(relevant, retrieved)
    # Ideal DCG: all relevant docs at top positions
    ideal_k = min(len(relevant), len(retrieved))
    idcg = sum(1.0 / math.log2(i + 2) for i in range(ideal_k))
    if idcg <= 0:
        return 0.0
    return dcg / idcg


def _average_precision(relevant: set[str], retrieved: list[str]) -> float:
    """Compute Average Precision for a single query.

    Returns 0.0 when no relevant documents exist.
    """
    if not relevant:
        return 0.0
    hits = 0
    sum_precisions = 0.0
    for i, doc_id in enumerate(retrieved, start=1):
        if doc_id in relevant:
            hits += 1
            sum_precisions += hits / i
    return sum_precisions / len(relevant)


def score_retrieval(
    *, queries: list[dict[str, Any]], retrieved: list[dict[str, Any]], k: int = 5
) -> RAGReport:
    retrieved_map: dict[str, list[str]] = {}
    for row in retrieved:
        if "id" not in row:
            continue
        retrieved_map[str(row["id"])] = _as_str_list(row.get("retrieved_ids"))

    per: list[dict[str, Any]] = []
    totals = {
        "queries": 0,
        "hits": 0,
        "recall_sum": 0.0,
        "precision_sum": 0.0,
        "mrr_sum": 0.0,
        "ndcg_sum": 0.0,
        "ap_sum": 0.0,
    }

    for q in queries:
        if "id" not in q:
            continue
        qid = str(q["id"])
        rel = set(_as_str_list(q.get("relevant_ids")))
        got = retrieved_map.get(qid, [])[:k]
        hit_count = len(rel.intersection(got))

        recall = (hit_count / len(rel)) if rel else 0.0
        precision = (hit_count / len(got)) if got else 0.0
        mrr = _mrr(rel, got)
        ndcg = _ndcg(rel, got)
        ap = _average_precision(rel, got)
        hit = 1 if hit_count > 0 else 0

        per.append(
            {
                "id": qid,
                "relevant_count": len(rel),
                "retrieved_count": len(got),
                "hit_count": hit_count,
                "hit": bool(hit),
                "recall": recall,
                "precision": precision,
                "mrr": mrr,
                "ndcg": ndcg,
                "ap": ap,
            }
        )

        totals["queries"] += 1
        totals["hits"] += hit
        totals["recall_sum"] += recall
        totals["precision_sum"] += precision
        totals["mrr_sum"] += mrr
        totals["ndcg_sum"] += ndcg
        totals["ap_sum"] += ap

    n = totals["queries"] or 1
    summary = {
        "k": k,
        "queries": totals["queries"],
        "hit_rate_at_k": totals["hits"] / n,
        "recall_at_k": totals["recall_sum"] / n,
        "precision_at_k": totals["precision_sum"] / n,
        "mrr_at_k": totals["mrr_sum"] / n,
        "ndcg_at_k": totals["ndcg_sum"] / n,
        "map_at_k": totals["ap_sum"] / n,
    }
    return RAGReport(summary=summary, per_query=per, schema_version=1)
