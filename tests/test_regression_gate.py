"""Regression gate: per-query diff, paired significance, multi-metric budgets."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from toolkit_rag_quality.cli import main
from toolkit_rag_quality.compare import CompareBudget, compare_reports
from toolkit_rag_quality.retrieval import score_run
from toolkit_rag_quality.stats import paired_permutation_test, paired_t_test

K = 3


def _qrels(n: int) -> dict[str, dict[str, int]]:
    return {f"q{i}": {f"d{i}": 1} for i in range(n)}


def _run(n: int, miss: set[int] = frozenset(), late: set[int] = frozenset()) -> dict:
    """Relevant doc at rank 1, except rank 3 for ``late`` and absent for ``miss``."""
    run = {}
    for i in range(n):
        if i in miss:
            run[f"q{i}"] = ["x", "y", "z"]
        elif i in late:
            run[f"q{i}"] = ["x", "y", f"d{i}"]
        else:
            run[f"q{i}"] = [f"d{i}", "x", "y"]
    return run


def _report(n: int, **kw):
    return score_run(qrels=_qrels(n), run=_run(n, **kw), k=K)


def test_per_query_diff_names_the_queries_that_got_worse() -> None:
    base = _report(6)
    cand = _report(6, miss={2}, late={4})
    result = compare_reports(baseline=base, candidate=cand, budget=CompareBudget())
    assert result["passed"] is False
    assert result["per_query"]["ndcg_at_k"] == {"worse": 2, "better": 0, "unchanged": 4}
    assert result["per_query"]["recall_at_k"] == {"worse": 1, "better": 0, "unchanged": 5}
    # Most regressed first: q2 lost its hit (delta -1), q4 dropped to rank 3 (delta -0.5).
    assert [(w["id"], w["delta"]) for w in result["most_regressed"]] == [("q2", -1.0), ("q4", -0.5)]
    diff = {row["id"]: row for row in result["per_query_diff"]}
    assert diff["q4"]["mrr"] == {"baseline": 1.0, "candidate": 1 / 3, "delta": 1 / 3 - 1.0}
    assert diff["q0"]["ndcg"]["delta"] == 0.0


def test_p_values_are_the_paired_tests_on_per_query_scores() -> None:
    base = _report(20)
    cand = _report(20, miss={1, 5, 9}, late={3})
    result = compare_reports(baseline=base, candidate=cand, budget=CompareBudget(), test="t-test")
    ndcg = result["metrics"]["ndcg_at_k"]
    b = [row["ndcg"] for row in base.per_query]
    c = [row["ndcg"] for row in cand.per_query]
    assert ndcg["p_value"] == paired_t_test(b, c).p_value
    assert ndcg["p_value_permutation"] == paired_permutation_test(b, c).p_value


def test_per_metric_budgets_override_and_off_disables_gating() -> None:
    base = _report(10)
    cand = _report(10, late={0})  # hit rate and recall unchanged; MRR/nDCG/MAP/precision drop
    loose = CompareBudget(
        max_recall_regression_pct=0.0,
        max_regression_pct=0.0,
        per_metric={"mrr_at_k": 10.0, "ndcg_at_k": 10.0, "map_at_k": None, "precision_at_k": None},
    )
    result = compare_reports(baseline=base, candidate=cand, budget=loose)
    assert result["passed"] is True
    assert result["metrics"]["map_at_k"]["gated"] is False
    assert result["metrics"]["map_at_k"]["over_budget"] is False

    strict = CompareBudget(max_recall_regression_pct=0.0, per_metric={"mrr_at_k": 1.0})
    result = compare_reports(baseline=base, candidate=cand, budget=strict)
    assert "mrr_at_k" in result["failed_metrics"]


def test_alpha_lets_a_non_significant_drop_pass() -> None:
    # 1 of 20 queries loses its hit: 5% drop, over a 2% budget, but p is large.
    base = _report(20)
    cand = _report(20, miss={7})
    plain = compare_reports(baseline=base, candidate=cand, budget=CompareBudget())
    assert plain["passed"] is False
    gated = compare_reports(baseline=base, candidate=cand, budget=CompareBudget(), alpha=0.05)
    assert gated["passed"] is True
    recall = gated["metrics"]["recall_at_k"]
    assert recall["over_budget"] is True and recall["significant"] is False
    assert recall["p_value"] > 0.5  # one changed query out of 20


def test_alpha_still_fails_a_significant_drop() -> None:
    base = _report(20)
    cand = _report(20, miss=set(range(10)))
    result = compare_reports(baseline=base, candidate=cand, budget=CompareBudget(), alpha=0.05)
    assert result["passed"] is False
    recall = result["metrics"]["recall_at_k"]
    assert recall["significant"] is True and recall["p_value"] < 0.05


def test_alpha_without_per_query_rows_is_an_error() -> None:
    base = _report(4)
    bare = type(base)(summary=dict(base.summary), per_query=[])
    with pytest.raises(ValueError, match="per-query rows"):
        compare_reports(baseline=bare, candidate=bare, budget=CompareBudget(), alpha=0.05)


def test_invalid_options_are_rejected() -> None:
    base = _report(3)
    with pytest.raises(ValueError):
        compare_reports(baseline=base, candidate=base, budget=CompareBudget(), alpha=1.5)
    with pytest.raises(ValueError):
        compare_reports(baseline=base, candidate=base, budget=CompareBudget(), test="z-test")
    with pytest.raises(ValueError):
        compare_reports(baseline=base, candidate=base, budget=CompareBudget(), primary_metric="f1")


# ------------------------------------------------------------------- CLI


def _write_report(tmp_path: Path, name: str, n: int, **kw) -> Path:
    q = tmp_path / "qrels.trec"
    q.write_text("".join(f"q{i} 0 d{i} 1\n" for i in range(n)), encoding="utf-8")
    r = tmp_path / f"{name}.jsonl"
    r.write_text(
        "".join(
            json.dumps({"id": qid, "retrieved_ids": ids}) + "\n"
            for qid, ids in _run(n, **kw).items()
        ),
        encoding="utf-8",
    )
    out = tmp_path / f"{name}.json"
    assert (
        main(
            ["score", "--queries", str(q), "--retrieved", str(r), "--k", str(K), "--out", str(out)]
        )
        == 0
    )
    return out


def test_cli_compare_writes_per_query_diff_and_markdown(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    base = _write_report(tmp_path, "base", 8)
    cand = _write_report(tmp_path, "cand", 8, miss={3})
    out = tmp_path / "cmp.json"
    capsys.readouterr()
    rc = main(
        ["compare", "--baseline", str(base), "--candidate", str(cand), "--out", str(out),
         "--budget", "ndcg=1", "--budget", "hit_rate=off", "--format", "markdown"]
    )  # fmt: skip
    assert rc == 4
    md = capsys.readouterr().out
    assert "rag.compare: FAIL" in md
    assert "| ndcg_at_k |" in md and "**FAIL**" in md
    assert "| q3 | -1.0000 |" in md
    env = json.loads(out.read_text(encoding="utf-8"))
    pred = env["predicate"]
    assert pred["verdict"] == "fail"
    assert pred["summary"]["metrics"]["hit_rate_at_k"]["gated"] is False
    assert pred["summary"]["metrics"]["ndcg_at_k"]["max_regression_pct"] == 1.0
    assert [r["id"] for r in pred["details"]["per_query_diff"]] == [f"q{i}" for i in range(8)]
    assert "per_query_diff" not in pred["summary"]


def test_cli_compare_alpha_passes_noise(tmp_path: Path) -> None:
    base = _write_report(tmp_path, "base", 20)
    cand = _write_report(tmp_path, "cand", 20, miss={11})
    args = ["compare", "--baseline", str(base), "--candidate", str(cand)]
    assert main(args) == 4
    assert main([*args, "--alpha", "0.05"]) == 0
    assert main([*args, "--alpha", "0.05", "--test", "t-test"]) == 0


@pytest.mark.parametrize("bad", ["ndcg", "ndcg=abc", "f1=2", "ndcg=-1"])
def test_cli_compare_rejects_bad_budget(tmp_path: Path, bad: str) -> None:
    base = _write_report(tmp_path, "base", 3)
    rc = main(["compare", "--baseline", str(base), "--candidate", str(base), "--budget", bad])
    assert rc == 2
