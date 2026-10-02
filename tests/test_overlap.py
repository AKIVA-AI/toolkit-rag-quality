from __future__ import annotations

import logging

import pytest

from toolkit_rag_quality.overlap import compute_overlap


def test_compute_overlap_exact_text() -> None:
    a = [{"id": "a1", "text": "Hello world"}, {"id": "a2", "text": "Unique A"}]
    b = [{"id": "b1", "text": "hello   world"}, {"id": "b2", "text": "Unique B"}]
    out = compute_overlap(a=a, b=b, max_records=100)
    assert out["a_docs"] == 2
    assert out["b_docs"] == 2
    assert out["overlap_docs"] == 1


def test_compute_overlap_empty_corpora() -> None:
    """Both corpora empty should return zero overlap."""
    out = compute_overlap(a=[], b=[], max_records=100)
    assert out["a_docs"] == 0
    assert out["b_docs"] == 0
    assert out["overlap_docs"] == 0
    assert out["overlap_rate"] == 0.0


def test_compute_overlap_single_doc_match() -> None:
    """Single doc in each corpus that match."""
    a = [{"id": "1", "text": "test doc"}]
    b = [{"id": "2", "text": "test doc"}]
    out = compute_overlap(a=a, b=b, max_records=100)
    assert out["overlap_docs"] == 1
    assert out["overlap_rate"] == 1.0


def test_compute_overlap_single_doc_no_match() -> None:
    """Single doc in each corpus that don't match."""
    a = [{"id": "1", "text": "alpha"}]
    b = [{"id": "2", "text": "beta"}]
    out = compute_overlap(a=a, b=b, max_records=100)
    assert out["overlap_docs"] == 0
    assert out["overlap_rate"] == 0.0


def test_compute_overlap_all_duplicates() -> None:
    """All docs in A appear in B."""
    a = [{"id": "a1", "text": "doc one"}, {"id": "a2", "text": "doc two"}]
    b = [
        {"id": "b1", "text": "doc one"},
        {"id": "b2", "text": "doc two"},
        {"id": "b3", "text": "extra"},
    ]
    out = compute_overlap(a=a, b=b, max_records=100)
    assert out["overlap_docs"] == 2
    assert out["overlap_rate"] == 1.0


def test_compute_overlap_missing_text_field() -> None:
    """Rows without 'text' field should be skipped."""
    a = [{"id": "a1", "text": "hello"}, {"id": "a2", "no_text": "missing"}]
    b = [{"id": "b1", "text": "hello"}, {"id": "b2"}]
    out = compute_overlap(a=a, b=b, max_records=100)
    assert out["a_docs"] == 1
    assert out["b_docs"] == 1
    assert out["overlap_docs"] == 1


def test_compute_overlap_missing_id_field() -> None:
    """Rows without 'id' field should be skipped."""
    a = [{"text": "no id here"}, {"id": "a1", "text": "valid"}]
    b = [{"id": "b1", "text": "valid"}]
    out = compute_overlap(a=a, b=b, max_records=100)
    assert out["a_docs"] == 1
    assert out["b_docs"] == 1


def test_compute_overlap_rejects_input_over_max_records() -> None:
    """Oversized input is rejected, never silently truncated (a truncated
    leakage check would report a false-clean result)."""
    a = [{"id": f"a{i}", "text": f"doc {i}"} for i in range(10)]
    b = [{"id": f"b{i}", "text": f"doc {i}"} for i in range(10)]
    with pytest.raises(ValueError, match="corpus A has 10 records, more than max_records=3"):
        compute_overlap(a=a, b=b, max_records=3)
    with pytest.raises(ValueError, match="corpus B has 10 records"):
        compute_overlap(a=a[:3], b=b, max_records=3)


def test_compute_overlap_at_max_records_is_accepted() -> None:
    a = [{"id": f"a{i}", "text": f"doc {i}"} for i in range(3)]
    out = compute_overlap(a=a, b=list(a), max_records=3)
    assert out["a_docs"] == 3
    assert out["overlap_docs"] == 3


def test_compute_overlap_counts_and_warns_on_skipped_rows(
    caplog: pytest.LogCaptureFixture,
) -> None:
    a = [{"id": "a1", "text": "x"}, {"text": "no id"}, {"id": "a3"}]
    b = [{"id": "b1", "text": "x"}, {"id": "b2"}]
    with caplog.at_level(logging.WARNING, logger="toolkit_rag_quality.overlap"):
        out = compute_overlap(a=a, b=b, max_records=100)
    assert out["a_skipped_rows"] == 2
    assert out["b_skipped_rows"] == 1
    assert any("corpus A" in r.getMessage() for r in caplog.records)


def test_compute_overlap_is_exact_match_only() -> None:
    """Documents that differ only in punctuation are NOT matched: overlap is
    exact after lowercasing and whitespace collapsing. Near-duplicate
    detection is not implemented."""
    a = [{"id": "a1", "text": "The cat sat on the mat."}]
    b = [{"id": "b1", "text": "The cat sat on the mat"}]
    out = compute_overlap(a=a, b=b, max_records=100)
    assert out["overlap_docs"] == 0


def test_compute_overlap_whitespace_normalization() -> None:
    """Text with different whitespace should still match."""
    a = [{"id": "a1", "text": "  hello   world  "}]
    b = [{"id": "b1", "text": "hello world"}]
    out = compute_overlap(a=a, b=b, max_records=100)
    assert out["overlap_docs"] == 1


def test_compute_overlap_case_normalization() -> None:
    """Text with different casing should still match."""
    a = [{"id": "a1", "text": "Hello World"}]
    b = [{"id": "b1", "text": "HELLO WORLD"}]
    out = compute_overlap(a=a, b=b, max_records=100)
    assert out["overlap_docs"] == 1
