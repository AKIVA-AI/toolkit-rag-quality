"""Monitoring and health checks for RAG Quality Toolkit"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any


class HealthCheck:
    @staticmethod
    def check_system() -> dict[str, Any]:
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
    def __init__(self) -> None:
        self.metrics: dict[str, Any] = {
            "evaluations_run": 0,
            "avg_quality_score": 0.0,
        }

    def record_evaluation(self, quality_score: float) -> None:
        self.metrics["evaluations_run"] += 1
        n = self.metrics["evaluations_run"]
        prev_avg = self.metrics["avg_quality_score"]
        self.metrics["avg_quality_score"] = (prev_avg * (n - 1) + quality_score) / n

    def get_metrics(self) -> dict[str, Any]:
        return {
            **self.metrics,
            "timestamp": datetime.now(tz=timezone.utc).isoformat(),
        }


_metrics = Metrics()


def get_metrics() -> dict[str, Any]:
    return _metrics.get_metrics()


def get_health_status() -> dict[str, Any]:
    return {"system": HealthCheck.check_system(), "metrics": get_metrics()}
