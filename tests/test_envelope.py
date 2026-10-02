"""Report envelope v1: in-toto Statement output, canonical JSON, schema agreement."""

from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path

import jsonschema
import pytest

from toolkit_rag_quality.cli import main
from toolkit_rag_quality.envelope import (
    PREDICATE_TYPE,
    STATEMENT_TYPE,
    canonical_json,
    validate_envelope,
)

ROOT = Path(__file__).resolve().parents[1]
SCHEMA = json.loads((ROOT / "schemas" / "report-envelope.v1.json").read_text(encoding="utf-8"))


def _write(path: Path, rows: list[dict]) -> Path:
    path.write_text("\n".join(json.dumps(r) for r in rows) + "\n", encoding="utf-8")
    return path


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


@pytest.fixture()
def score_files(tmp_path: Path) -> tuple[Path, Path]:
    q = _write(
        tmp_path / "queries.jsonl",
        [{"id": "q1", "relevant_ids": ["d1", "d2"]}, {"id": "q2", "relevant_ids": ["d3"]}],
    )
    r = _write(
        tmp_path / "run.jsonl",
        [{"id": "q1", "retrieved_ids": ["d1", "x"]}, {"id": "q2", "retrieved_ids": ["y", "d3"]}],
    )
    return q, r


def _score(q: Path, r: Path, out: Path, *extra: str) -> int:
    return main(["score", "--queries", str(q), "--retrieved", str(r), "--out", str(out), *extra])


def test_schema_is_a_valid_draft_2020_12_schema() -> None:
    jsonschema.Draft202012Validator.check_schema(SCHEMA)


def test_spec_document_is_committed() -> None:
    text = (ROOT / "docs" / "report-envelope.md").read_text(encoding="utf-8")
    assert "in-toto Statement v1" in text
    assert "schemas/report-envelope.v1.json" in text


def test_score_out_is_a_canonical_schema_valid_envelope(
    tmp_path: Path, score_files: tuple[Path, Path]
) -> None:
    q, r = score_files
    out = tmp_path / "report.json"
    assert _score(q, r, out, "--k", "2") == 0

    raw = out.read_bytes()
    env = json.loads(raw)
    # Canonical form: sorted keys, no insignificant whitespace, trailing newline.
    assert raw == canonical_json(env).encode("utf-8")
    assert raw.endswith(b"\n") and not raw.endswith(b"\n\n")
    assert b": " not in raw and b", " not in raw

    jsonschema.validate(env, SCHEMA)
    assert validate_envelope(env) == []
    assert env["_type"] == STATEMENT_TYPE
    assert env["predicateType"] == PREDICATE_TYPE
    pred = env["predicate"]
    assert pred["tool"]["name"] == "toolkit-rag-quality"
    assert pred["kind"] == "rag.score"
    assert (pred["verdict"], pred["exit_code"]) == ("pass", 0)
    # The subject is the evaluated run file, identified by its SHA-256.
    assert env["subject"] == [{"name": r.as_posix(), "digest": {"sha256": _sha(r)}}]
    assert [i["digest"]["sha256"] for i in pred["inputs"]] == [_sha(q), _sha(r)]
    assert pred["summary"]["k"] == 2
    assert pred["summary"]["recall_at_k"] == pytest.approx(0.75)
    assert [row["id"] for row in pred["details"]["per_query"]] == ["q1", "q2"]


def test_source_date_epoch_makes_reports_byte_identical(
    tmp_path: Path, score_files: tuple[Path, Path], monkeypatch: pytest.MonkeyPatch
) -> None:
    q, r = score_files
    monkeypatch.setenv("SOURCE_DATE_EPOCH", "1790000000")
    a, b = tmp_path / "a.json", tmp_path / "b.json"
    assert _score(q, r, a) == 0
    assert _score(q, r, b) == 0
    assert a.read_bytes() == b.read_bytes()
    assert json.loads(a.read_bytes())["predicate"]["created_at"] == "2026-09-21T14:13:20Z"


def test_stdout_json_is_the_same_envelope(
    tmp_path: Path, score_files: tuple[Path, Path], capsys: pytest.CaptureFixture[str]
) -> None:
    q, r = score_files
    out = tmp_path / "report.json"
    assert _score(q, r, out) == 0
    assert capsys.readouterr().out == out.read_text(encoding="utf-8")


