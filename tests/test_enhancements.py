"""Tests for rag-quality-toolkit enhancements."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from toolkit_rag_quality.cli import (
    EXIT_CLI_ERROR,
    EXIT_SUCCESS,
    main,
)
from toolkit_rag_quality.io import (
    read_json,
    read_jsonl,
    validate_path_for_read,
    validate_path_for_write,
    write_json,
)

# ============================================================================
# Path Validation Tests
# ============================================================================


def test_validate_path_for_read_success(tmp_path: Path) -> None:
    """Test read path validation succeeds with valid file."""
    file_path = tmp_path / "test.json"
    file_path.write_text('{"test": true}', encoding="utf-8")

    result = validate_path_for_read(file_path)
    assert result.is_absolute()
    assert result.is_file()


def test_validate_path_for_read_not_found() -> None:
    """Test read path validation fails with non-existent file."""
    with pytest.raises(FileNotFoundError, match="File not found"):
        validate_path_for_read(Path("/nonexistent/file.json"))


def test_validate_path_for_read_is_directory(tmp_path: Path) -> None:
    """Test read path validation fails when path is directory."""
    with pytest.raises(ValueError, match="not a file"):
        validate_path_for_read(tmp_path)


def test_validate_path_for_write_success(tmp_path: Path) -> None:
    """Test write path validation succeeds."""
    file_path = tmp_path / "output.json"
    result = validate_path_for_write(file_path)
    assert result.is_absolute()


def test_validate_path_for_write_is_directory(tmp_path: Path) -> None:
    """Test write path validation fails when path is directory."""
    with pytest.raises(ValueError, match="is a directory"):
        validate_path_for_write(tmp_path)


# ============================================================================
# JSON IO Tests
# ============================================================================


def test_read_json_success(tmp_path: Path) -> None:
    """Test reading valid JSON file."""
    file_path = tmp_path / "test.json"
    data = {"key": "value", "number": 42}
    file_path.write_text(json.dumps(data), encoding="utf-8")

    result = read_json(file_path)
    assert result == data


def test_read_json_invalid_json(tmp_path: Path) -> None:
    """Test reading invalid JSON raises ValueError."""
    file_path = tmp_path / "invalid.json"
    file_path.write_text("not valid json", encoding="utf-8")

    with pytest.raises(ValueError, match="Invalid JSON"):
        read_json(file_path)


def test_read_json_file_not_found() -> None:
    """Test reading non-existent file raises FileNotFoundError."""
    with pytest.raises(FileNotFoundError):
        read_json(Path("/nonexistent.json"))


def test_write_json_success(tmp_path: Path) -> None:
    """Test writing JSON file."""
    file_path = tmp_path / "output.json"
    data = {"test": True, "value": 123}

    write_json(file_path, data)

    assert file_path.exists()
    assert json.loads(file_path.read_text()) == data


# ============================================================================
# JSONL IO Tests
# ============================================================================


def test_read_jsonl_success(tmp_path: Path) -> None:
    """Test reading JSONL file."""
    file_path = tmp_path / "test.jsonl"
    rows = [{"id": 1}, {"id": 2}, {"id": 3}]
    content = "\n".join(json.dumps(r) for r in rows) + "\n"
    file_path.write_text(content, encoding="utf-8")

    result = list(read_jsonl(file_path))

    assert len(result) == 3
    assert result[0] == {"id": 1}


def test_read_jsonl_skips_empty_lines(tmp_path: Path) -> None:
    """Test JSONL reader skips empty lines."""
    file_path = tmp_path / "test.jsonl"
    content = '{"id": 1}\n\n{"id": 2}\n\n\n{"id": 3}\n'
    file_path.write_text(content, encoding="utf-8")

    result = list(read_jsonl(file_path))

    assert len(result) == 3


def test_read_jsonl_invalid_json(tmp_path: Path) -> None:
    """Test JSONL reader raises on invalid JSON."""
    file_path = tmp_path / "invalid.jsonl"
    content = '{"id": 1}\nnot json\n{"id": 2}\n'
    file_path.write_text(content, encoding="utf-8")

    with pytest.raises(ValueError, match="Invalid JSON at line 2"):
        list(read_jsonl(file_path))


def test_read_jsonl_non_dict_object(tmp_path: Path) -> None:
    """Test JSONL reader raises on non-dict objects."""
    file_path = tmp_path / "invalid.jsonl"
    content = '{"id": 1}\n["array"]\n{"id": 2}\n'
    file_path.write_text(content, encoding="utf-8")

    with pytest.raises(ValueError, match="non-dict"):
        list(read_jsonl(file_path))


# ============================================================================
# CLI Score Command Tests
# ============================================================================


def test_cli_score_queries_not_found(tmp_path: Path) -> None:
    """Test score fails when queries file doesn't exist."""
    retrieved_file = tmp_path / "retrieved.jsonl"
    retrieved_file.write_text('{"id": "q1", "retrieved_ids": []}\n', encoding="utf-8")

    exit_code = main([
        "score",
        "--queries", "/nonexistent.jsonl",
        "--retrieved", str(retrieved_file),
    ])

    assert exit_code == EXIT_CLI_ERROR


