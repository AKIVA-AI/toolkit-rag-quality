"""Near-duplicate and leakage detection over word shingles.

Two measures, each used where it is meaningful:

* **Jaccard similarity** ``|A & B| / |A | B|`` between two documents' shingle
  sets, for near-duplicate documents (:func:`near_duplicates`). Candidate
  pairs come from MinHash signatures with LSH banding; every candidate is then
  verified with the *exact* Jaccard, so a reported pair is never a false
  positive. The only approximation is a small chance of missing a pair,
  reported as ``miss_probability_at_threshold``.
* **Containment** ``|Q & D| / |Q|``: how much of a short eval text (a query or
  an answer) appears inside a corpus document (:func:`containment_leaks`).
  Jaccard is the wrong measure here: a 12-word question copied verbatim into a
  300-word document has a Jaccard similarity of about 0.03 but a containment of
  1.0. Containment is computed exactly with an inverted index.

Text is normalized (Unicode NFKC, lowercase), split into words (runs of
letters and digits, so punctuation is ignored), and turned into overlapping
word n-grams ("shingles"). A text shorter than the shingle size becomes a
single shingle of all its words.
"""

from __future__ import annotations

import hashlib
import logging
import random
import re
import unicodedata
from collections import defaultdict
from collections.abc import Iterable
from typing import Any

logger = logging.getLogger(__name__)

_WORD_RE = re.compile(r"[^\W_]+", re.UNICODE)
_MERSENNE_61 = (1 << 61) - 1
_MAX_HASH = (1 << 64) - 1

DEFAULT_NEAR_DUP_THRESHOLD = 0.8
DEFAULT_NEAR_DUP_SHINGLE = 5
DEFAULT_CONTAINMENT_THRESHOLD = 0.6
DEFAULT_CONTAINMENT_SHINGLE = 3
DEFAULT_NUM_PERM = 128
#: LSH banding is chosen so a pair exactly at the threshold is found with at
#: least this probability (pairs above the threshold are found more often).
MIN_RECALL_AT_THRESHOLD = 0.995


def tokenize(text: str) -> list[str]:
    """Lowercased words (letters and digits) after Unicode NFKC normalization."""
    return _WORD_RE.findall(unicodedata.normalize("NFKC", text).lower())


def shingles(text: str, n: int) -> set[str]:
    """Set of word n-grams. A text with fewer than ``n`` words gives one shingle."""
    if n < 1:
        raise ValueError(f"shingle size must be a positive integer, got {n!r}")
    words = tokenize(text)
    if not words:
        return set()
    if len(words) <= n:
        return {" ".join(words)}
    return {" ".join(words[i : i + n]) for i in range(len(words) - n + 1)}


def jaccard(a: set[Any], b: set[Any]) -> float:
    """Exact Jaccard similarity; 0.0 when both sets are empty."""
    union = len(a | b)
    return len(a & b) / union if union else 0.0


def containment(query: set[Any], doc: set[Any]) -> float:
    """Share of ``query``'s shingles that also occur in ``doc``; 0.0 for an empty query."""
    return len(query & doc) / len(query) if query else 0.0


def _hash64(shingle: str) -> int:
    return int.from_bytes(hashlib.blake2b(shingle.encode("utf-8"), digest_size=8).digest(), "big")


class MinHasher:
    """MinHash signatures with ``num_perm`` universal hash functions.

    ``h_i(x) = (a_i * x + b_i) mod (2**61 - 1)`` over a 64-bit BLAKE2b hash of
    each shingle, with ``a_i, b_i`` drawn from a seeded generator, so
    signatures are identical across runs and machines. The share of equal
    signature positions is an unbiased estimate of the Jaccard similarity
    (Broder, 1997).
    """

    def __init__(self, num_perm: int = DEFAULT_NUM_PERM, seed: int = 1) -> None:
        if num_perm < 1:
            raise ValueError(f"num_perm must be a positive integer, got {num_perm!r}")
        # Seeded PRNG so signatures are reproducible, not for security.
        rng = random.Random(seed)  # nosec B311
        self.num_perm = num_perm
        self._a = [rng.randrange(1, _MERSENNE_61) for _ in range(num_perm)]
        self._b = [rng.randrange(0, _MERSENNE_61) for _ in range(num_perm)]

    def signature(self, items: Iterable[str]) -> list[int]:
        hashes = [_hash64(s) for s in items]
        if not hashes:
            return [_MAX_HASH] * self.num_perm
        p = _MERSENNE_61
        return [min((a * x + b) % p for x in hashes) for a, b in zip(self._a, self._b, strict=True)]

    @staticmethod
    def estimate(sig_a: list[int], sig_b: list[int]) -> float:
        """Estimated Jaccard similarity: the share of equal signature positions."""
        if len(sig_a) != len(sig_b):
            raise ValueError("signatures must have the same length")
        return sum(1 for x, y in zip(sig_a, sig_b, strict=True) if x == y) / len(sig_a)


