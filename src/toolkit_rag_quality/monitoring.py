"""Monitoring and health checks for RAG Quality Toolkit"""
from datetime import datetime
from typing import Dict, Any


class HealthCheck:
    @staticmethod
    def check_system() -> Dict[str, Any]:
        try:
            return {"status": "healthy", "timestamp": datetime.utcnow().isoformat()}
        except Exception as e:
            return {"status": "unhealthy", "error": str(e), "timestamp": datetime.utcnow().isoformat()}


class Metrics:
    def __init__(self):
        self.metrics = {"evaluations_run": 0, "avg_quality_score": 0.0}
    
    def record_evaluation(self, quality_score: float):
        self.metrics["evaluations_run"] += 1
        self.metrics["avg_quality_score"] = (
            (self.metrics["avg_quality_score"] * (self.metrics["evaluations_run"] - 1) + quality_score)
            / self.metrics["evaluations_run"]
        )
    
    def get_metrics(self) -> Dict[str, Any]:
        return {**self.metrics, "timestamp": datetime.utcnow().isoformat()}


_metrics = Metrics()


def get_metrics() -> Dict[str, Any]:
    return _metrics.get_metrics()


def get_health_status() -> Dict[str, Any]:
    return {"system": HealthCheck.check_system(), "metrics": get_metrics()}

