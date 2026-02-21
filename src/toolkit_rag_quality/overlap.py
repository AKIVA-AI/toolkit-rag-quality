from __future__ import annotations

import hashlib
from typing import Any


def _norm(text: str) -> str:
    return " ".join(text.strip().lower().split())


def _fingerprint(text: str) -> str:
    return hashlib.sha256(_norm(text).encode("utf-8")).hexdigest()


def compute_overlap(
    *, a: list[dict[str, Any]], b: list[dict[str, Any]], max_records: int = 50000
) -> dict:
    a_fps: dict[str, str] = {}
    b_fps: dict[str, str] = {}

    for row in a[:max_records]:
        if "id" not in row or "text" not in row:
            continue
        a_fps[str(row["id"])] = _fingerprint(str(row["text"]))

    for row in b[:max_records]:
        if "id" not in row or "text" not in row:
            continue
        b_fps[str(row["id"])] = _fingerprint(str(row["text"]))

    a_set = set(a_fps.values())
    b_set = set(b_fps.values())
    overlap = a_set.intersection(b_set)

    return {
        "a_docs": len(a_fps),
        "b_docs": len(b_fps),
        "overlap_docs": len(overlap),
        "overlap_rate": (len(overlap) / len(a_set)) if a_set else 0.0,
    }
