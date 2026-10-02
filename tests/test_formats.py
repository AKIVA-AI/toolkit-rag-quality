"""TREC / BEIR / JSONL qrels and run import, export and format detection."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from toolkit_rag_quality.cli import main
from toolkit_rag_quality.formats import (
    detect_format,
    load_qrels,
    load_run,
    qrels_from_rows,
    read_beir_qrels,
    read_trec_qrels,
    read_trec_run,
    run_from_rows,
    write_qrels,
    write_run,
)


def _text(path: Path, text: str) -> Path:
    path.write_text(text, encoding="utf-8")
    return path


def test_read_trec_qrels_with_grades(tmp_path: Path) -> None:
    p = _text(tmp_path / "q.qrels", "q1 0 d1 2\nq1 0 d2 0\n\nq2 0 d9 1\n")
    assert read_trec_qrels(p) == {"q1": {"d1": 2, "d2": 0}, "q2": {"d9": 1}}


def test_read_trec_qrels_rejects_bad_lines(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="4 columns"):
        read_trec_qrels(_text(tmp_path / "a", "q1 0 d1\n"))
    with pytest.raises(ValueError, match="integer"):
        read_trec_qrels(_text(tmp_path / "b", "q1 0 d1 high\n"))
    with pytest.raises(ValueError, match="conflicting"):
        read_trec_qrels(_text(tmp_path / "c", "q1 0 d1 1\nq1 0 d1 2\n"))


def test_read_beir_qrels(tmp_path: Path) -> None:
    # Same layout as qrels/test.tsv in a BEIR dataset.
    p = _text(tmp_path / "test.tsv", "query-id\tcorpus-id\tscore\n1\t31715818\t1\n3\t14717500\t2\n")
    assert read_beir_qrels(p) == {"1": {"31715818": 1}, "3": {"14717500": 2}}


def test_read_trec_run_rejects_duplicates_and_bad_scores(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="listed twice"):
        read_trec_run(_text(tmp_path / "a", "q1 Q0 d1 1 2.0 t\nq1 Q0 d1 2 1.0 t\n"))
    with pytest.raises(ValueError, match="not a number"):
        read_trec_run(_text(tmp_path / "b", "q1 Q0 d1 1 high t\n"))
    with pytest.raises(ValueError, match="6 columns"):
        read_trec_run(_text(tmp_path / "c", "q1 Q0 d1 1 2.0\n"))


def test_detect_format(tmp_path: Path) -> None:
    assert detect_format(_text(tmp_path / "a", '\n{"id": "q1"}\n')) == "jsonl"
    assert detect_format(_text(tmp_path / "b", "query-id\tcorpus-id\tscore\n")) == "beir"
    assert detect_format(_text(tmp_path / "c", "q1 0 d1 1\n")) == "trec-qrels"
    assert detect_format(_text(tmp_path / "d", "q1 Q0 d1 1 3.2 bm25\n")) == "trec-run"
    with pytest.raises(ValueError, match="empty"):
        detect_format(_text(tmp_path / "e", "\n"))


def test_load_run_refuses_qrels_and_vice_versa(tmp_path: Path) -> None:
    qrels = _text(tmp_path / "q", "q1 0 d1 1\n")
    run = _text(tmp_path / "r", "q1 Q0 d1 1 3.2 bm25\n")
    with pytest.raises(ValueError, match="not a run"):
        load_run(qrels)
    with pytest.raises(ValueError, match="not qrels"):
        load_qrels(run)


def test_jsonl_rows_graded_and_binary() -> None:
    qrels, skipped = qrels_from_rows(
        [
            {"id": "q1", "relevant_ids": ["d1", "d2"]},
            {"id": "q2", "relevance": {"d3": 2, "d4": 0}},
            {"id": "q3", "relevant_ids": []},
            {"query": "no id"},
        ]
    )
    assert qrels == {"q1": {"d1": 1, "d2": 1}, "q2": {"d3": 2, "d4": 0}, "q3": {}}
    assert skipped == 1


@pytest.mark.parametrize(
    "rows",
    [
        [{"id": "q1", "relevant_ids": ["d1"]}, {"id": "q1", "relevant_ids": ["d2"]}],
        [{"id": "q1", "relevant_ids": ["d1"], "relevance": {"d1": 2}}],
        [{"id": "q1", "relevance": {"d1": 1.5}}],
        [{"id": "q1", "relevance": {"d1": True}}],
        [{"id": "q1", "relevance": ["d1"]}],
    ],
)
def test_jsonl_query_rows_fail_closed(rows: list[dict]) -> None:
    with pytest.raises(ValueError):
        qrels_from_rows(rows)


def test_duplicate_run_rows_fail() -> None:
    with pytest.raises(ValueError, match="duplicate"):
        run_from_rows([{"id": "q1", "retrieved_ids": []}, {"id": "q1", "retrieved_ids": []}])


@pytest.mark.parametrize("fmt", ["jsonl", "trec"])
def test_qrels_round_trip(tmp_path: Path, fmt: str) -> None:
    qrels = {"q1": {"d1": 2, "d2": 0}, "q2": {"d3": 1}}
    out = tmp_path / f"qrels.{fmt}"
    write_qrels(out, qrels, fmt)
    assert load_qrels(out, "auto")[0] == qrels


@pytest.mark.parametrize("fmt", ["jsonl", "trec"])
def test_run_round_trip_preserves_order(tmp_path: Path, fmt: str) -> None:
    # "b" before "a" at equal rank would be reversed by trec_eval's doc-id
    # tie-break if the exported scores tied; they must be strictly decreasing.
    run = {"q1": ["a", "c", "b"], "q2": ["z"]}
    out = tmp_path / f"run.{fmt}"
    write_run(out, run, fmt)
    assert load_run(out, "auto")[0] == run


def test_trec_run_export_layout(tmp_path: Path) -> None:
    out = tmp_path / "run.trec"
    write_run(out, {"q1": ["a", "b"]}, "trec", tag="bm25")
    assert out.read_text(encoding="utf-8") == "q1 Q0 a 1 2 bm25\nq1 Q0 b 2 1 bm25\n"
    with pytest.raises(ValueError, match="tag"):
        write_run(out, {"q1": ["a"]}, "trec", tag="has space")


def test_cli_score_accepts_trec_and_beir_inputs(tmp_path: Path) -> None:
    qrels = _text(tmp_path / "test.tsv", "query-id\tcorpus-id\tscore\nq1\td1\t2\nq1\td2\t1\n")
    run = _text(tmp_path / "run.trec", "q1 Q0 d2 1 9.0 bm25\nq1 Q0 d1 2 8.0 bm25\n")
    out = tmp_path / "report.json"
    rc = main(["score", "--queries", str(qrels), "--retrieved", str(run), "--out", str(out)])
    assert rc == 0
    summary = json.loads(out.read_text(encoding="utf-8"))["predicate"]["summary"]
    # DCG = 1/log2(2) + 2/log2(3); IDCG = 2/log2(2) + 1/log2(3)
    assert summary["ndcg_at_k"] == pytest.approx(
        (1 + 2 / 1.584962500721156) / (2 + 1 / 1.584962500721156)
    )
    assert summary["relevance_level"] == 1


def test_cli_relevance_level_flag(tmp_path: Path) -> None:
    qrels = _text(tmp_path / "q.qrels", "q1 0 d1 2\nq1 0 d2 1\n")
    run = _text(tmp_path / "r.trec", "q1 Q0 d2 1 9.0 t\nq1 Q0 d1 2 8.0 t\n")
    out = tmp_path / "report.json"
    args = ["score", "--queries", str(qrels), "--retrieved", str(run), "--out", str(out)]
    assert main([*args, "--relevance-level", "2", "--k", "1"]) == 0
    summary = json.loads(out.read_text(encoding="utf-8"))["predicate"]["summary"]
    assert summary["precision_at_k"] == 0.0  # d2 (grade 1) is not relevant at level 2
    assert summary["relevance_level"] == 2


def test_cli_convert_trec_run_to_jsonl_and_back(tmp_path: Path) -> None:
    run = _text(tmp_path / "r.trec", "q1 Q0 b 1 1.0 t\nq1 Q0 a 2 1.0 t\nq1 Q0 c 3 5.0 t\n")
    as_jsonl = tmp_path / "run.jsonl"
    assert main(["convert", "run", "--in", str(run), "--out", str(as_jsonl), "--to", "jsonl"]) == 0
    rows = [json.loads(line) for line in as_jsonl.read_text(encoding="utf-8").splitlines()]
    assert rows == [{"id": "q1", "retrieved_ids": ["c", "b", "a"]}]
    back = tmp_path / "back.trec"
    assert main(["convert", "run", "--in", str(as_jsonl), "--out", str(back), "--to", "trec"]) == 0
    assert read_trec_run(back) == {"q1": ["c", "b", "a"]}


def test_cli_convert_beir_qrels_to_trec(tmp_path: Path) -> None:
    qrels = _text(tmp_path / "test.tsv", "query-id\tcorpus-id\tscore\n1\t10\t1\n")
    out = tmp_path / "qrels.trec"
    assert main(["convert", "qrels", "--in", str(qrels), "--out", str(out), "--to", "trec"]) == 0
    assert out.read_text(encoding="utf-8") == "1 0 10 1\n"


def test_cli_convert_bad_input_is_exit_2(tmp_path: Path) -> None:
    bad = _text(tmp_path / "bad.trec", "q1 Q0 d1 1 notanumber t\n")
    out = tmp_path / "x.jsonl"
    assert main(["convert", "run", "--in", str(bad), "--out", str(out), "--to", "jsonl"]) == 2
    assert not out.exists()
