"""Run a retriever over a query set and produce a run (query id -> ranked doc ids).

Supported retrievers, detected from the object's class:

* **LangChain** retrievers (``langchain_core.retrievers.BaseRetriever`` and
  anything else with ``invoke(query) -> list[Document]``). Install the
  ``langchain`` extra.
* **LlamaIndex** retrievers (``llama_index.core.retrievers.BaseRetriever``,
  ``retrieve(query) -> list[NodeWithScore]``). Install the ``llamaindex`` extra.
* Any **callable** ``f(query: str) -> list`` returning doc ids (strings) or
  objects with an ``id`` attribute.

This module never imports LangChain or LlamaIndex itself; it only calls the
retriever it is given.

Document ids: with ``id_key`` set, the id is read from each result's metadata
(``Document.metadata[id_key]`` or ``node.metadata[id_key]``). Otherwise the
framework's own id is used (``Document.id`` for LangChain, ``node.node_id``
for LlamaIndex). A result without an id is an error, because a run with
made-up ids cannot be scored.
"""

from __future__ import annotations

import importlib
import logging
import sys
from collections.abc import Callable, Iterable
from pathlib import Path
from typing import Any

from .formats import Run

logger = logging.getLogger(__name__)

FRAMEWORKS = ("auto", "langchain", "llamaindex", "callable")


def detect_framework(retriever: Any) -> str:
    """``langchain``, ``llamaindex`` or ``callable``, from the class hierarchy."""
    for cls in type(retriever).__mro__:
        module = cls.__module__ or ""
        if module.startswith("langchain"):
            return "langchain"
        if module.startswith("llama_index"):
            return "llamaindex"
    if hasattr(retriever, "retrieve") and callable(retriever.retrieve):
        return "llamaindex"
    if hasattr(retriever, "invoke") and callable(retriever.invoke):
        return "langchain"
    if callable(retriever):
        return "callable"
    raise TypeError(
        f"{type(retriever).__name__} is not a LangChain or LlamaIndex retriever, or a callable"
    )


def _metadata_id(meta: Any, id_key: str, where: str) -> str:
    if not isinstance(meta, dict) or meta.get(id_key) in (None, ""):
        raise ValueError(f"{where}: result has no metadata[{id_key!r}]")
    return str(meta[id_key])


def _langchain_ids(results: Iterable[Any], id_key: str | None, where: str) -> list[str]:
    ids: list[str] = []
    for doc in results:
        if id_key:
            ids.append(_metadata_id(getattr(doc, "metadata", None), id_key, where))
            continue
        doc_id = getattr(doc, "id", None)
        if doc_id in (None, ""):
            raise ValueError(
                f"{where}: a LangChain Document has no id; set Document.id or pass --id-key"
            )
        ids.append(str(doc_id))
    return ids


def _llamaindex_ids(results: Iterable[Any], id_key: str | None, where: str) -> list[str]:
    ids: list[str] = []
    for item in results:
        node = getattr(item, "node", item)
        if id_key:
            ids.append(_metadata_id(getattr(node, "metadata", None), id_key, where))
            continue
        node_id = getattr(node, "node_id", None) or getattr(node, "id_", None)
        if node_id in (None, ""):
            raise ValueError(f"{where}: a LlamaIndex node has no node_id; pass --id-key")
        ids.append(str(node_id))
    return ids


def _callable_ids(results: Iterable[Any], id_key: str | None, where: str) -> list[str]:
    ids: list[str] = []
    for item in results:
        if isinstance(item, str):
            ids.append(item)
        elif id_key and isinstance(item, dict):
            ids.append(_metadata_id(item, id_key, where))
        elif getattr(item, "id", None) not in (None, ""):
            ids.append(str(item.id))
        else:
            raise ValueError(f"{where}: result {item!r} is not a doc id")
    return ids


def _dedupe(ids: list[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for d in ids:
        if d not in seen:
            seen.add(d)
            out.append(d)
    return out


def run_retriever(
    retriever: Any,
    queries: list[tuple[str, str]],
    *,
    k: int | None = None,
    id_key: str | None = None,
    framework: str = "auto",
) -> Run:
    """Retrieve for each ``(query_id, query_text)`` and return a run.

    Each ranking is de-duplicated (first occurrence wins) and truncated to
    ``k`` when given. A retriever error is re-raised with the query id.
    """
    if framework not in FRAMEWORKS:
        raise ValueError(f"framework must be one of {', '.join(FRAMEWORKS)}, got {framework!r}")
    if k is not None and k < 1:
        raise ValueError(f"k must be a positive integer, got {k!r}")
    kind = detect_framework(retriever) if framework == "auto" else framework
    call: Callable[[str], Any]
    extract: Callable[[Iterable[Any], str | None, str], list[str]]
    if kind == "langchain":
        call, extract = retriever.invoke, _langchain_ids
    elif kind == "llamaindex":
        call, extract = retriever.retrieve, _llamaindex_ids
    else:
        call, extract = retriever, _callable_ids

    run: Run = {}
    for qid, text in queries:
        if qid in run:
            raise ValueError(f"duplicate query id {qid!r}")
        where = f"query {qid!r}"
        try:
            results = call(text)
        except Exception as e:  # re-raised with context, never swallowed
            raise RuntimeError(f"{where}: retriever failed: {e}") from e
        ids = _dedupe(extract(results or [], id_key, where))
        run[qid] = ids[:k] if k else ids
    logger.info("Retrieved results for %d queries with a %s retriever", len(run), kind)
    return run


def load_object(spec: str) -> Any:
    """Load ``module:attr`` (or ``module:factory()`` to call a zero-argument factory).

    The current directory is put on ``sys.path`` first, so a local module works.
    This imports and runs the named code: only use specs you trust.
    """
    module_name, sep, attr = spec.partition(":")
    if not sep or not module_name or not attr:
        raise ValueError(f"expected 'module:attr' or 'module:factory()', got {spec!r}")
    call = attr.endswith("()")
    attr = attr[:-2] if call else attr
    cwd = str(Path.cwd())
    if cwd not in sys.path:
        sys.path.insert(0, cwd)
    module = importlib.import_module(module_name)
    obj: Any = module
    for part in attr.split("."):
        if not hasattr(obj, part):
            raise ValueError(f"{module_name} has no attribute {attr!r}")
        obj = getattr(obj, part)
    return obj() if call else obj


def query_texts(
    rows: list[dict[str, Any]], fields: tuple[str, ...] = ("query", "text", "question")
) -> list[tuple[str, str]]:
    """``(id, text)`` pairs from query rows (``id`` or BEIR ``_id``; first non-empty field).

    Raises:
        ValueError: if a row has no id or no text in any of ``fields``.
    """
    out: list[tuple[str, str]] = []
    for n, row in enumerate(rows, start=1):
        qid = row.get("id", row.get("_id"))
        text = next((row[f] for f in fields if isinstance(row.get(f), str) and row[f]), None)
        if qid is None or text is None:
            raise ValueError(f"query row {n}: needs an id and one of {', '.join(fields)}")
        out.append((str(qid), text))
    return out