def test_legacy_json_flag_keeps_the_old_shape(
    tmp_path: Path, score_files: tuple[Path, Path]
) -> None:
    q, r = score_files
    out = tmp_path / "legacy.json"
    assert _score(q, r, out, "--legacy-json") == 0
    obj = json.loads(out.read_text(encoding="utf-8"))
    assert set(obj) == {"schema_version", "summary", "per_query"}


def test_input_error_writes_an_error_envelope(tmp_path: Path) -> None:
    q = _write(tmp_path / "q.jsonl", [{"id": "q1", "relevant_ids": []}])  # nothing judged
    r = _write(tmp_path / "r.jsonl", [{"id": "q1", "retrieved_ids": ["d1"]}])
    out = tmp_path / "report.json"
    assert _score(q, r, out) == 2
    env = json.loads(out.read_text(encoding="utf-8"))
    jsonschema.validate(env, SCHEMA)
    assert (env["predicate"]["verdict"], env["predicate"]["exit_code"]) == ("error", 2)
    assert "no judged queries" in env["predicate"]["summary"]["error"]


def test_missing_input_writes_no_report(tmp_path: Path) -> None:
    q = _write(tmp_path / "q.jsonl", [{"id": "q1", "relevant_ids": ["d1"]}])
    out = tmp_path / "report.json"
    assert _score(q, tmp_path / "missing.jsonl", out) == 2
    assert not out.exists()


def _compare(base: Path, cand: Path, out: Path) -> int:
    return main(["compare", "--baseline", str(base), "--candidate", str(cand), "--out", str(out)])


def test_compare_reads_envelopes_and_emits_pass_or_fail(tmp_path: Path) -> None:
    q = _write(tmp_path / "q.jsonl", [{"id": "q1", "relevant_ids": ["d1"]}])
    good = _write(tmp_path / "good.jsonl", [{"id": "q1", "retrieved_ids": ["d1"]}])
    bad = _write(tmp_path / "bad.jsonl", [{"id": "q1", "retrieved_ids": ["x", "d1"]}])
    base, worse = tmp_path / "base.json", tmp_path / "worse.json"
    assert _score(q, good, base) == 0
    assert _score(q, bad, worse) == 0

    same = tmp_path / "same.json"
    assert _compare(base, base, same) == 0
    env = json.loads(same.read_text(encoding="utf-8"))
    jsonschema.validate(env, SCHEMA)
    assert (env["predicate"]["kind"], env["predicate"]["verdict"]) == ("rag.compare", "pass")

    regressed = tmp_path / "regressed.json"
    assert _compare(base, worse, regressed) == 4
    env = json.loads(regressed.read_text(encoding="utf-8"))
    jsonschema.validate(env, SCHEMA)
    assert (env["predicate"]["verdict"], env["predicate"]["exit_code"]) == ("fail", 4)
    assert "mrr_at_k" in env["predicate"]["summary"]["failed_metrics"]
    assert env["subject"][0]["digest"]["sha256"] == _sha(worse)


def test_compare_still_reads_legacy_reports(tmp_path: Path) -> None:
    legacy = tmp_path / "legacy.json"
    legacy.write_text(
        json.dumps({"summary": {"k": 5, "recall_at_k": 0.5}, "per_query": []}), encoding="utf-8"
    )
    assert _compare(legacy, legacy, tmp_path / "out.json") == 0


def test_compare_rejects_a_non_score_envelope(tmp_path: Path) -> None:
    a = _write(tmp_path / "a.jsonl", [{"id": "a1", "text": "x"}])
    overlap = tmp_path / "overlap.json"
    assert main(["overlap", "--a", str(a), "--b", str(a), "--out", str(overlap)]) == 0
    out = tmp_path / "cmp.json"
    assert _compare(overlap, overlap, out) == 2
    env = json.loads(out.read_text(encoding="utf-8"))
    assert env["predicate"]["verdict"] == "error"


