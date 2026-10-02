"""A small pure-Python BM25 retriever over a BEIR corpus, for the README example.

Not a production retriever: no stemming, a short stopword list, everything in
memory. It exists so the 5-minute example needs nothing beyond this package.

Usage with ``toolkit-rag run-retriever`` (run from the repository root)::

    toolkit-rag run-retriever --retriever "examples.bm25:baseline()" ...
    toolkit-rag run-retriever --retriever "examples.bm25:candidate()" ...

The corpus is read from ``$BEIR_DIR/corpus.jsonl`` (default ``scifact``).
``baseline()`` uses the common BM25 setting k1 = 0.9, b = 0.4 over title and
text; ``candidate()`` drops the title, a plausible-looking change whose effect
the regression gate then measures.
"""

from __future__ import annotations

import json
import math
import os
import re
from collections import Counter, defaultdict
from collections.abc import Callable
from pathlib import Path

_WORD = re.compile(r"[a-z0-9]+")
_STOP = frozenset(
    "a an and are as at be by for from has have in is it its of on or that the this to was "
    "were which with we our not no".split()
)


def _tokens(text: str) -> list[str]:
    return [w for w in _WORD.findall(text.lower()) if w not in _STOP]


class BM25:
    def __init__(self, docs: dict[str, str], k1: float = 0.9, b: float = 0.4) -> None:
        self.k1, self.b = k1, b
        self.postings: dict[str, list[tuple[str, int]]] = defaultdict(list)
        self.length: dict[str, int] = {}
        for doc_id, text in docs.items():
            tokens = _tokens(text)
            self.length[doc_id] = len(tokens)
            for term, tf in Counter(tokens).items():
                self.postings[term].append((doc_id, tf))
        n = len(docs)
        self.avg_len = sum(self.length.values()) / max(n, 1)
        self.idf = {
            t: math.log(1 + (n - len(p) + 0.5) / (len(p) + 0.5)) for t, p in self.postings.items()
        }

    def __call__(self, query: str, k: int = 100) -> list[str]:
        scores: dict[str, float] = defaultdict(float)
        for term in set(_tokens(query)):
            idf = self.idf.get(term)
            if idf is None:
                continue
            for doc_id, tf in self.postings[term]:
                norm = self.k1 * (1 - self.b + self.b * self.length[doc_id] / self.avg_len)
                scores[doc_id] += idf * tf * (self.k1 + 1) / (tf + norm)
        return sorted(scores, key=lambda d: (-scores[d], d))[:k]


def _corpus(with_title: bool) -> dict[str, str]:
    path = Path(os.environ.get("BEIR_DIR", "scifact")) / "corpus.jsonl"
    docs: dict[str, str] = {}
    with path.open(encoding="utf-8") as fh:
        for line in fh:
            row = json.loads(line)
            title = row.get("title", "") if with_title else ""
            docs[str(row["_id"])] = f"{title} {row.get('text', '')}"
    return docs


def baseline() -> Callable[[str], list[str]]:
    return BM25(_corpus(with_title=True))


def candidate() -> Callable[[str], list[str]]:
    return BM25(_corpus(with_title=False))
