from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .envelope import is_envelope
from .io import write_json

#: Summary keys every ``rag.score`` report carries.
SCORE_SUMMARY_KEYS: tuple[str, ...] = (
    "k",
    "queries",
    "hit_rate_at_k",
    "recall_at_k",
    "precision_at_k",
    "mrr_at_k",
    "ndcg_at_k",
    "map_at_k",
)


@dataclass(frozen=True)
class RAGReport:
    summary: dict[str, Any]
    per_query: list[dict[str, Any]]
    schema_version: int = 1

    def to_dict(self) -> dict[str, Any]:
        """The legacy (pre-1.0) report shape."""
        return {
            "schema_version": int(self.schema_version),
            "summary": self.summary,
            "per_query": self.per_query,
        }

    @staticmethod
    def from_dict(obj: dict[str, Any]) -> RAGReport:
        return RAGReport(
            summary=dict(obj.get("summary") or {}),
            per_query=list(obj.get("per_query") or []),
            schema_version=int(obj.get("schema_version", 1)),
        )


def load_report(obj: Any) -> RAGReport:
    """Load a score report from an envelope (``rag.score``) or the legacy shape.

    Raises:
        ValueError: if ``obj`` is an envelope of another kind, an ``error``
            envelope, or not a report at all.
    """
    if is_envelope(obj):
        pred = obj.get("predicate")
        if not isinstance(pred, dict):
            raise ValueError("report envelope has no predicate")
        kind = pred.get("kind")
        if kind != "rag.score":
            raise ValueError(f"expected a rag.score report, got kind {kind!r}")
        if pred.get("verdict") == "error":
            raise ValueError("the report is an error report; it has no scores to compare")
        summary = pred.get("summary")
        details = pred.get("details")
        per_query = details.get("per_query") if isinstance(details, dict) else None
        if not isinstance(summary, dict) or not isinstance(per_query, list):
            raise ValueError("rag.score envelope needs predicate.summary and details.per_query")
        return RAGReport(summary=dict(summary), per_query=list(per_query))
    if isinstance(obj, dict) and isinstance(obj.get("summary"), dict):
        return RAGReport.from_dict(obj)
    raise ValueError("not a report: expected an envelope or an object with a 'summary'")


def validate_score_report(report: RAGReport) -> list[str]:
    """Check that a score report carries every headline metric and per-query rows."""
    errors = [f"summary.{key}: missing" for key in SCORE_SUMMARY_KEYS if key not in report.summary]
    for i, row in enumerate(report.per_query):
        if not isinstance(row, dict) or "id" not in row:
            errors.append(f"per_query[{i}]: must be an object with an 'id'")
    return errors


def write_report_json(report: RAGReport, path: Path) -> None:
    """Write a report in the legacy shape, with the same path validation as
    every other output."""
    write_json(path, report.to_dict())