def test_overlap_emits_an_envelope(tmp_path: Path) -> None:
    a = _write(tmp_path / "a.jsonl", [{"id": "a1", "text": "Hello  World"}])
    b = _write(tmp_path / "b.jsonl", [{"id": "b1", "text": "hello world"}])
    out = tmp_path / "overlap.json"
    assert main(["overlap", "--a", str(a), "--b", str(b), "--out", str(out)]) == 0
    env = json.loads(out.read_text(encoding="utf-8"))
    jsonschema.validate(env, SCHEMA)
    assert env["predicate"]["kind"] == "rag.overlap"
    assert env["predicate"]["summary"]["overlap_docs"] == 1
    assert [s["name"] for s in env["subject"]] == [a.as_posix(), b.as_posix()]


def test_validate_report_accepts_envelope_and_rejects_inconsistent_verdict(
    tmp_path: Path, score_files: tuple[Path, Path]
) -> None:
    q, r = score_files
    out = tmp_path / "report.json"
    assert _score(q, r, out) == 0
    assert main(["validate-report", "--report", str(out)]) == 0

    env = json.loads(out.read_text(encoding="utf-8"))
    env["predicate"]["exit_code"] = 4  # verdict still "pass"
    bad = tmp_path / "bad.json"
    bad.write_text(json.dumps(env), encoding="utf-8")
    assert main(["validate-report", "--report", str(bad)]) == 4


def _valid_envelope() -> dict:
    return {
        "_type": STATEMENT_TYPE,
        "subject": [{"name": "run.jsonl", "digest": {"sha256": "a" * 64}}],
        "predicateType": PREDICATE_TYPE,
        "predicate": {
            "tool": {"name": "toolkit-rag-quality", "version": "1.0.0"},
            "kind": "rag.score",
            "created_at": "2026-09-26T18:00:00Z",
            "verdict": "pass",
            "exit_code": 0,
            "inputs": [],
            "summary": {},
            "details": {},
        },
    }


def _mutations() -> list[tuple[str, dict]]:
    cases: list[tuple[str, dict]] = []

    def case(name: str, fn) -> None:
        env = _valid_envelope()
        fn(env)
        cases.append((name, env))

    case("wrong _type", lambda e: e.update(_type="https://in-toto.io/Statement/v0.1"))
    case("empty subject", lambda e: e.update(subject=[]))
    case("bad digest", lambda e: e["subject"][0]["digest"].update(sha256="ABC"))
    case("no digest", lambda e: e["subject"][0].pop("digest"))
    case("bad predicateType", lambda e: e.update(predicateType="https://example.com/x"))
    case("missing summary", lambda e: e["predicate"].pop("summary"))
    case("bad verdict", lambda e: e["predicate"].update(verdict="ok"))
    case("pass with exit 4", lambda e: e["predicate"].update(exit_code=4))
    case("fail with exit 0", lambda e: e["predicate"].update(verdict="fail"))
    case("error with exit 0", lambda e: e["predicate"].update(verdict="error"))
    case("negative exit", lambda e: e["predicate"].update(exit_code=-1, verdict="error"))
    case("non-UTC time", lambda e: e["predicate"].update(created_at="2026-09-26T18:00:00+02:00"))
    case("bad kind", lambda e: e["predicate"].update(kind="score"))
    case("tool without version", lambda e: e["predicate"]["tool"].pop("version"))
    case("details not object", lambda e: e["predicate"].update(details=[]))
    return cases


def test_valid_envelope_passes_both_validators() -> None:
    env = _valid_envelope()
    jsonschema.validate(env, SCHEMA)
    assert validate_envelope(env) == []


@pytest.mark.parametrize(("name", "env"), _mutations(), ids=[n for n, _ in _mutations()])
def test_builtin_validator_agrees_with_json_schema(name: str, env: dict) -> None:
    """Every mutation is rejected by both the JSON Schema and validate_envelope."""
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(copy.deepcopy(env), SCHEMA)
    assert validate_envelope(env), name


def test_unknown_fields_are_ignored_by_both_validators() -> None:
    """in-toto Statement v1 consumers ignore unrecognized fields; so does the shared schema."""
    env = _valid_envelope()
    env["extra"] = 1
    env["predicate"]["note"] = "x"
    jsonschema.validate(env, SCHEMA)
    assert validate_envelope(env) == []


def test_canonical_json_rejects_nan() -> None:
    with pytest.raises(ValueError):
        canonical_json({"x": float("nan")})
