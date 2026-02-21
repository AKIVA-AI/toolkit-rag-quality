from __future__ import annotations

import json
from pathlib import Path

import pytest

from toolkit_rag_quality.cli import build_parser


def test_cli_version_flag_prints(capsys: pytest.CaptureFixture[str]) -> None:
    parser = build_parser()
    with pytest.raises(SystemExit) as exc:
        parser.parse_args(["--version"])
    assert exc.value.code == 0
    assert "toolkit-rag" in capsys.readouterr().out


def test_cli_score_and_compare(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    queries = tmp_path / "queries.jsonl"
    retrieved = tmp_path / "retrieved.jsonl"
    queries.write_text(
        "\n".join(
            [
                json.dumps({"id": "q1", "query": "x", "relevant_ids": ["d1", "d2"]}),
                json.dumps({"id": "q2", "query": "y", "relevant_ids": ["d9"]}),
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    retrieved.write_text(
        "\n".join(
            [
                json.dumps({"id": "q1", "retrieved_ids": ["d2", "d3"]}),
                json.dumps({"id": "q2", "retrieved_ids": ["d9"]}),
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    parser = build_parser()
    out_report = tmp_path / "report.json"
    score_args = parser.parse_args(
        [
            "score",
            "--queries",
            str(queries),
            "--retrieved",
            str(retrieved),
            "--k",
            "2",
            "--out",
            str(out_report),
        ]
    )
    assert int(score_args.func(score_args)) == 0
    assert out_report.exists()
    candidate_payload = json.loads(capsys.readouterr().out)
    assert "summary" in candidate_payload
    validate_args = parser.parse_args(["validate-report", "--report", str(out_report)])
    assert int(validate_args.func(validate_args)) == 0

    baseline = tmp_path / "baseline.json"
    baseline.write_text(
        json.dumps({"summary": {"recall_at_k": 1.0}, "per_query": []}),
        encoding="utf-8",
    )
    compare_args = parser.parse_args(
        [
            "compare",
            "--baseline",
            str(baseline),
            "--candidate",
            str(out_report),
            "--max-recall-regression-pct",
            "2.0",
        ]
    )
    rc = int(compare_args.func(compare_args))
    assert rc in {0, 4}


def test_cli_overlap(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    a = tmp_path / "a.jsonl"
    b = tmp_path / "b.jsonl"
    a.write_text(
        "\n".join(
            [
                json.dumps({"id": "a1", "text": "Hello world"}),
                json.dumps({"id": "a2", "text": "A"}),
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    b.write_text(
        "\n".join(
            [
                json.dumps({"id": "b1", "text": "hello   world"}),
                json.dumps({"id": "b2", "text": "B"}),
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    parser = build_parser()
    args = parser.parse_args(["overlap", "--a", str(a), "--b", str(b), "--max-records", "10"])
    assert int(args.func(args)) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["overlap_docs"] == 1

