"""Retriever adapters: run a retriever over queries to produce a run file.

The LangChain and LlamaIndex tests use the real libraries (the ``langchain``
and ``llamaindex`` extras) and are skipped when those are not installed; CI
installs them in the ``adapters`` job.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

from toolkit_rag_quality.adapters import (
    detect_framework,
    load_object,
    query_texts,
    run_retriever,
)
from toolkit_rag_quality.cli import main
from toolkit_rag_quality.formats import read_trec_run

DOCS = {
    "d1": "aspirin reduces fever and pain",
    "d2": "insulin regulates blood sugar",
    "d3": "aspirin thins the blood",
    "d4": "vitamin c and the common cold",
}
QUERIES = [("q1", "aspirin"), ("q2", "blood sugar"), ("q3", "nothing matches")]


def _keyword_ids(query: str) -> list[str]:
    """Rank docs by the number of query words they contain (ties by doc id)."""
    words = query.lower().split()
    scored = [(sum(w in text.split() for w in words), doc) for doc, text in DOCS.items()]
    return [doc for score, doc in sorted(scored, key=lambda s: (-s[0], s[1])) if score > 0]


EXPECTED = {"q1": ["d1", "d3"], "q2": ["d2", "d3"], "q3": []}


def test_callable_retriever() -> None:
    assert detect_framework(_keyword_ids) == "callable"
    assert run_retriever(_keyword_ids, QUERIES) == EXPECTED


def test_results_are_deduplicated_and_truncated() -> None:
    run = run_retriever(lambda q: ["a", "b", "a", "c", "d"], [("q", "x")], k=3)
    assert run == {"q": ["a", "b", "c"]}


def test_retriever_errors_name_the_query() -> None:
    def boom(query: str) -> list[str]:
        raise ConnectionError("index offline")

    with pytest.raises(RuntimeError, match="query 'q1'.*index offline"):
        run_retriever(boom, [("q1", "x")])


def test_results_without_ids_fail() -> None:
    with pytest.raises(ValueError, match="not a doc id"):
        run_retriever(lambda q: [object()], [("q1", "x")])


def test_query_texts_reads_beir_rows() -> None:
    rows = [{"_id": "1", "text": "a question"}, {"id": "2", "query": "another"}]
    assert query_texts(rows) == [("1", "a question"), ("2", "another")]
    with pytest.raises(ValueError):
        query_texts([{"_id": "3"}])


def test_load_object_supports_factories(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    (tmp_path / "my_retriever_mod.py").write_text(
        "def build():\n    return lambda q: ['d1']\nRETRIEVER = lambda q: ['d2']\n",
        encoding="utf-8",
    )
    monkeypatch.chdir(tmp_path)
    monkeypatch.syspath_prepend(str(tmp_path))
    assert load_object("my_retriever_mod:build()")("x") == ["d1"]
    assert load_object("my_retriever_mod:RETRIEVER")("x") == ["d2"]
    with pytest.raises(ValueError):
        load_object("my_retriever_mod")
    with pytest.raises(ValueError):
        load_object("my_retriever_mod:missing")
    sys.modules.pop("my_retriever_mod", None)


# ------------------------------------------------------------------ LangChain


def _langchain_retriever(with_ids: bool = True):
    lc_retrievers = pytest.importorskip("langchain_core.retrievers")
    from langchain_core.documents import Document

    class KeywordRetriever(lc_retrievers.BaseRetriever):
        def _get_relevant_documents(self, query, *, run_manager):  # type: ignore[override]
            return [
                Document(
                    page_content=DOCS[d],
                    id=d if with_ids else None,
                    metadata={"doc_id": d},
                )
                for d in _keyword_ids(query)
            ]

    return KeywordRetriever()


def test_langchain_retriever_uses_document_ids() -> None:
    retriever = _langchain_retriever()
    assert detect_framework(retriever) == "langchain"
    assert run_retriever(retriever, QUERIES) == EXPECTED


def test_langchain_retriever_with_metadata_id_key() -> None:
    retriever = _langchain_retriever(with_ids=False)
    assert run_retriever(retriever, QUERIES, id_key="doc_id") == EXPECTED
    with pytest.raises(ValueError, match="no id"):
        run_retriever(retriever, QUERIES)


# ----------------------------------------------------------------- LlamaIndex


def _llamaindex_retriever():
    li = pytest.importorskip("llama_index.core.retrievers")
    from llama_index.core.schema import NodeWithScore, TextNode

    class KeywordRetriever(li.BaseRetriever):
        def _retrieve(self, query_bundle):  # type: ignore[override]
            ranked = _keyword_ids(query_bundle.query_str)
            return [
                NodeWithScore(
                    node=TextNode(id_=d, text=DOCS[d], metadata={"doc_id": d}),
                    score=float(len(ranked) - i),
                )
                for i, d in enumerate(ranked)
            ]

    return KeywordRetriever()


def test_llamaindex_retriever_uses_node_ids() -> None:
    retriever = _llamaindex_retriever()
    assert detect_framework(retriever) == "llamaindex"
    assert run_retriever(retriever, QUERIES) == EXPECTED
    assert run_retriever(retriever, QUERIES, id_key="doc_id") == EXPECTED


# ------------------------------------------------------------------------ CLI


def test_cli_run_retriever_writes_a_scorable_trec_run(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    (tmp_path / "kw_retriever_mod.py").write_text(
        "DOCS = " + repr(DOCS) + "\n"
        "def search(query):\n"
        "    words = query.lower().split()\n"
        "    scored = [(sum(w in t.split() for w in words), d) for d, t in DOCS.items()]\n"
        "    return [d for s, d in sorted(scored, key=lambda x: (-x[0], x[1])) if s > 0]\n",
        encoding="utf-8",
    )
    monkeypatch.chdir(tmp_path)
    monkeypatch.syspath_prepend(str(tmp_path))
    queries = tmp_path / "queries.jsonl"
    queries.write_text(
        "".join(json.dumps({"_id": q, "text": t}) + "\n" for q, t in QUERIES), encoding="utf-8"
    )
    run = tmp_path / "run.trec"
    rc = main(
        ["run-retriever", "--retriever", "kw_retriever_mod:search", "--queries", str(queries),
         "--k", "10", "--out", str(run), "--to", "trec", "--tag", "keyword"]
    )  # fmt: skip
    assert rc == 0
    assert read_trec_run(run) == {q: ids for q, ids in EXPECTED.items() if ids}
    assert "keyword" in run.read_text(encoding="utf-8")

    qrels = tmp_path / "qrels.trec"
    qrels.write_text("q1 0 d3 1\nq2 0 d2 1\n", encoding="utf-8")
    report = tmp_path / "report.json"
    assert (
        main(["score", "--queries", str(qrels), "--retrieved", str(run), "--out", str(report)]) == 0
    )
    summary = json.loads(report.read_text(encoding="utf-8"))["predicate"]["summary"]
    assert summary["mrr_at_k"] == pytest.approx((1 / 2 + 1) / 2)
    sys.modules.pop("kw_retriever_mod", None)


def test_cli_run_retriever_bad_spec_is_exit_2(tmp_path: Path) -> None:
    queries = tmp_path / "q.jsonl"
    queries.write_text('{"id": "q1", "query": "x"}\n', encoding="utf-8")
    out = tmp_path / "run.jsonl"
    args = ["run-retriever", "--queries", str(queries), "--out", str(out)]
    assert main([*args, "--retriever", "no_such_module_xyz:thing"]) == 2
    assert main([*args, "--retriever", "json"]) == 2
    assert not out.exists()
