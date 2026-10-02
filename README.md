# Toolkit RAG Quality

[![PyPI](https://img.shields.io/pypi/v/toolkit-rag-quality.svg)](https://pypi.org/project/toolkit-rag-quality/)
[![Python versions](https://img.shields.io/pypi/pyversions/toolkit-rag-quality.svg)](https://pypi.org/project/toolkit-rag-quality/)
[![License](https://img.shields.io/badge/license-Apache--2.0-blue.svg)](LICENSE)

**Retrieval regression testing in CI.** `toolkit-rag` scores a retriever's ranked results with metrics that match trec_eval exactly, tells you which queries got worse and whether the change is statistically significant, fails the build when it regresses beyond budget, and checks that eval queries and answers have not leaked into the corpus. It is deterministic, makes no model calls and has no runtime dependencies (LangChain and LlamaIndex adapters are optional extras).

It complements, rather than replaces, two good tools: [Ragas](https://docs.ragas.io/) judges *generation* quality (faithfulness, answer relevance) with LLMs, and [ranx](https://github.com/AmenRa/ranx) is a research library with many more IR metrics, fusion and multi-system statistics. `toolkit-rag` is the CI piece: a gate with a stable report format, per-query diffs and a GitHub Action.

## Capabilities

| Capability | Status | Notes |
|---|---|---|
| Retrieval metrics at k: hit rate, recall, precision, MRR, nDCG, MAP (`score`) | Working | Equal to trec_eval: hard-coded pytrec_eval reference values in `tests/test_trec_reference.py` and `tests/test_graded_reference.py`; on BEIR SciFact all six metrics match trec_eval to 12 decimals. |
| Graded relevance and `--relevance-level` | Working | Integer grades; nDCG uses linear gains, as trec_eval does. Checked at relevance levels 1 and 2. |
| TREC qrels/run and BEIR qrels import, TREC and JSONL export (`score`, `convert`) | Working | trec_eval tie-breaking for runs; formats auto-detected. |
| Regression gate (`compare`) | Working | Per-metric budgets for all six metrics; fails when the reports use a different k, relevance level or query set. |
| Per-query diff (`compare`) | Working | Which queries got worse or better, per metric, with the most regressed listed. |
| Paired significance tests (`compare --alpha`) | Working | Randomization test (exact up to 16 queries) and paired t-test, checked against SciPy. |
| GitHub Action (`action.yml`) | Working | Composite action for the regression gate, with a step summary; tested end to end in CI. |
| Eval leakage check (`leakage`) | Working | Exact containment of eval queries/answers in corpus documents; exits 4 above `--max-leaks`. |
| Near-duplicate documents (`overlap --method minhash`) | Working | MinHash-LSH candidates verified with exact Jaccard over word shingles; the miss probability at the threshold is reported. Checked against exhaustive exact Jaccard. Pure Python: a 5,000 x 5,000 document comparison takes about a minute. |
| Exact-duplicate overlap between corpora (`overlap`) | Working | Exact match after lowercasing and whitespace collapsing, via SHA-256 fingerprints. |
| Retriever adapters (`run-retriever`) | Working | LangChain and LlamaIndex retrievers (optional extras) or any callable, to a TREC or JSONL run. |
| Report envelope (default JSON output) | Working | Every report is an in-toto Statement v1 in canonical JSON, with SHA-256 digests of the inputs. See [Report format](#report-format). |
| Report validation (`validate-report`) | Working | Checks an envelope against the v1 rules (including verdict/exit-code consistency) and, for `rag.score`, that every headline metric is present. |
| Semantic (embedding) similarity for paraphrase leakage | Planned | Not implemented: `leakage` finds copied text, not reworded text. |
| Generation-side metrics (faithfulness, answer relevance) | Not planned | Use Ragas or a similar LLM-judged tool. |

## Install

Python 3.10 or newer is required.

```bash
pip install toolkit-rag-quality
pip install "toolkit-rag-quality[langchain]"     # LangChain retriever adapter
pip install "toolkit-rag-quality[llamaindex]"    # LlamaIndex retriever adapter
toolkit-rag --version
```

To work on the code, see [Development](#development).

## 5-minute example: BEIR SciFact

This compares two configurations of a small BM25 retriever on the [BEIR](https://github.com/beir-cellar/beir) SciFact test set (300 queries, 5,183 abstracts, 2.8 MB download). The retriever is `examples/bm25.py`, a pure-Python BM25 kept small for the example. The candidate drops document titles from the index, a plausible-looking change. Run it from the root of a clone of this repository, so that `examples.bm25` can be imported:

```bash
git clone https://github.com/AKIVA-AI/toolkit-rag-quality.git
cd toolkit-rag-quality

curl -LO https://public.ukp.informatik.tu-darmstadt.de/thakur/BEIR/datasets/scifact.zip
unzip -q scifact.zip

# 1. Produce a run file for each configuration (about 2 seconds each).
toolkit-rag run-retriever --retriever "examples.bm25:baseline()" --queries scifact/queries.jsonl \
  --qrels scifact/qrels/test.tsv --k 100 --out baseline.trec --tag bm25-title
toolkit-rag run-retriever --retriever "examples.bm25:candidate()" --queries scifact/queries.jsonl \
  --qrels scifact/qrels/test.tsv --k 100 --out candidate.trec --tag bm25-notitle

# 2. Score both at k = 10 against the BEIR qrels.
toolkit-rag score --queries scifact/qrels/test.tsv --retrieved baseline.trec --k 10 --out baseline.json --format table
toolkit-rag score --queries scifact/qrels/test.tsv --retrieved candidate.trec --k 10 --out candidate.json --format table

# 3. Gate the candidate: 2% budget, fail only on significant drops.
toolkit-rag compare --baseline baseline.json --candidate candidate.json --alpha 0.05 --format markdown

# 4. Check whether any SciFact claim is copied into the corpus.
toolkit-rag leakage --corpus scifact/corpus.jsonl --items scifact/queries.jsonl --field text --format table
```

Step 2 gives the baseline nDCG@10 = 0.6598 (the BEIR paper reports 0.665 for its Elasticsearch BM25 baseline). Step 3 exits 4 and prints:

| metric | baseline | candidate | change % | budget % | p-value | worse / better | result |
|---|---|---|---|---|---|---|---|
| recall_at_k | 0.7768 | 0.7629 | -1.79 | 2.00 | 0.1014 | 7 / 1 | pass |
| precision_at_k | 0.0853 | 0.0833 | -2.34 | 2.00 | 0.0762 | 7 / 1 | pass (not significant) |
| ndcg_at_k | 0.6598 | 0.6427 | -2.59 | 2.00 | 0.0056 | 30 / 16 | **FAIL** |
| mrr_at_k | 0.6295 | 0.6128 | -2.64 | 2.00 | 0.0186 | 26 / 14 | **FAIL** |
| map_at_k | 0.6169 | 0.5984 | -2.99 | 2.00 | 0.0072 | 30 / 16 | **FAIL** |
| hit_rate_at_k | 0.8000 | 0.7867 | -1.67 | 2.00 | 0.2246 | 5 / 1 | pass |

followed by the most regressed queries (query `1194` drops from nDCG@10 = 1.0 to 0). Dropping titles costs 2.6% nDCG@10, and 30 queries got worse against 16 that improved, which the randomization test finds significant (p = 0.006). Precision also dropped past its budget, but not significantly, so `--alpha` lets it pass. Step 4 exits 4: 18 of the 1,109 SciFact claims (train and test) share at least 60% of their word 3-grams with one abstract, two of them verbatim. That is expected for a fact-checking dataset whose claims were written from those abstracts, and it shows what the check reports; for your own eval set, a leak usually means the question was copied into the knowledge base.

The numbers above were produced with this repository's code in a clean Python 3.12 container.

## Usage

Score retrieval results:

```bash
toolkit-rag score --queries queries.jsonl --retrieved retrieved.jsonl --k 5 --out report.json
```

Compare a candidate report to a baseline (CI gating):

```bash
toolkit-rag compare --baseline baseline.json --candidate report.json \
  --max-recall-regression-pct 2.0 --max-regression-pct 5.0 \
  --budget ndcg=1 --budget hit_rate=off --alpha 0.05 --format markdown
```

What the gate checks:

- **Budgets.** Each metric's mean may drop by at most its budget, in percent of the baseline. `--max-recall-regression-pct` (default 2) covers recall; `--max-regression-pct` covers the other five metrics and defaults to the recall budget. `--budget METRIC=PCT` (repeatable) overrides either for one metric, and `--budget METRIC=off` reports a metric without gating it. Metric names: `recall`, `precision`, `ndcg`, `mrr`, `map`, `hit_rate` (or the `*_at_k` summary keys).
- **Comparability.** The gate fails if the reports use a different `k`, a different relevance level, or a different query set.
- **Per-query diff.** For every query and metric, the report lists baseline, candidate and delta (`details.per_query_diff`), counts the queries that got worse, better or stayed the same (`summary.per_query`), and names the most regressed queries by `--primary-metric` (default nDCG; `--top`, default 10).
- **Significance.** Each metric gets a two-sided paired test on its per-query scores: a randomization (sign-flip) test by default, or `--test t-test`. With 16 queries or fewer, the randomization test enumerates every sign pattern (exact); above that it draws `--permutations` (default 10,000) patterns from a fixed `--seed`, so results are reproducible. Both tests are checked against SciPy (`scipy.stats.permutation_test` and `scipy.stats.ttest_rel`) in `tests/test_stats.py`.
- **`--alpha`.** Without it, any drop over budget fails. With it, a metric over budget fails only if its drop is also significant (p < alpha), so noise on a small query set does not break the build. With fewer than two queries there is no p-value, and an over-budget drop fails. `--alpha` needs per-query rows in both reports.

`--format markdown` prints a table of metrics (change, budget, p-value, worse/better counts) and the most regressed queries, suitable for a CI step summary.

Produce a run file from your own retriever (LangChain, LlamaIndex, or any Python callable):

```bash
pip install "toolkit-rag-quality[langchain]"   # or "toolkit-rag-quality[llamaindex]"; a plain callable needs neither
toolkit-rag run-retriever --retriever my_pipeline:build_retriever() \
  --queries queries.jsonl --qrels qrels.trec --k 100 --out run.trec --tag my-retriever
```

- `--retriever module:attr` names a retriever object; `module:factory()` calls a zero-argument factory. The current directory is on the import path. This imports and runs that code, so only point it at code you trust.
- LangChain retrievers are called with `invoke(query)`, LlamaIndex retrievers with `retrieve(query)`, and a callable with `f(query)` (returning doc ids). The framework is detected from the class, or set with `--framework`.
- Document ids come from `Document.id` (LangChain) or `node.node_id` (LlamaIndex), or from a metadata field with `--id-key doc_id`. A result without an id is an error.
- Each ranking is de-duplicated and cut to `--k`. `--qrels` limits the run to judged queries. `--to jsonl` writes a JSONL run instead of TREC.
- The adapters are tested against real `langchain-core` and `llama-index-core` in CI (`tests/test_adapters.py`).

Find duplicate documents between two corpora (for example, to check test/train contamination):

```bash
toolkit-rag overlap --a corpus_a.jsonl --b corpus_b.jsonl --out overlap.json                 # exact
toolkit-rag overlap --a corpus_a.jsonl --b corpus_b.jsonl --method minhash --threshold 0.8   # near-duplicate
```

- `--method exact` (default) matches documents whose text is identical after lowercasing and collapsing whitespace.
- `--method minhash` matches documents whose word 5-gram shingles (`--shingle`) have a Jaccard similarity of at least `--threshold` (default 0.8, the setting used for training-data deduplication by Lee et al., 2022, "Deduplicating Training Data Makes Language Models Better"). Text is normalized (Unicode NFKC, lowercase, punctuation dropped) first. MinHash-LSH only proposes candidate pairs; every reported pair is verified with the exact Jaccard similarity, so there are no false positives. A pair can be missed: the LSH banding is chosen so a pair exactly at the threshold is found with probability at least 99.5%, and the report states the actual miss probability (`miss_probability_at_threshold`). The pairs are in `details.pairs`.

Check whether eval queries or answers appear in the corpus:

```bash
toolkit-rag leakage --corpus corpus.jsonl --items eval.jsonl --field query --field answer --out leakage.json
```

`leakage` measures **containment**: the share of an eval text's word 3-grams that also occur in one corpus document, computed exactly with an inverted index. Jaccard similarity is the wrong measure here: a 12-word question copied verbatim into a 300-word document has a Jaccard similarity of about 0.03 but a containment of 1.0. An item leaks when any of its fields reaches `--threshold` (default 0.6). What that default catches, from `tests/test_leakage.py`, for a 12-word question:

| Eval text vs the corpus document | Containment | Flagged at 0.6 |
|---|---|---|
| Verbatim copy, or a case/punctuation variant | 1.0 | yes |
| One word substituted | 0.7 | yes |
| Two words substituted, far apart | 0.5 | no |
| Unrelated question | 0.0 | no |

Lower the threshold to catch paraphrase-level copies (and expect more false positives on templated text); raise it to flag only near-verbatim copies. Paraphrases with different wording are not detected: that needs embedding similarity, which is not implemented. `leakage` exits 4 when more items leak than `--max-leaks` (default 0). Items and corpus rows may use BEIR field names (`_id`, `title`, `text`).

A corpus or item file with more rows than `--max-records` (default 50,000) is rejected, not truncated.

Check a report's shape:

```bash
toolkit-rag validate-report --report report.json
```

Every command prints its report as JSON by default; `--format table` or `--format markdown` prints a human-readable summary instead. `--out` always writes the JSON report. Global flags: `--verbose` and `--log-format text|json`.

## GitHub Action

`action.yml` at the repository root is a composite action that runs the regression gate and writes the Markdown summary to the job's step summary. Produce the two score reports in earlier steps (for example, the baseline from `main` and the candidate from the pull request), then:

```yaml
- uses: AKIVA-AI/toolkit-rag-quality@v1.0.0
  with:
    baseline: reports/baseline.json
    candidate: reports/candidate.json
    max-recall-regression-pct: "2.0"
    budgets: |
      ndcg=1
      hit_rate=off
    alpha: "0.05"          # optional: fail only on significant drops
```

| Input | Default | Meaning |
|---|---|---|
| `baseline`, `candidate` | required | Score reports from `toolkit-rag score --out` |
| `max-recall-regression-pct` | `2.0` | Recall budget, in percent of the baseline |
| `max-regression-pct` | recall budget | Budget for the other metrics |
| `budgets` | none | One `METRIC=PCT` or `METRIC=off` per line |
| `alpha` | none | Significance level for `--alpha` |
| `test` | `permutation` | `permutation` or `t-test` |
| `report` | `rag-compare.json` | Where the compare report is written |
| `fail-on-regression` | `true` | Fail the step when the gate does not pass |
| `python-version` | `3.12` | Empty string: use the runner's Python |

Outputs: `verdict` (`pass`, `fail` or `error`), `exit-code` and `report`. The step fails when the gate does not pass. GitHub drops a composite action's outputs when the action fails, so to read `verdict` in a later step set `fail-on-regression: "false"` and decide there. The action installs the package from the action's own checkout, so the gate always matches the pinned version. CI runs the action end to end on fixtures (the `action` job in `.github/workflows/ci.yml`).

With few queries a real drop may not reach significance: in that CI job, 4 of 8 queries losing their only relevant document gives p = 0.125, so `alpha: 0.05` lets it pass. Use `alpha` to absorb noise on large query sets, not to gate small ones.

## Metric definitions

All metrics use the cutoff `k` and follow trec_eval (`P_k`, `recall_k`, `ndcg_cut_k`, `map_cut_k`, `success_k`, and `recip_rank` over the top k). Judgments can be binary or graded (integer grades). A document is **relevant** when its grade is at least the relevance level (`--relevance-level`, default 1, like `trec_eval -l`).

- **precision@k** = relevant documents in the top k, divided by k (not by the number of documents returned).
- **recall@k** = relevant documents in the top k, divided by the number of relevant documents.
- **nDCG@k** uses the grade as a linear gain (grade 1 for `relevant_ids`) and the discount `1/log2(rank + 1)`. The ideal DCG sorts all positive grades in the judgments and keeps the top k. As in trec_eval, nDCG ignores the relevance level, and zero or negative grades give no gain.
- **MAP@k** is the sum of precision at each relevant rank within k, divided by the number of relevant documents.
- **MRR@k** is the reciprocal rank of the first relevant document within k, or 0.
- **hit rate@k** is 1 if any relevant document appears in the top k.

These definitions are checked against values computed with trec_eval (through `pytrec_eval`): binary cases in `tests/test_trec_reference.py`, graded cases at relevance levels 1 and 2 in `tests/test_graded_reference.py`.

Input handling:

- Repeated ids in a retrieved list are removed before the cutoff; the first occurrence wins.
- A query with no judgments at all (for example an empty `relevant_ids`) is unjudged. It is excluded from the averages, counted in `unjudged_queries`, and logged.
- A judged query with no document at or above the relevance level is scored (0 on everything except possibly nDCG) and averaged in, as trec_eval does. It is counted in `queries_without_relevant`.
- A judged query with no retrieved row scores 0 on every metric and is counted in `queries_without_results`.
- Run entries for queries that have no judgments are ignored and counted in `unscored_run_queries`.
- Rows without an `id` are counted (`skipped_query_rows`, `skipped_retrieved_rows`) and logged. A repeated query id, a row with both `relevant_ids` and `relevance`, or a non-integer grade is an error.
- `k` and `--relevance-level` must be positive integers. Scoring with no judged queries is an error.

## Data formats

`score --queries` takes relevance judgments and `score --retrieved` takes ranked results. The format is detected from the first line, or set with `--queries-format jsonl|trec|beir` and `--retrieved-format jsonl|trec`.

Queries JSONL (one object per line), binary or graded:

```json
{"id":"q1","query":"...","relevant_ids":["doc-1","doc-9"]}
{"id":"q2","relevance":{"doc-3":2,"doc-4":1,"doc-7":0}}
```

Retrieved JSONL, ranked best first:

```json
{"id":"q1","retrieved_ids":["doc-9","doc-2","doc-1"]}
```

TREC qrels (`qid iter docid grade`) and TREC runs (`qid Q0 docid rank score tag`). As in trec_eval, a run is ranked by score (highest first) with ties broken by doc id in descending order; the rank column is ignored. A document listed twice for one query is an error.

BEIR qrels: the tab-separated `qrels/<split>.tsv` file of a BEIR dataset (`query-id`, `corpus-id`, `score` header).

Convert between formats:

```bash
toolkit-rag convert qrels --in scifact/qrels/test.tsv --to trec --out test.qrels
toolkit-rag convert run --in run.trec --to jsonl --out run.jsonl
toolkit-rag convert run --in run.jsonl --to trec --tag my-retriever --out run.trec
```

A JSONL run carries ranks only, so a TREC export writes the score `len(ranking) - rank + 1`: strictly decreasing, so trec_eval reproduces the list order.

Corpora JSONL:

```json
{"id":"doc-1","text":"..."}
```

## Report format

`score`, `compare`, `overlap` and `leakage` write their result as a **report envelope**: an [in-toto Statement v1](https://github.com/in-toto/attestation/blob/main/spec/v1/statement.md), the attestation format used by SLSA and Sigstore. The full convention is in [docs/report-envelope.md](docs/report-envelope.md) and the JSON Schema is [schemas/report-envelope.v1.json](schemas/report-envelope.v1.json).

```json
{
  "_type": "https://in-toto.io/Statement/v1",
  "subject": [{"name": "run.jsonl", "digest": {"sha256": "..."}}],
  "predicateType": "https://github.com/AKIVA-AI/toolkit-rag-quality/report/v1",
  "predicate": {
    "tool": {"name": "toolkit-rag-quality", "version": "..."},
    "kind": "rag.score",
    "created_at": "2026-09-26T18:00:00Z",
    "verdict": "pass",
    "exit_code": 0,
    "inputs": [{"name": "queries.jsonl", "digest": {"sha256": "..."}}, {"name": "run.jsonl", "digest": {"sha256": "..."}}],
    "summary": {"k": 5, "queries": 300, "recall_at_k": 0.71, "...": "..."},
    "details": {"per_query": [{"id": "q1", "recall": 1.0, "...": "..."}]}
  }
}
```

- The file is canonical JSON (sorted keys, no insignificant whitespace, trailing newline), so its SHA-256 is stable. Set `SOURCE_DATE_EPOCH` to pin `created_at` and get byte-identical reports from the same inputs.
- `verdict` follows the exit code: `pass` (0), `fail` (4), `error` (2 or 3). When an input is invalid and `--out` is given, an `error` report is written; when an input file is missing, no report is written.
- `--legacy-json` emits the pre-1.0 shape (`schema_version`, `summary`, `per_query`) for one more minor version. `compare` reads both shapes.

| `kind` | `subject` | `predicate.summary` | `predicate.details` |
|---|---|---|---|
| `rag.score` | the run file | `k`, `relevance_level`, `queries`, `unjudged_queries`, `queries_without_results`, `queries_without_relevant`, `unscored_run_queries`, `skipped_query_rows`, `skipped_retrieved_rows`, and `hit_rate_at_k`, `recall_at_k`, `precision_at_k`, `mrr_at_k`, `ndcg_at_k`, `map_at_k` | `per_query`: one row per judged query with `recall`, `precision`, `mrr`, `ndcg`, `ap`, `hit` |
| `rag.compare` | the candidate report | `passed`, `reason`, `failed_metrics`, `alpha`, `test`, `queries_compared`, `per_query.<metric>` (`worse`, `better`, `unchanged`), `most_regressed`, and `metrics.<name>` with `baseline`, `candidate`, `regression_pct`, `max_regression_pct`, `gated`, `over_budget`, `p_value`, `significant`, `passed` | `per_query_diff`: per query and metric, `baseline`, `candidate`, `delta` |
| `rag.overlap` (exact) | both corpora | `a_docs`, `b_docs`, `overlap_docs`, `overlap_rate`, skipped-row counts, `match` | empty |
| `rag.overlap` (minhash) | both corpora | `method`, `a_docs`, `b_docs`, `pairs`, `a_docs_with_match`, `overlap_rate`, `threshold`, `shingle`, `num_perm`, `bands`, `rows`, `candidates_checked`, `miss_probability_at_threshold` | `pairs`: `a_id`, `b_id`, `jaccard` |
| `rag.leakage` | the eval items | `items`, `texts_checked`, `corpus_docs`, `leaked_items`, `leaked_texts`, `threshold`, `shingle`, `fields`, `max_leaks`, skipped counts | `leaks`: `item_id`, `field`, `doc_id`, `containment`, `shared_shingles`, `item_shingles` |
| any, on error | the input files that exist | `error`: the message | empty |

To sign a report, use the optional [toolkit-ml-provenance](https://github.com/AKIVA-AI/toolkit-ml-provenance) CLI (Ed25519 key, or Sigstore keyless with its `sigstore` extra):

```bash
toolkit-mlsbom sign-file report.json     # then: toolkit-mlsbom verify-file report.json
```

## Exit codes

| Code | Meaning |
|---|---|
| `0` | Success, or `compare` passed |
| `2` | CLI or input error (bad arguments, unreadable file, invalid input) |
| `3` | Unexpected error |
| `4` | `compare` failed its budget or `leakage` found more leaks than allowed (`verdict: fail`), or `validate-report` found an invalid report |

## Development

Install from source in editable mode, with the test, lint and type-check tools:

```bash
git clone https://github.com/AKIVA-AI/toolkit-rag-quality.git
cd toolkit-rag-quality
pip install -e ".[dev]"            # add ,langchain,llamaindex to run the adapter tests
pytest -q
ruff check .
pyright src/
```

See [CONTRIBUTING.md](CONTRIBUTING.md) and [CHANGELOG.md](CHANGELOG.md).

## Contributing and security

Contributions are welcome: see [CONTRIBUTING.md](CONTRIBUTING.md) and the
[Code of Conduct](CODE_OF_CONDUCT.md). Please report security problems
privately, as described in [SECURITY.md](SECURITY.md).

## Releasing

Releases are cut by pushing a `vX.Y.Z` tag. CI runs the tests, builds the
sdist and wheel, checks them, attaches them to a GitHub Release and publishes
them to PyPI with Trusted Publishing. [RELEASING.md](RELEASING.md) describes
the process and how to verify a release.

## License

Apache License 2.0. See [LICENSE](LICENSE) and [NOTICE](NOTICE).

Versions 0.2.0 and earlier were released under the MIT License and remain available under it.
