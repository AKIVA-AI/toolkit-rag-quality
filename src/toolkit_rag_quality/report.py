from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class RAGReport:
    summary: dict[str, Any]
    per_query: list[dict[str, Any]]
    schema_version: int = 1

    def to_dict(self) -> dict[str, Any]:
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


def write_report_json(report: RAGReport, path: Path) -> None:
    path.write_text(json.dumps(report.to_dict(), indent=2, sort_keys=True), encoding="utf-8")