def test_cli_score_retrieved_not_found(tmp_path: Path) -> None:
    """Test score fails when retrieved file doesn't exist."""
    queries_file = tmp_path / "queries.jsonl"
    queries_file.write_text('{"id": "q1", "relevant_ids": []}\n', encoding="utf-8")

    exit_code = main([
        "score",
        "--queries", str(queries_file),
        "--retrieved", "/nonexistent.jsonl",
    ])

    assert exit_code == EXIT_CLI_ERROR


# ============================================================================
# CLI Overlap Command Tests
# ============================================================================


def test_cli_overlap_corpus_a_not_found(tmp_path: Path) -> None:
    """Test overlap fails when corpus A doesn't exist."""
    b_file = tmp_path / "corpus_b.jsonl"
    b_file.write_text('{"id": "1", "text": "test"}\n', encoding="utf-8")

    exit_code = main([
        "overlap",
        "--a", "/nonexistent.jsonl",
        "--b", str(b_file),
    ])

    assert exit_code == EXIT_CLI_ERROR


def test_cli_overlap_corpus_b_not_found(tmp_path: Path) -> None:
    """Test overlap fails when corpus B doesn't exist."""
    a_file = tmp_path / "corpus_a.jsonl"
    a_file.write_text('{"id": "1", "text": "test"}\n', encoding="utf-8")

    exit_code = main([
        "overlap",
        "--a", str(a_file),
        "--b", "/nonexistent.jsonl",
    ])

    assert exit_code == EXIT_CLI_ERROR


# ============================================================================
# CLI Compare Command Tests
# ============================================================================


def test_cli_compare_baseline_not_found(tmp_path: Path) -> None:
    """Test compare fails when baseline doesn't exist."""
    candidate = tmp_path / "candidate.json"
    candidate.write_text('{"summary": {}, "per_query": []}', encoding="utf-8")

    exit_code = main([
        "compare",
        "--baseline", "/nonexistent.json",
        "--candidate", str(candidate),
    ])

    assert exit_code == EXIT_CLI_ERROR


def test_cli_compare_candidate_not_found(tmp_path: Path) -> None:
    """Test compare fails when candidate doesn't exist."""
    baseline = tmp_path / "baseline.json"
    baseline.write_text('{"summary": {}, "per_query": []}', encoding="utf-8")

    exit_code = main([
        "compare",
        "--baseline", str(baseline),
        "--candidate", "/nonexistent.json",
    ])

    assert exit_code == EXIT_CLI_ERROR


# ============================================================================
# CLI Validate Command Tests
# ============================================================================


def test_cli_validate_report_not_found() -> None:
    """Test validate fails when report doesn't exist."""
    exit_code = main([
        "validate-report",
        "--report", "/nonexistent.json",
    ])

    assert exit_code == EXIT_CLI_ERROR


def test_cli_validate_report_invalid_json(tmp_path: Path) -> None:
    """Test validate fails with invalid JSON."""
    report = tmp_path / "report.json"
    report.write_text("not valid json", encoding="utf-8")

    exit_code = main([
        "validate-report",
        "--report", str(report),
    ])

    assert exit_code == EXIT_CLI_ERROR


# ============================================================================
# Edge Case Tests
# ============================================================================


def test_cli_verbose_flag(tmp_path: Path, caplog) -> None:
    """Test --verbose flag enables debug logging."""
    queries = tmp_path / "queries.jsonl"
    queries.write_text('{"id": "q1", "relevant_ids": ["d1"]}\n', encoding="utf-8")
    
    retrieved = tmp_path / "retrieved.jsonl"
    retrieved.write_text('{"id": "q1", "retrieved_ids": ["d1"]}\n', encoding="utf-8")

    exit_code = main([
        "--verbose",
        "score",
        "--queries", str(queries),
        "--retrieved", str(retrieved),
    ])

    assert exit_code == EXIT_SUCCESS


def test_write_json_creates_parent_directory(tmp_path: Path) -> None:
    """Test write creates parent directories."""
    file_path = tmp_path / "subdir" / "nested" / "output.json"
    data = {"nested": True}

    write_json(file_path, data)

    assert file_path.exists()
    assert json.loads(file_path.read_text()) == data