def candidate_probability(s: float, bands: int, rows: int) -> float:
    """Probability that LSH banding makes a pair with Jaccard ``s`` a candidate:
    ``1 - (1 - s**rows) ** bands`` (Leskovec, Rajaraman and Ullman, *Mining of
    Massive Datasets*, section 3.4)."""
    return 1.0 - (1.0 - s**rows) ** bands


def choose_bands(threshold: float, num_perm: int) -> tuple[int, int]:
    """Pick ``(bands, rows)`` with ``bands * rows == num_perm``: the most rows
    (fewest spurious candidates) that still find a pair at the threshold with
    probability at least ``MIN_RECALL_AT_THRESHOLD``."""
    best = (num_perm, 1)
    for rows in range(1, num_perm + 1):
        if num_perm % rows:
            continue
        bands = num_perm // rows
        if candidate_probability(threshold, bands, rows) >= MIN_RECALL_AT_THRESHOLD:
            best = (bands, rows)
    return best


def _text_of(row: dict[str, Any], fields: tuple[str, ...]) -> str | None:
    parts = [str(row[f]) for f in fields if isinstance(row.get(f), str) and row[f].strip()]
    return " ".join(parts) if parts else None


def row_id(row: dict[str, Any]) -> str | None:
    """A row's id: ``id``, or ``_id`` as in BEIR files."""
    for key in ("id", "_id"):
        if key in row:
            return str(row[key])
    return None


def doc_text(row: dict[str, Any]) -> str | None:
    """A corpus row's text: ``title`` and ``text`` joined (BEIR corpus layout)."""
    return _text_of(row, ("title", "text"))


def _corpus_shingles(
    rows: list[dict[str, Any]], n: int, label: str
) -> tuple[dict[str, set[str]], int]:
    out: dict[str, set[str]] = {}
    skipped = 0
    for row in rows:
        rid = row_id(row)
        text = doc_text(row)
        if rid is None or text is None:
            skipped += 1
            continue
        if rid in out:
            raise ValueError(f"corpus {label}: duplicate document id {rid!r}")
        out[rid] = shingles(text, n)
    if skipped:
        logger.warning("Skipped %d row(s) in corpus %s without an id or text", skipped, label)
    return out, skipped


