"""Near-duplicate (MinHash-LSH, exact Jaccard) and containment leakage checks.

References:

* Jaccard similarity and the LSH banding S-curve ``1 - (1 - s**r) ** b``:
  Leskovec, Rajaraman and Ullman, *Mining of Massive Datasets* (3rd ed.),
  Example 3.1 (SIM = 3/8) and Figure 3.9 (b = 20, r = 5).
* MinHash as an unbiased Jaccard estimator: Broder, "On the resemblance and
  containment of documents" (1997).
* Near-duplicate recall is checked against exhaustive exact Jaccard over all
  pairs (the ground truth), not against another approximation.
"""

from __future__ import annotations

import json
import random
from pathlib import Path

import pytest

from toolkit_rag_quality.cli import main
from toolkit_rag_quality.leakage import (
    MinHasher,
    candidate_probability,
    choose_bands,
    containment,
    containment_leaks,
    jaccard,
    near_duplicates,
    shingles,
    tokenize,
)


def test_tokenize_ignores_case_and_punctuation() -> None:
    assert tokenize("The cat sat on the mat.") == ["the", "cat", "sat", "on", "the", "mat"]
    assert tokenize("Ｆｕｌｌ-width, NFKC!") == ["full", "width", "nfkc"]


def test_shingles_worked_example() -> None:
    assert shingles("a b c a b", 2) == {"a b", "b c", "c a"}
    assert shingles("two words", 5) == {"two words"}  # shorter than n: one shingle
    assert shingles("...", 3) == set()


def test_jaccard_mmds_example_3_1() -> None:
    # Three elements in the intersection, eight in the union: SIM = 3/8.
    s = {"a", "c", "d", "x"}
    t = {"a", "c", "d", "b", "e", "f", "g"}
    assert len(s & t) == 3 and len(s | t) == 8
    assert jaccard(s, t) == 3 / 8


# Figure 3.9 of Mining of Massive Datasets: b = 20 bands of r = 5 rows.
MMDS_FIG_3_9 = [(0.2, 0.006), (0.3, 0.047), (0.4, 0.186), (0.5, 0.470), (0.6, 0.802), (0.7, 0.975)]


@pytest.mark.parametrize(("s", "expected"), MMDS_FIG_3_9)
def test_lsh_s_curve_matches_mmds_figure_3_9(s: float, expected: float) -> None:
    assert round(candidate_probability(s, 20, 5), 3) == expected


def test_lsh_s_curve_at_0_8_matches_mmds_example() -> None:
    assert abs(candidate_probability(0.8, 20, 5) - 0.99965) < 1e-5


def test_choose_bands_meets_the_recall_target() -> None:
    bands, rows = choose_bands(0.8, 128)
    assert (bands, rows) == (32, 4)
    assert candidate_probability(0.8, bands, rows) >= 0.995
    bands, rows = choose_bands(0.5, 128)
    assert bands * rows == 128 and candidate_probability(0.5, bands, rows) >= 0.995


