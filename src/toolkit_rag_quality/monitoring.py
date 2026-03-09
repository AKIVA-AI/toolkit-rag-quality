"""Monitoring and health checks for RAG Quality Toolkit."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any


class HealthCheck:
    """System health check."""

    @staticmethod
    def check_system() -> dict[str, Any]:
        """Return current system health status."""
        try:
            return {
                "status": "healthy",
                "timestamp": datetime.now(tz=timezone.utc).isoformat(),
            }
        except Exception as e:
            return {
                "status": "unhealthy",
                "error": str(e),
                "timestamp": datetime.now(tz=timezone.utc).isoformat(),
            }


class Metrics:
    """Track evaluation metrics with running averages."""

    def __init__(self) -> None:
        self.metrics: dict[str, Any] = {
            "evaluations_run": 0,
            "avg_quality_score": 0.0,
        }

    def record_evaluation(self, quality_score: float) -> None:
        """Record a quality score and update running average."""
        self.metrics["evaluations_run"] += 1
        n = self.metrics["evaluations_run"]
        prev_avg = self.metrics["avg_quality_score"]
        self.metrics["avg_quality_score"] = (prev_avg * (n - 1) + quality_score) / n

    def get_metrics(self) -> dict[str, Any]:
        """Return current metrics with timestamp."""
        return {
            **self.metrics,
            "timestamp": datetime.now(tz=timezone.utc).isoformat(),
        }


def get_health_status(metrics: Metrics | None = None) -> dict[str, Any]:
    """Return combined health and metrics status.

    Args:
        metrics: Optional Metrics instance. If None, returns empty metrics.

    Returns:
        Dict with system health and metrics data.
    """
    result: dict[str, Any] = {"system": HealthCheck.check_system()}
    if metrics is not None:
        result["metrics"] = metrics.get_metrics()
    return result


def format_health_output(status: dict[str, Any], *, indent: int = 2) -> str:
    """Format health status as JSON string."""
    return json.dumps(status, indent=indent, sort_keys=True)
