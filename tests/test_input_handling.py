"""Input handling for ``score``: nothing is dropped or averaged in silently."""

from __future__ import annotations

import json
import logging
from pathlib import Path

import pytest

from toolkit_rag_quality.cli import EXIT_CLI_ERROR, main
from toolkit_rag_quality.retrieval import score_retrieval


def test_unjudged_queries_are_excluded_from_averages() -> None:
    queries = [
        {"id": "q1", "relevant_ids": ["d1"]},
        {"id": "q2", "relevant_ids": []},
        {"id": "q3"},
    ]
    retrieved = [
        {"id": "q1", "retrieved_ids": ["d1"]},
        {"id": "q2", "retrieved_ids": ["d1"]},
        {"id": "q3", "retrieved_ids": ["d1"]},
    ]
    report = score_retrieval(queries=queries, retrieved=retrieved, k=1)
    assert report.summary["queries"] == 1
    assert report.summary["unjudged_queries"] == 2
    assert report.summary["recall_at_k"] == 1.0
    assert [row["id"] for row in report.per_query] == ["q1"]


def test_unjudged_queries_log_a_warning(caplog: pytest.LogCaptureFixture) -> None:
    with caplog.at_level(logging.WARNING, logger="toolkit_rag_quality.retrieval"):
        score_retrieval(
            queries=[{"id": "q1", "relevant_ids": ["d1"]}, {"id": "q2", "relevant_ids": []}],
            retrieved=[{"id": "q1", "retrieved_ids": ["d1"]}],
            k=1,
        )
    assert any("no relevance judgments" in r.getMessage() for r in caplog.records)


def test_no_judged_queries_is_an_error() -> None:
    with pytest.raises(ValueError, match="no judged queries"):
        score_retrieval(
            queries=[{"id": "q1", "relevant_ids": []}],
            retrieved=[{"id": "q1", "retrieved_ids": ["d1"]}],
            k=5,
        )


def test_rows_without_id_are_counted_and_warned(caplog: pytest.LogCaptureFixture) -> None:
    with caplog.at_level(logging.WARNING, logger="toolkit_rag_quality.retrieval"):
        report = score_retrieval(
            queries=[{"relevant_ids": ["d1"]}, {"id": "q1", "relevant_ids": ["d1"]}],
            retrieved=[{"retrieved_ids": ["d1"]}, {"id": "q1", "retrieved_ids": ["d1"]}],
            k=5,
        )
    assert report.summary["skipped_query_rows"] == 1
    assert report.summary["skipped_retrieved_rows"] == 1
    messages = " ".join(r.getMessage() for r in caplog.records)
    assert "query row" in messages
    assert "retrieved row" in messages


def test_judged_queries_without_results_score_zero_and_are_counted() -> None:
    report = score_retrieval(
        queries=[{"id": "q1", "relevant_ids": ["d1"]}, {"id": "q2", "relevant_ids": ["d2"]}],
        retrieved=[{"id": "q1", "retrieved_ids": ["d1"]}],
        k=1,
    )
    assert report.summary["queries"] == 2
    assert report.summary["queries_without_results"] == 1
    assert report.summary["recall_at_k"] == 0.5


def _write(path: Path, rows: list[dict]) -> Path:
    path.write_text("\n".join(json.dumps(r) for r in rows) + "\n", encoding="utf-8")
    return path


@pytest.mark.parametrize("k", ["0", "-1", "abc"])
def test_cli_rejects_invalid_k(tmp_path: Path, k: str) -> None:
    q = _write(tmp_path / "q.jsonl", [{"id": "q1", "relevant_ids": ["d1"]}])
    r = _write(tmp_path / "r.jsonl", [{"id": "q1", "retrieved_ids": ["d1", "d2"]}])
    with pytest.raises(SystemExit) as exc:
        main(["score", "--queries", str(q), "--retrieved", str(r), "--k", k])
    assert exc.value.code == 2


def test_cli_score_with_no_judged_queries_fails(tmp_path: Path) -> None:
    q = _write(tmp_path / "q.jsonl", [{"id": "q1", "relevant_ids": []}])
    r = _write(tmp_path / "r.jsonl", [{"id": "q1", "retrieved_ids": ["d1"]}])
    rc = main(["score", "--queries", str(q), "--retrieved", str(r)])
    assert rc == EXIT_CLI_ERROR


@pytest.mark.parametrize("value", ["0", "-5", "many"])
def test_cli_overlap_rejects_invalid_max_records(tmp_path: Path, value: str) -> None:
    a = _write(tmp_path / "a.jsonl", [{"id": "a1", "text": "x"}])
    with pytest.raises(SystemExit) as exc:
        main(["overlap", "--a", str(a), "--b", str(a), "--max-records", value])
    assert exc.value.code == 2


def test_cli_overlap_oversized_input_fails(tmp_path: Path) -> None:
    rows = [{"id": f"a{i}", "text": f"t{i}"} for i in range(5)]
    a = _write(tmp_path / "a.jsonl", rows)
    rc = main(["overlap", "--a", str(a), "--b", str(a), "--max-records", "2"])
    assert rc == EXIT_CLI_ERROR


def test_cli_score_out_creates_parent_directory(tmp_path: Path) -> None:
    q = _write(tmp_path / "q.jsonl", [{"id": "q1", "relevant_ids": ["d1"]}])
    r = _write(tmp_path / "r.jsonl", [{"id": "q1", "retrieved_ids": ["d1"]}])
    out = tmp_path / "nested" / "dir" / "report.json"
    rc = main(["score", "--queries", str(q), "--retrieved", str(r), "--out", str(out)])
    assert rc == 0
    report = json.loads(out.read_text(encoding="utf-8"))
    assert report["predicate"]["summary"]["queries"] == 1


def test_cli_score_out_rejects_path_traversal(tmp_path: Path) -> None:
    q = _write(tmp_path / "q.jsonl", [{"id": "q1", "relevant_ids": ["d1"]}])
    r = _write(tmp_path / "r.jsonl", [{"id": "q1", "retrieved_ids": ["d1"]}])
    out = f"{tmp_path}/a/../report.json"
    rc = main(["score", "--queries", str(q), "--retrieved", str(r), "--out", out])
    assert rc == EXIT_CLI_ERROR
