from __future__ import annotations

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


def score_retrieval(
    *, queries: list[dict[str, Any]], retrieved: list[dict[str, Any]], k: int = 5
) -> RAGReport:
    retrieved_map: dict[str, list[str]] = {}
    for row in retrieved:
        if "id" not in row:
            continue
        retrieved_map[str(row["id"])] = _as_str_list(row.get("retrieved_ids"))

    per: list[dict[str, Any]] = []
    totals = {"queries": 0, "hits": 0, "recall_sum": 0.0, "precision_sum": 0.0, "mrr_sum": 0.0}

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
            }
        )

        totals["queries"] += 1
        totals["hits"] += hit
        totals["recall_sum"] += recall
        totals["precision_sum"] += precision
        totals["mrr_sum"] += mrr

    n = totals["queries"] or 1
    summary = {
        "k": k,
        "queries": totals["queries"],
        "hit_rate_at_k": totals["hits"] / n,
        "recall_at_k": totals["recall_sum"] / n,
        "precision_at_k": totals["precision_sum"] / n,
        "mrr_at_k": totals["mrr_sum"] / n,
    }
    return RAGReport(summary=summary, per_query=per, schema_version=1)
