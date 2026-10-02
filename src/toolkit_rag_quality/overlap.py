"""Exact-duplicate overlap between two text corpora.

Each document's text is normalized (lowercased, surrounding whitespace
stripped, internal whitespace collapsed to single spaces) and fingerprinted
with SHA-256. Two documents overlap only when their normalized text is
identical: texts that differ by a single character or punctuation mark are
not matched. For near-duplicates, see :mod:`toolkit_rag_quality.leakage`.
"""

from __future__ import annotations

import hashlib
import logging
from typing import Any

logger = logging.getLogger(__name__)


def _norm(text: str) -> str:
    return " ".join(text.strip().lower().split())


def _fingerprint(text: str) -> str:
    return hashlib.sha256(_norm(text).encode("utf-8")).hexdigest()


def _fingerprints(rows: list[dict[str, Any]], label: str) -> tuple[dict[str, str], int]:
    fps: dict[str, str] = {}
    skipped = 0
    for row in rows:
        if "id" not in row or "text" not in row:
            skipped += 1
            continue
        fps[str(row["id"])] = _fingerprint(str(row["text"]))
    if skipped:
        logger.warning("Skipped %d row(s) in corpus %s without 'id' or 'text'", skipped, label)
    return fps, skipped


def compute_overlap(
    *, a: list[dict[str, Any]], b: list[dict[str, Any]], max_records: int = 50000
) -> dict:
    """Count documents in corpus A whose normalized text also appears in B.

    ``overlap_rate`` is the share of A's distinct normalized texts found in B.

    Raises:
        ValueError: if either corpus has more than ``max_records`` rows. The
            input is rejected rather than truncated, because a leakage check
            over a truncated corpus can report a false-clean result.
    """
    if max_records < 1:
        raise ValueError(f"max_records must be a positive integer, got {max_records!r}")
    for label, rows in (("A", a), ("B", b)):
        if len(rows) > max_records:
            raise ValueError(
                f"corpus {label} has {len(rows)} records, more than max_records={max_records}; "
                "raise --max-records to process the whole corpus"
            )

    a_fps, a_skipped = _fingerprints(a, "A")
    b_fps, b_skipped = _fingerprints(b, "B")

    a_set = set(a_fps.values())
    b_set = set(b_fps.values())
    overlap = a_set.intersection(b_set)

    return {
        "a_docs": len(a_fps),
        "b_docs": len(b_fps),
        "a_skipped_rows": a_skipped,
        "b_skipped_rows": b_skipped,
        "overlap_docs": len(overlap),
        "overlap_rate": (len(overlap) / len(a_set)) if a_set else 0.0,
        "match": "exact_normalized_text",
    }