def near_duplicates(
    *,
    a: list[dict[str, Any]],
    b: list[dict[str, Any]],
    threshold: float = DEFAULT_NEAR_DUP_THRESHOLD,
    shingle: int = DEFAULT_NEAR_DUP_SHINGLE,
    num_perm: int = DEFAULT_NUM_PERM,
    seed: int = 1,
) -> dict[str, Any]:
    """Pairs of documents (one from A, one from B) with Jaccard >= ``threshold``.

    MinHash-LSH proposes candidates; each is kept only if its exact Jaccard
    similarity reaches the threshold. Returns a summary and the pairs sorted
    by similarity (highest first).
    """
    if not 0.0 < threshold <= 1.0:
        raise ValueError(f"threshold must be in (0, 1], got {threshold!r}")
    a_sh, a_skipped = _corpus_shingles(a, shingle, "A")
    b_sh, b_skipped = _corpus_shingles(b, shingle, "B")
    hasher = MinHasher(num_perm=num_perm, seed=seed)
    bands, rows = choose_bands(threshold, num_perm)

    buckets: dict[tuple[int, tuple[int, ...]], list[str]] = defaultdict(list)
    for doc_id, sh in b_sh.items():
        if not sh:
            continue
        sig = hasher.signature(sh)
        for band in range(bands):
            buckets[(band, tuple(sig[band * rows : (band + 1) * rows]))].append(doc_id)

    pairs: list[dict[str, Any]] = []
    candidates = 0
    for a_id, sh in a_sh.items():
        if not sh:
            continue
        sig = hasher.signature(sh)
        found: set[str] = set()
        for band in range(bands):
            found.update(buckets.get((band, tuple(sig[band * rows : (band + 1) * rows])), ()))
        candidates += len(found)
        for b_id in sorted(found):
            j = jaccard(sh, b_sh[b_id])
            if j >= threshold:
                pairs.append({"a_id": a_id, "b_id": b_id, "jaccard": j})

    pairs.sort(key=lambda p: (-p["jaccard"], p["a_id"], p["b_id"]))
    a_matched = {p["a_id"] for p in pairs}
    summary = {
        "method": "minhash_lsh_exact_jaccard",
        "a_docs": len(a_sh),
        "b_docs": len(b_sh),
        "a_skipped_rows": a_skipped,
        "b_skipped_rows": b_skipped,
        "pairs": len(pairs),
        "a_docs_with_match": len(a_matched),
        "overlap_rate": len(a_matched) / len(a_sh) if a_sh else 0.0,
        "threshold": threshold,
        "shingle": shingle,
        "num_perm": num_perm,
        "bands": bands,
        "rows": rows,
        "candidates_checked": candidates,
        "miss_probability_at_threshold": 1.0 - candidate_probability(threshold, bands, rows),
    }
    return {"summary": summary, "pairs": pairs}


def containment_leaks(
    *,
    items: list[dict[str, Any]],
    corpus: list[dict[str, Any]],
    fields: tuple[str, ...] = ("query", "question", "answer", "text"),
    threshold: float = DEFAULT_CONTAINMENT_THRESHOLD,
    shingle: int = DEFAULT_CONTAINMENT_SHINGLE,
) -> dict[str, Any]:
    """Eval texts (each listed field of each item) contained in a corpus document.

    For every text, finds the corpus document with the highest containment
    (exact, via an inverted index of shingles). A text leaks when that
    containment reaches ``threshold``.
    """
    if not 0.0 < threshold <= 1.0:
        raise ValueError(f"threshold must be in (0, 1], got {threshold!r}")
    docs, corpus_skipped = _corpus_shingles(corpus, shingle, "corpus")
    index: dict[str, list[str]] = defaultdict(list)
    for doc_id, sh in docs.items():
        for s in sh:
            index[s].append(doc_id)

    leaks: list[dict[str, Any]] = []
    texts = 0
    skipped_items = 0
    leaked_items: set[str] = set()
    for row in items:
        rid = row_id(row)
        present = [f for f in fields if isinstance(row.get(f), str) and row[f].strip()]
        if rid is None or not present:
            skipped_items += 1
            continue
        for f in present:
            q = shingles(str(row[f]), shingle)
            if not q:
                continue
            texts += 1
            counts: dict[str, int] = defaultdict(int)
            for s in q:
                for doc_id in index.get(s, ()):
                    counts[doc_id] += 1
            if not counts:
                continue
            best_doc = min(counts, key=lambda d: (-counts[d], d))
            score = counts[best_doc] / len(q)
            if score >= threshold:
                leaked_items.add(rid)
                leaks.append(
                    {
                        "item_id": rid,
                        "field": f,
                        "doc_id": best_doc,
                        "containment": score,
                        "shared_shingles": counts[best_doc],
                        "item_shingles": len(q),
                    }
                )
    if skipped_items:
        logger.warning("Skipped %d eval item(s) without an id or any of %s", skipped_items, fields)
    leaks.sort(key=lambda x: (-x["containment"], x["item_id"], x["field"]))
    summary = {
        "method": "exact_containment",
        "items": len(items) - skipped_items,
        "skipped_items": skipped_items,
        "texts_checked": texts,
        "corpus_docs": len(docs),
        "corpus_skipped_rows": corpus_skipped,
        "leaked_items": len(leaked_items),
        "leaked_texts": len(leaks),
        "threshold": threshold,
        "shingle": shingle,
        "fields": list(fields),
    }
    return {"summary": summary, "leaks": leaks}
