"""Relevance judgments (qrels) and runs: JSONL, TREC and BEIR formats.

In memory:

* **qrels** map a query id to ``{doc_id: grade}``. Grades are integers, as in
  trec_eval. A document is *relevant* when its grade is at least the
  relevance level (default 1); nDCG uses every positive grade as its gain.
* a **run** maps a query id to a ranked list of doc ids, best first.

On disk:

* JSONL queries: ``{"id": "q1", "relevant_ids": ["d1"]}`` (each listed id
  has grade 1) or ``{"id": "q1", "relevance": {"d1": 2, "d2": 0}}``.
* JSONL runs: ``{"id": "q1", "retrieved_ids": ["d9", "d1"]}``.
* TREC qrels: ``qid iter docid grade`` per line.
* TREC runs: ``qid Q0 docid rank score tag`` per line. As in trec_eval, the
  ranking is by score, highest first, with ties broken by doc id in
  descending order; the rank column is ignored.
* BEIR qrels: tab-separated ``query-id  corpus-id  score`` with a header line
  (``qrels/<split>.tsv`` in a BEIR dataset).
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

from .io import read_jsonl, validate_path_for_read, write_text

logger = logging.getLogger(__name__)

Qrels = dict[str, dict[str, int]]
Run = dict[str, list[str]]

QRELS_FORMATS = ("auto", "jsonl", "trec", "beir")
RUN_FORMATS = ("auto", "jsonl", "trec")


def _as_str_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [str(x) for x in value]
    return [str(value)]


def _grade(value: Any, where: str) -> int:
    """Parse a relevance grade. Grades must be integers (as in trec_eval)."""
    if isinstance(value, bool):
        raise ValueError(f"{where}: relevance grade must be an integer, got {value!r}")
    if isinstance(value, int):
        return value
    if isinstance(value, float) and value.is_integer():
        return int(value)
    if isinstance(value, str):
        try:
            return int(value)
        except ValueError:
            pass
        try:
            f = float(value)
        except ValueError:
            f = None
        if f is not None and f.is_integer():
            return int(f)
    raise ValueError(f"{where}: relevance grade must be an integer, got {value!r}")


def _read_lines(path: Path) -> list[str]:
    validated = validate_path_for_read(path)
    return validated.read_text(encoding="utf-8").splitlines()


def detect_format(path: Path) -> str:
    """Guess a file's format from its first non-empty line.

    ``jsonl`` if it is a JSON object, ``beir`` if it is a tab-separated
    ``query-id`` header, ``trec-run`` for six whitespace-separated columns
    and ``trec-qrels`` for four.
    """
    for line in _read_lines(path):
        stripped = line.strip()
        if not stripped:
            continue
        if stripped.startswith("{"):
            return "jsonl"
        if stripped.lower().startswith("query-id") or stripped.lower().startswith("query_id"):
            return "beir"
        cols = stripped.split()
        if len(cols) == 6:
            return "trec-run"
        if len(cols) == 4:
            return "trec-qrels"
        raise ValueError(f"{path}: cannot detect the format of line {stripped[:80]!r}")
    raise ValueError(f"{path}: file is empty")


# --------------------------------------------------------------------- JSONL


def qrels_from_rows(rows: list[dict[str, Any]]) -> tuple[Qrels, int]:
    """Build qrels from JSONL query rows. Returns ``(qrels, skipped_rows)``.

    Rows without an ``id`` are skipped and counted. A query with an empty
    ``relevant_ids`` list and no ``relevance`` map has no judgments; it is
    kept with an empty mapping so the scorer can report it as unjudged.

    Raises:
        ValueError: on a repeated query id, a row with both ``relevant_ids``
            and ``relevance``, or a non-integer grade.
    """
    qrels: Qrels = {}
    skipped = 0
    for n, row in enumerate(rows, start=1):
        if "id" not in row:
            skipped += 1
            continue
        qid = str(row["id"])
        if qid in qrels:
            raise ValueError(f"query row {n}: duplicate query id {qid!r}")
        has_ids = row.get("relevant_ids") not in (None, [])
        relevance = row.get("relevance")
        if relevance is not None:
            if has_ids:
                raise ValueError(
                    f"query row {n} ({qid!r}): use either 'relevant_ids' or 'relevance', not both"
                )
            if not isinstance(relevance, dict):
                raise ValueError(f"query row {n} ({qid!r}): 'relevance' must be an object")
            qrels[qid] = {
                str(doc): _grade(g, f"query row {n} ({qid!r}) doc {doc!r}")
                for doc, g in relevance.items()
            }
        else:
            qrels[qid] = {doc: 1 for doc in _as_str_list(row.get("relevant_ids"))}
    if skipped:
        logger.warning("Skipped %d query row(s) without an 'id' field", skipped)
    return qrels, skipped


def run_from_rows(rows: list[dict[str, Any]]) -> tuple[Run, int]:
    """Build a run from JSONL rows. Returns ``(run, skipped_rows)``.

    Raises:
        ValueError: on a repeated query id.
    """
    run: Run = {}
    skipped = 0
    for n, row in enumerate(rows, start=1):
        if "id" not in row:
            skipped += 1
            continue
        qid = str(row["id"])
        if qid in run:
            raise ValueError(f"retrieved row {n}: duplicate query id {qid!r}")
        run[qid] = _as_str_list(row.get("retrieved_ids"))
    if skipped:
        logger.warning("Skipped %d retrieved row(s) without an 'id' field", skipped)
    return run, skipped


def qrels_to_rows(qrels: Qrels) -> list[dict[str, Any]]:
    return [{"id": qid, "relevance": dict(docs)} for qid, docs in qrels.items()]


def run_to_rows(run: Run) -> list[dict[str, Any]]:
    return [{"id": qid, "retrieved_ids": list(docs)} for qid, docs in run.items()]


def _write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    write_text(path, "".join(json.dumps(r, sort_keys=True) + "\n" for r in rows))


# ---------------------------------------------------------------------- TREC


def read_trec_qrels(path: Path) -> Qrels:
    """Read a TREC qrels file (``qid iter docid grade``)."""
    qrels: Qrels = {}
    for n, line in enumerate(_read_lines(path), start=1):
        if not line.strip():
            continue
        cols = line.split()
        if len(cols) != 4:
            raise ValueError(f"{path}:{n}: expected 4 columns (qid iter docid grade)")
        qid, _iter, doc, grade = cols
        docs = qrels.setdefault(qid, {})
        g = _grade(grade, f"{path}:{n}")
        if doc in docs and docs[doc] != g:
            raise ValueError(f"{path}:{n}: conflicting grades for {qid} {doc}")
        docs[doc] = g
    return qrels


def read_beir_qrels(path: Path) -> Qrels:
    """Read BEIR qrels: TSV with a ``query-id corpus-id score`` header."""
    qrels: Qrels = {}
    lines = _read_lines(path)
    header_seen = False
    for n, line in enumerate(lines, start=1):
        if not line.strip():
            continue
        cols = line.split("\t")
        if not header_seen:
            header_seen = True
            if cols[0].strip().lower() in ("query-id", "query_id"):
                continue
        if len(cols) != 3:
            raise ValueError(f"{path}:{n}: expected 3 tab-separated columns")
        qid, doc, grade = (c.strip() for c in cols)
        docs = qrels.setdefault(qid, {})
        g = _grade(grade, f"{path}:{n}")
        if doc in docs and docs[doc] != g:
            raise ValueError(f"{path}:{n}: conflicting grades for {qid} {doc}")
        docs[doc] = g
    return qrels


def trec_ranking(scores: dict[str, float]) -> list[str]:
    """Order documents as trec_eval does: score descending, then doc id descending."""
    return sorted(scores, key=lambda d: (scores[d], d), reverse=True)


def read_trec_run(path: Path) -> Run:
    """Read a TREC run file (``qid Q0 docid rank score tag``).

    Raises:
        ValueError: on a malformed line, a non-numeric score, or a document
            listed twice for the same query.
    """
    scores: dict[str, dict[str, float]] = {}
    for n, line in enumerate(_read_lines(path), start=1):
        if not line.strip():
            continue
        cols = line.split()
        if len(cols) != 6:
            raise ValueError(f"{path}:{n}: expected 6 columns (qid Q0 docid rank score tag)")
        qid, _q0, doc, _rank, score, _tag = cols
        try:
            value = float(score)
        except ValueError:
            raise ValueError(f"{path}:{n}: score {score!r} is not a number") from None
        docs = scores.setdefault(qid, {})
        if doc in docs:
            raise ValueError(f"{path}:{n}: document {doc!r} listed twice for query {qid!r}")
        docs[doc] = value
    return {qid: trec_ranking(docs) for qid, docs in scores.items()}


def write_trec_qrels(path: Path, qrels: Qrels) -> None:
    lines = [
        f"{qid} 0 {doc} {grade}\n" for qid, docs in qrels.items() for doc, grade in docs.items()
    ]
    write_text(path, "".join(lines))


def write_trec_run(path: Path, run: Run, tag: str = "toolkit-rag") -> None:
    """Write a run in TREC format.

    The score column is ``len(ranking) - rank + 1``: strictly decreasing, so
    trec_eval reproduces the list order exactly. Runs carry ranks, not the
    retriever's own scores.
    """
    if not tag or any(c.isspace() for c in tag):
        raise ValueError(f"run tag must be a non-empty string without spaces, got {tag!r}")
    lines: list[str] = []
    for qid, docs in run.items():
        n = len(docs)
        lines.extend(
            f"{qid} Q0 {doc} {rank} {n - rank + 1} {tag}\n" for rank, doc in enumerate(docs, 1)
        )
    write_text(path, "".join(lines))


# -------------------------------------------------------------------- loaders


def load_qrels(path: Path, fmt: str = "auto") -> tuple[Qrels, int]:
    """Load qrels in any supported format. Returns ``(qrels, skipped_rows)``."""
    if fmt == "auto":
        detected = detect_format(path)
        fmt = {"trec-qrels": "trec", "trec-run": "trec-run"}.get(detected, detected)
    if fmt == "jsonl":
        return qrels_from_rows(list(read_jsonl(path)))
    if fmt == "trec":
        return read_trec_qrels(path), 0
    if fmt == "beir":
        return read_beir_qrels(path), 0
    if fmt == "trec-run":
        raise ValueError(f"{path}: looks like a TREC run, not qrels")
    raise ValueError(f"unknown qrels format {fmt!r}; expected one of {', '.join(QRELS_FORMATS)}")


def load_run(path: Path, fmt: str = "auto") -> tuple[Run, int]:
    """Load a run in any supported format. Returns ``(run, skipped_rows)``."""
    if fmt == "auto":
        detected = detect_format(path)
        if detected == "trec-run":
            fmt = "trec"
        elif detected == "jsonl":
            fmt = "jsonl"
        else:
            raise ValueError(f"{path}: looks like {detected}, not a run")
    if fmt == "jsonl":
        return run_from_rows(list(read_jsonl(path)))
    if fmt == "trec":
        return read_trec_run(path), 0
    raise ValueError(f"unknown run format {fmt!r}; expected one of {', '.join(RUN_FORMATS)}")


def write_qrels(path: Path, qrels: Qrels, fmt: str) -> None:
    if fmt == "jsonl":
        _write_jsonl(path, qrels_to_rows(qrels))
    elif fmt == "trec":
        write_trec_qrels(path, qrels)
    else:
        raise ValueError(f"cannot write qrels as {fmt!r}; expected jsonl or trec")


def write_run(path: Path, run: Run, fmt: str, tag: str = "toolkit-rag") -> None:
    if fmt == "jsonl":
        _write_jsonl(path, run_to_rows(run))
    elif fmt == "trec":
        write_trec_run(path, run, tag=tag)
    else:
        raise ValueError(f"cannot write a run as {fmt!r}; expected jsonl or trec")
