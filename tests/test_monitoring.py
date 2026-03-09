"""Tests for monitoring module."""
from __future__ import annotations

import json

from toolkit_rag_quality.monitoring import (
    HealthCheck,
    Metrics,
    format_health_output,
    get_health_status,
)


def test_health_check_returns_healthy() -> None:
    """HealthCheck should return healthy status."""
    result = HealthCheck.check_system()
    assert result["status"] == "healthy"
    assert "timestamp" in result


def test_metrics_initial_state() -> None:
    """New Metrics instance should have zero evaluations."""
    m = Metrics()
    metrics = m.get_metrics()
    assert metrics["evaluations_run"] == 0
    assert metrics["avg_quality_score"] == 0.0
    assert "timestamp" in metrics


def test_metrics_record_single_evaluation() -> None:
    """Recording one evaluation should update count and average."""
    m = Metrics()
    m.record_evaluation(0.85)
    metrics = m.get_metrics()
    assert metrics["evaluations_run"] == 1
    assert abs(metrics["avg_quality_score"] - 0.85) < 1e-9


def test_metrics_record_multiple_evaluations() -> None:
    """Running average should be correct after multiple recordings."""
    m = Metrics()
    m.record_evaluation(0.80)
    m.record_evaluation(0.90)
    m.record_evaluation(0.70)
    metrics = m.get_metrics()
    assert metrics["evaluations_run"] == 3
    expected_avg = (0.80 + 0.90 + 0.70) / 3
    assert abs(metrics["avg_quality_score"] - expected_avg) < 1e-9


def test_get_health_status_without_metrics() -> None:
    """get_health_status without metrics should return system health only."""
    status = get_health_status()
    assert "system" in status
    assert status["system"]["status"] == "healthy"
    assert "metrics" not in status


def test_get_health_status_with_metrics() -> None:
    """get_health_status with metrics should include both."""
    m = Metrics()
    m.record_evaluation(0.75)
    status = get_health_status(metrics=m)
    assert "system" in status
    assert "metrics" in status
    assert status["metrics"]["evaluations_run"] == 1


def test_format_health_output_valid_json() -> None:
    """format_health_output should produce valid JSON."""
    status = get_health_status()
    output = format_health_output(status)
    parsed = json.loads(output)
    assert "system" in parsed


def test_format_health_output_custom_indent() -> None:
    """format_health_output should respect indent parameter."""
    status = get_health_status()
    output = format_health_output(status, indent=4)
    # 4-space indent should be present
    assert "    " in output
