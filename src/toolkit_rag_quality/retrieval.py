from __future__ import annotations

import logging
import math
from typing import Any

from .formats import Qrels, Run, qrels_from_rows, run_from_rows
from .report import RAGReport

logger = logging.getLogger(__name__)


def _dedupe(ids: list[str]) -> list[str]:
    """Remove repeated document ids, keeping the first (highest-ranked) one.

    A document can only be retrieved once; counting a repeat as a second hit
    would push nDCG and AP above 1.0.
    """
    seen: set[str] = set()
    out: list[str] = []
    for doc_id in ids:
        if doc_id not in seen:
            seen.add(doc_id)
            out.append(doc_id)
    return out


def _dcg(gains: list[float]) -> float:
    """DCG with linear gain and discount ``1/log2(rank + 1)`` (trec_eval ``ndcg_cut``)."""
    return sum(g / math.log2(i + 2) for i, g in enumerate(gains))


def query_metrics(
    grades: dict[str, int], ranked: list[str], k: int, relevance_level: int = 1
) -> dict[str, Any]:
    """Metrics at cutoff ``k`` for one query, with trec_eval semantics.

    * A document is relevant when its grade is ``>= relevance_level``. Hit
      rate, recall, precision, MRR and AP use this binary view.
    * nDCG uses the grade itself as the gain for every positive grade,
      whatever the relevance level; zero and negative grades give no gain.
      The ideal DCG sorts all positive grades from the qrels, truncated at k.
    * ``ranked`` is de-duplicated (first occurrence wins) before the cutoff.
    * With no relevant documents, recall, precision, MRR, AP and hit are 0.
    """
    unique = _dedupe(ranked)
    got = unique[:k]
    relevant = {d for d, g in grades.items() if g >= relevance_level}
    flags = [d in relevant for d in got]
    hit_count = sum(flags)

    first = next((i for i, f in enumerate(flags, start=1) if f), 0)
    ap_sum = 0.0
    seen = 0
    for i, f in enumerate(flags, start=1):
        if f:
            seen += 1
            ap_sum += seen / i
    n_rel = len(relevant)

    dcg = _dcg([float(max(grades.get(d, 0), 0)) for d in got])
    ideal = sorted((g for g in grades.values() if g > 0), reverse=True)[:k]
    idcg = _dcg([float(g) for g in ideal])

    return {
        "relevant_count": n_rel,
        "judged_count": len(grades),
        "retrieved_count": len(got),
        "hit_count": hit_count,
        "duplicates_removed": len(ranked) - len(unique),
        "hit": hit_count > 0,
        "recall": hit_count / n_rel if n_rel else 0.0,
        "precision": hit_count / k,
        "mrr": 1.0 / first if first else 0.0,
        "ndcg": dcg / idcg if idcg > 0 else 0.0,
        "ap": ap_sum / n_rel if n_rel else 0.0,
    }


_METRIC_SUMMARY = (
    ("hit", "hit_rate_at_k"),
    ("recall", "recall_at_k"),
    ("precision", "precision_at_k"),
    ("mrr", "mrr_at_k"),
    ("ndcg", "ndcg_at_k"),
    ("ap", "map_at_k"),
)


def score_run(
    *,
    qrels: Qrels,
    run: Run,
    k: int = 5,
    relevance_level: int = 1,
    skipped_query_rows: int = 0,
    skipped_retrieved_rows: int = 0,
) -> RAGReport:
    """Score a run against (optionally graded) qrels at cutoff ``k``.

    Semantics follow trec_eval (``P_k``, ``recall_k``, ``ndcg_cut_k``,
    ``map_cut_k``, ``success_k``, and ``recip_rank`` over the top k):

    * A query is *judged* when it has at least one judgment (any grade,
      including 0). Unjudged queries are counted in ``unjudged_queries``,
      logged, and excluded from the averages.
    * A judged query with no relevant document (every grade below
      ``relevance_level``) is scored and averaged in, as trec_eval does; it
      is counted in ``queries_without_relevant``.
    * A judged query missing from the run scores zero on every metric and is
      counted in ``queries_without_results`` (trec_eval ``-c``).
    * Run entries for queries that are not in the qrels are ignored and
      counted in ``unscored_run_queries``.

    Raises:
        ValueError: if ``k`` or ``relevance_level`` is not a positive integer,
            or if no query is judged.
    """
    if isinstance(k, bool) or not isinstance(k, int) or k < 1:
        raise ValueError(f"k must be a positive integer, got {k!r}")
    if (
        isinstance(relevance_level, bool)
        or not isinstance(relevance_level, int)
        or relevance_level < 1
    ):
        raise ValueError(f"relevance_level must be a positive integer, got {relevance_level!r}")

    per: list[dict[str, Any]] = []
    unjudged: list[str] = []
    without_results = 0
    without_relevant = 0
    for qid, grades in qrels.items():
        if not grades:
            unjudged.append(qid)
            continue
        if qid not in run:
            without_results += 1
        row = query_metrics(grades, run.get(qid, []), k, relevance_level)
        if row["relevant_count"] == 0:
            without_relevant += 1
        per.append({"id": qid, **row})

    unscored = sum(1 for qid in run if qid not in qrels)
    if unjudged:
        logger.warning(
            "Excluded %d query(ies) with no relevance judgments from scoring: %s",
            len(unjudged),
            ", ".join(unjudged[:10]) + (" ..." if len(unjudged) > 10 else ""),
        )
    if without_results:
        logger.warning("%d judged query(ies) have no retrieved row and score zero", without_results)
    if without_relevant:
        logger.warning(
            "%d judged query(ies) have no document at relevance level >= %d",
            without_relevant,
            relevance_level,
        )
    if unscored:
        logger.warning("Ignored %d run query(ies) that are not in the judgments", unscored)

    n = len(per)
    if n == 0:
        raise ValueError(
            "no judged queries to score: every query row is missing an 'id' "
            "or has no relevance judgments"
        )
    summary: dict[str, Any] = {
        "k": k,
        "relevance_level": relevance_level,
        "queries": n,
        "unjudged_queries": len(unjudged),
        "queries_without_results": without_results,
        "queries_without_relevant": without_relevant,
        "unscored_run_queries": unscored,
        "skipped_query_rows": skipped_query_rows,
        "skipped_retrieved_rows": skipped_retrieved_rows,
    }
    for metric, key in _METRIC_SUMMARY:
        summary[key] = sum(float(row[metric]) for row in per) / n
    return RAGReport(summary=summary, per_query=per, schema_version=1)


def score_retrieval(
    *,
    queries: list[dict[str, Any]],
    retrieved: list[dict[str, Any]],
    k: int = 5,
    relevance_level: int = 1,
) -> RAGReport:
    """Score JSONL-style rows: queries with ``relevant_ids`` (grade 1) or a
    ``relevance`` map of graded judgments, and ranked ``retrieved_ids``.

    Rows without an ``id`` are counted (``skipped_query_rows``,
    ``skipped_retrieved_rows``) and logged. See :func:`score_run` for the
    metric semantics.

    Raises:
        ValueError: if ``k`` is not a positive integer, a query id repeats,
            a grade is not an integer, or no query is judged.
    """
    if isinstance(k, bool) or not isinstance(k, int) or k < 1:
        raise ValueError(f"k must be a positive integer, got {k!r}")
    qrels, skipped_q = qrels_from_rows(queries)
    run, skipped_r = run_from_rows(retrieved)
    return score_run(
        qrels=qrels,
        run=run,
        k=k,
        relevance_level=relevance_level,
        skipped_query_rows=skipped_q,
        skipped_retrieved_rows=skipped_r,
    )
