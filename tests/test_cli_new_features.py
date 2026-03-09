"""Tests for new CLI features: --format, --log-format, health subcommand."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from toolkit_rag_quality.cli import (
    EXIT_SUCCESS,
    _JsonLogFormatter,
    _format_output,
    _format_table,
    build_parser,
    main,
)


def test_cli_health_subcommand(capsys: pytest.CaptureFixture[str]) -> None:
    """health subcommand should return healthy status."""
    exit_code = main(["health"])
    assert exit_code == EXIT_SUCCESS
    output = json.loads(capsys.readouterr().out)
    assert output["system"]["status"] == "healthy"


def test_cli_health_table_format(capsys: pytest.CaptureFixture[str]) -> None:
    """health --format table should produce non-JSON output."""
    exit_code = main(["health", "--format", "table"])
    assert exit_code == EXIT_SUCCESS
    output = capsys.readouterr().out
    assert "system:" in output


def test_cli_score_table_format(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    """score --format table should produce table output."""
    queries = tmp_path / "queries.jsonl"
    retrieved = tmp_path / "retrieved.jsonl"
    queries.write_text('{"id": "q1", "relevant_ids": ["d1"]}\n', encoding="utf-8")
    retrieved.write_text('{"id": "q1", "retrieved_ids": ["d1"]}\n', encoding="utf-8")

    exit_code = main([
        "score",
        "--queries", str(queries),
        "--retrieved", str(retrieved),
        "--format", "table",
    ])
    assert exit_code == EXIT_SUCCESS
    output = capsys.readouterr().out
    # Table output should not be valid JSON
    with pytest.raises(json.JSONDecodeError):
        json.loads(output)


def test_cli_score_json_format(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    """score --format json should produce valid JSON (default)."""
    queries = tmp_path / "queries.jsonl"
    retrieved = tmp_path / "retrieved.jsonl"
    queries.write_text('{"id": "q1", "relevant_ids": ["d1"]}\n', encoding="utf-8")
    retrieved.write_text('{"id": "q1", "retrieved_ids": ["d1"]}\n', encoding="utf-8")

    exit_code = main([
        "score",
        "--queries", str(queries),
        "--retrieved", str(retrieved),
        "--format", "json",
    ])
    assert exit_code == EXIT_SUCCESS
    output = json.loads(capsys.readouterr().out)
    assert "summary" in output


def test_cli_log_format_json_flag(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    """--log-format json should be accepted without error."""
    queries = tmp_path / "queries.jsonl"
    retrieved = tmp_path / "retrieved.jsonl"
    queries.write_text('{"id": "q1", "relevant_ids": ["d1"]}\n', encoding="utf-8")
    retrieved.write_text('{"id": "q1", "retrieved_ids": ["d1"]}\n', encoding="utf-8")

    exit_code = main([
        "--log-format", "json",
        "score",
        "--queries", str(queries),
        "--retrieved", str(retrieved),
    ])
    assert exit_code == EXIT_SUCCESS


def test_format_output_json() -> None:
    """_format_output with json should produce valid JSON."""
    data = {"key": "value"}
    result = _format_output(data, "json")
    assert json.loads(result) == data


def test_format_output_table() -> None:
    """_format_output with table should produce text."""
    data = {"alpha": 1, "beta": 2}
    result = _format_output(data, "table")
    assert "alpha" in result
    assert "beta" in result


def test_format_table_nested_dict() -> None:
    """_format_table should handle nested dicts."""
    data = {"system": {"status": "healthy"}, "version": "1.0"}
    result = _format_table(data)
    assert "system:" in result
    assert "status" in result


def test_format_table_with_list() -> None:
    """_format_table should show list summary."""
    data = {"items": [1, 2, 3]}
    result = _format_table(data)
    assert "3 items" in result


def test_json_log_formatter() -> None:
    """_JsonLogFormatter should produce valid JSON log lines."""
    import logging

    formatter = _JsonLogFormatter(datefmt="%Y-%m-%dT%H:%M:%S")
    record = logging.LogRecord(
        name="test", level=logging.INFO, pathname="", lineno=0,
        msg="test message", args=(), exc_info=None,
    )
    output = formatter.format(record)
    parsed = json.loads(output)
    assert parsed["message"] == "test message"
    assert parsed["level"] == "INFO"


def test_build_parser_has_format_on_all_subcommands() -> None:
    """All data-producing subcommands should accept --format."""
    parser = build_parser()
    for cmd in ["score", "overlap", "compare", "validate-report", "health"]:
        # Should not raise
        if cmd == "score":
            args = parser.parse_args([
                cmd, "--queries", "q.jsonl", "--retrieved", "r.jsonl", "--format", "table",
            ])
        elif cmd == "overlap":
            args = parser.parse_args([cmd, "--a", "a.jsonl", "--b", "b.jsonl", "--format", "table"])
        elif cmd == "compare":
            args = parser.parse_args([
                cmd, "--baseline", "b.json", "--candidate", "c.json", "--format", "table",
            ])
        elif cmd == "validate-report":
            args = parser.parse_args([cmd, "--report", "r.json", "--format", "table"])
        elif cmd == "health":
            args = parser.parse_args([cmd, "--format", "table"])
        assert args.format == "table"