def test_minhash_estimates_jaccard_within_sampling_error() -> None:
    hasher = MinHasher(num_perm=256, seed=3)
    rng = random.Random(0)
    errors = []
    for target in (0.2, 0.5, 0.8):
        for _ in range(10):
            universe = [f"w{rng.random()}" for _ in range(400)]
            k = int(len(universe) * target)  # |A & B| for J = target (union is 400)
            a = set(universe[: 200 + k // 2])
            b = set(universe[200 - k // 2 : 400])
            exact = jaccard(a, b)
            est = MinHasher.estimate(hasher.signature(a), hasher.signature(b))
            se = (exact * (1 - exact) / 256) ** 0.5
            assert abs(est - exact) <= 4 * se + 1e-9
            errors.append(est - exact)
    # Unbiased: the mean error over 30 pairs is close to zero.
    assert abs(sum(errors) / len(errors)) < 0.02


def test_signatures_are_reproducible() -> None:
    sh = shingles("the quick brown fox jumps over the lazy dog", 3)
    assert MinHasher(seed=5).signature(sh) == MinHasher(seed=5).signature(sh)
    assert MinHasher(seed=5).signature(sh) != MinHasher(seed=6).signature(sh)


def _corpus(seed: int = 11) -> tuple[list[dict], list[dict]]:
    rng = random.Random(seed)
    vocab = [f"w{i}" for i in range(3000)]
    a = [{"id": f"a{i}", "text": " ".join(rng.choices(vocab, k=60))} for i in range(150)]
    b = [{"id": f"b{i}", "text": " ".join(rng.choices(vocab, k=60))} for i in range(150)]
    # Plant near-copies of 40 A documents in B with 0..8 word substitutions.
    for i in range(40):
        words = a[i]["text"].split()
        for _ in range(i % 9):
            words[rng.randrange(len(words))] = rng.choice(vocab)
        b.append({"id": f"copy{i}", "text": " ".join(words)})
    return a, b


def test_near_duplicates_equal_exhaustive_exact_jaccard() -> None:
    a, b = _corpus()
    threshold, n = 0.5, 5
    found = near_duplicates(a=a, b=b, threshold=threshold, shingle=n)
    truth = set()
    for x in a:
        sx = shingles(x["text"], n)
        for y in b:
            if jaccard(sx, shingles(y["text"], n)) >= threshold:
                truth.add((x["id"], y["id"]))
    assert truth, "the fixture must contain pairs above the threshold"
    assert {(p["a_id"], p["b_id"]) for p in found["pairs"]} == truth
    # Every reported similarity is the exact Jaccard.
    for p in found["pairs"]:
        sa = shingles(next(r["text"] for r in a if r["id"] == p["a_id"]), n)
        sb = shingles(next(r["text"] for r in b if r["id"] == p["b_id"]), n)
        assert p["jaccard"] == jaccard(sa, sb)
    s = found["summary"]
    assert s["pairs"] == len(truth)
    assert s["miss_probability_at_threshold"] <= 0.005


def test_near_duplicates_match_punctuation_and_case_variants() -> None:
    result = near_duplicates(
        a=[{"id": "a", "text": "The cat sat on the mat."}],
        b=[{"id": "b", "text": "the cat sat on the mat"}],
        threshold=0.9,
    )
    assert result["pairs"] == [{"a_id": "a", "b_id": "b", "jaccard": 1.0}]


def test_near_duplicates_reject_bad_input() -> None:
    with pytest.raises(ValueError):
        near_duplicates(a=[], b=[], threshold=0.0)
    with pytest.raises(ValueError, match="duplicate"):
        near_duplicates(a=[{"id": "x", "text": "a"}, {"id": "x", "text": "b"}], b=[])


QUESTION = "which enzyme converts angiotensin one into angiotensin two in the human lungs"
DOC = (
    "Background text about blood pressure regulation. " * 20
    + QUESTION
    + ". More unrelated text follows here about renal physiology. " * 10
)


def test_containment_is_the_right_measure_for_short_texts() -> None:
    q, d = shingles(QUESTION, 3), shingles(DOC, 3)
    assert containment(q, d) == 1.0
    assert jaccard(q, d) < 0.5  # Jaccard would hide a verbatim copy


@pytest.mark.parametrize(
    ("question", "expected", "leaks"),
    [
        (QUESTION, 1.0, True),  # verbatim
        (QUESTION.upper() + "?", 1.0, True),  # case and punctuation
        # One word substituted mid-sentence: 3 of 10 trigrams change.
        (QUESTION.replace("into", "to"), 0.7, True),
        # Two substitutions far apart: 5 of 10 trigrams change.
        (QUESTION.replace("enzyme", "protein").replace("in the", "of the"), 0.5, False),
        ("completely different question about quantum chromodynamics", 0.0, False),
    ],
)
def test_containment_thresholds_worked_examples(
    question: str, expected: float, leaks: bool
) -> None:
    result = containment_leaks(
        items=[{"id": "q1", "query": question}], corpus=[{"id": "d1", "text": DOC}]
    )
    assert result["summary"]["threshold"] == 0.6
    q = shingles(question, 3)
    assert containment(q, shingles(DOC, 3)) == pytest.approx(expected)
    assert (result["summary"]["leaked_items"] == 1) is leaks
    if leaks:
        assert result["leaks"][0]["doc_id"] == "d1"
        assert result["leaks"][0]["containment"] == pytest.approx(expected)


def test_containment_uses_beir_ids_titles_and_all_fields() -> None:
    corpus = [{"_id": "d9", "title": "Angiotensin", "text": QUESTION}]
    items = [{"_id": "7", "text": "unrelated words here", "answer": QUESTION}]
    result = containment_leaks(items=items, corpus=corpus)
    assert result["leaks"][0]["item_id"] == "7"
    assert result["leaks"][0]["field"] == "answer"
    assert result["summary"]["texts_checked"] == 2


# --------------------------------------------------------------------- CLI


def _jsonl(path: Path, rows: list[dict]) -> Path:
    path.write_text("".join(json.dumps(r) + "\n" for r in rows), encoding="utf-8")
    return path


def test_cli_leakage_gate(tmp_path: Path) -> None:
    corpus = _jsonl(tmp_path / "corpus.jsonl", [{"_id": "d1", "title": "t", "text": DOC}])
    items = _jsonl(
        tmp_path / "items.jsonl",
        [{"id": "q1", "query": QUESTION}, {"id": "q2", "query": "nothing like the corpus at all"}],
    )
    out = tmp_path / "leak.json"
    args = ["leakage", "--corpus", str(corpus), "--items", str(items), "--out", str(out)]
    assert main(args) == 4
    env = json.loads(out.read_text(encoding="utf-8"))
    pred = env["predicate"]
    assert (pred["kind"], pred["verdict"], pred["exit_code"]) == ("rag.leakage", "fail", 4)
    assert pred["summary"]["leaked_items"] == 1
    assert pred["details"]["leaks"][0]["item_id"] == "q1"
    assert main([*args, "--max-leaks", "1"]) == 0
    assert main([*args, "--threshold", "1.5"]) == 2


def test_cli_leakage_rejects_oversized_input(tmp_path: Path) -> None:
    corpus = _jsonl(tmp_path / "c.jsonl", [{"id": f"d{i}", "text": "x"} for i in range(3)])
    items = _jsonl(tmp_path / "i.jsonl", [{"id": "q", "query": "x"}])
    rc = main(["leakage", "--corpus", str(corpus), "--items", str(items), "--max-records", "2"])
    assert rc == 2


def test_cli_overlap_minhash(tmp_path: Path) -> None:
    a, b = _corpus()
    fa, fb = _jsonl(tmp_path / "a.jsonl", a), _jsonl(tmp_path / "b.jsonl", b)
    out = tmp_path / "near.json"
    rc = main(
        ["overlap", "--a", str(fa), "--b", str(fb), "--method", "minhash",
         "--threshold", "0.5", "--out", str(out)]
    )  # fmt: skip
    assert rc == 0
    pred = json.loads(out.read_text(encoding="utf-8"))["predicate"]
    assert pred["summary"]["method"] == "minhash_lsh_exact_jaccard"
    assert pred["summary"]["shingle"] == 5
    assert pred["summary"]["pairs"] == len(pred["details"]["pairs"]) > 0
