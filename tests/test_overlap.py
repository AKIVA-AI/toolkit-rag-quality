from __future__ import annotations

from toolkit_rag_quality.overlap import compute_overlap


def test_compute_overlap_exact_text() -> None:
    a = [{"id": "a1", "text": "Hello world"}, {"id": "a2", "text": "Unique A"}]
    b = [{"id": "b1", "text": "hello   world"}, {"id": "b2", "text": "Unique B"}]
    out = compute_overlap(a=a, b=b, max_records=100)
    assert out["a_docs"] == 2
    assert out["b_docs"] == 2
    assert out["overlap_docs"] == 1

