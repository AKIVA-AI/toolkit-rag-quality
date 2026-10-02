# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [1.0.0] - 2026-09-26

First stable release: retrieval regression testing in CI. Highlights: trec_eval-equal metrics with graded relevance and TREC/BEIR formats, a regression gate with per-query diffs, paired significance tests and per-metric budgets, a GitHub Action, leakage and near-duplicate checks, retriever adapters, and in-toto report envelopes. See the breaking changes under **Changed** and **Removed**.

### Release and project files

- CI now runs `pip-audit` with every optional extra installed (`langchain`, `llamaindex`), not only `dev`. One advisory is ignored with a documented justification and a re-check date: CVE-2026-81726 in `nltk`, which arrives only through `llama-index-core` and has no fixed release yet. This package never imports `nltk`. See "Known advisories" in `SECURITY.md`.
- The PyPI distribution name is now `toolkit-rag-quality`, matching the repository (was `toolkit-rag-quality-toolkit`, never published). Import paths and CLI commands are unchanged.
- `schemas/report-envelope.v1.json` is now byte-identical to the shared copy used across the toolkit repos. The built-in `validate_envelope` now ignores unknown fields too, as in-toto Statement v1 intends.
- Release workflow: a `v*` tag runs the tests, builds the sdist and wheel,
  checks them with `twine check --strict` (twine 6.1 or newer, which reads the
  Metadata 2.4 that setuptools 77+ writes), installs the wheel and checks its
  version against the tag, and attaches both files to a GitHub Release. The
  PyPI upload (Trusted Publishing) runs only when the repository variable
  `PUBLISH_TO_PYPI` is `true`. See `RELEASING.md`.
- CI builds and checks the package the same way on every pull request.
- Package metadata: SPDX license expression `Apache-2.0` with `LICENSE` and
  `NOTICE` in the distributions, author AKIVA AI, LLC, and links to the
  documentation, issues and changelog.
- Added `CODE_OF_CONDUCT.md` (Contributor Covenant 2.1), issue and pull request
  templates and `RELEASING.md`. `SECURITY.md` lists the supported versions and
  the private reporting channel.

### Fixed
- precision@k now divides by k, not by the number of documents returned. Returning fewer documents no longer raises the score.
- nDCG@k's ideal DCG now covers `min(|relevant|, k)` positions, not `min(|relevant|, len(retrieved))`.
- Repeated ids in a retrieved list are removed before the cutoff (first occurrence wins). Duplicates previously pushed nDCG and AP above 1.0.
- `--k` must be a positive integer. A negative k used to mis-slice the results and report every metric as 1.0.
- Queries with no `relevant_ids` are excluded from the averages (trec_eval semantics) and counted in `unjudged_queries`, instead of being averaged in as zero. Scoring with no judged queries is an error.
- Rows without an `id` (and, for `overlap`, without `text`) are counted in the output and logged, instead of being dropped silently.
- `overlap` rejects a corpus larger than `--max-records` instead of silently truncating it.
- `compare` now fails when any of recall, precision, nDCG, MRR, MAP or hit rate regresses beyond budget, when a baseline metric is missing from the candidate, or when the reports use a different k or query set. It used to check only recall.
- `score --out` now uses the same path validation as `overlap --out`, and creates missing parent directories. The `..` check now also works, because the CLI no longer resolves the path before validation.

### Added
- `examples/bm25.py` and a 5-minute BEIR SciFact walkthrough in the README.
- **GitHub Action**: `action.yml` is a composite action that installs the package from its own checkout, runs `compare` with budgets and optional `alpha`, writes the Markdown table to the step summary, and exposes `verdict`, `exit-code` and `report` outputs. A CI job runs it end to end on fixtures (pass, fail and not-significant cases).
- **Retriever adapters**: `toolkit-rag run-retriever --retriever module:attr` runs a LangChain retriever (`invoke`), a LlamaIndex retriever (`retrieve`) or any callable over a query set (JSONL or BEIR `queries.jsonl`) and writes a TREC or JSONL run. Optional extras `langchain` (`langchain-core`) and `llamaindex` (`llama-index-core`); the core stays dependency-free. A new CI job tests the adapters against the real libraries.
- **Near-duplicate documents**: `overlap --method minhash` finds document pairs with Jaccard similarity of word shingles at or above `--threshold` (default 0.8, 5-word shingles). MinHash-LSH (pure Python, seeded) proposes candidates and every pair is verified with the exact Jaccard; the report states the miss probability at the threshold. Tested against exhaustive exact Jaccard and the LSH S-curve of *Mining of Massive Datasets*, Figure 3.9.
- **Leakage check**: `toolkit-rag leakage` flags eval queries/answers whose word 3-grams are contained in a corpus document (exact containment, default threshold 0.6), with worked threshold examples in the README. Exits 4 above `--max-leaks`. Reads BEIR field names (`_id`, `title`).
- **Per-query diff** in `compare`: every query's baseline, candidate and delta per metric (`details.per_query_diff`), worse/better/unchanged counts per metric, and the most regressed queries (`--primary-metric`, `--top`).
- **Paired significance tests** (`stats.py`, no dependencies): a two-sided randomization (sign-flip) test, exact up to 16 queries and seeded Monte Carlo above, and the paired t-test. Validated against `scipy.stats.permutation_test` and `scipy.stats.ttest_rel` (hard-coded reference values in `tests/test_stats.py`).
- `compare --alpha`: a metric over budget fails only when its drop is significant. `--test permutation|t-test`, `--permutations`, `--seed`.
- `compare --budget METRIC=PCT` (repeatable) sets a budget per metric; `METRIC=off` reports without gating.
- `compare --format markdown` prints a metric table and the most regressed queries.
- **Graded relevance.** Query rows can carry `"relevance": {"doc": grade}`; nDCG uses the grade as a linear gain, and `--relevance-level` sets the minimum grade that counts as relevant (trec_eval `-l`). New reference tests check every metric against trec_eval at relevance levels 1 and 2.
- **TREC and BEIR formats.** `score` reads TREC qrels, TREC runs (ranked with trec_eval's tie-breaking) and BEIR `qrels/*.tsv`, auto-detected or set with `--queries-format` / `--retrieved-format`. `toolkit-rag convert qrels|run` converts between JSONL and TREC (and from BEIR).
- `score_run(qrels=..., run=...)` Python API; summary fields `relevance_level`, `queries_without_relevant` and `unscored_run_queries`.
- `compare` fails with `relevance_level_mismatch` when the two reports used different relevance levels.
- **Report envelope v1** is now the default JSON output of `score`, `compare` and `overlap` (stdout and `--out`): an in-toto Statement v1 in canonical JSON, with SHA-256 digests of the subject and inputs, and a `verdict` that matches the exit code. The convention is in `docs/report-envelope.md`; the JSON Schema is `schemas/report-envelope.v1.json`. `SOURCE_DATE_EPOCH` pins `created_at` for byte-identical reports.
- An input error with `--out` writes an `error` report.
- `--format markdown` on every command.
- `validate-report` checks envelopes against the v1 rules (verdict/exit-code consistency, digests, timestamps) and that `rag.score` reports carry every headline metric.
- `compare --max-regression-pct` sets the budget for the non-recall metrics (defaults to the recall budget).
- A test fixture cross-checked against trec_eval reference values (computed with pytrec_eval and hard-coded).

### Removed
- **Breaking:** the `health` command and `toolkit_rag_quality.monitoring`. The health check always reported "healthy" and could not fail.
- **Breaking:** the unused `toolkit_rag_quality.control_plane` package.
- The unused `.env.example` and the `LOG_LEVEL` setting, which the CLI never read.

### Changed
- A query whose judgments are all below the relevance level (for example only grade-0 judgments) is now scored and averaged in, as trec_eval does. A query with no judgments at all is still excluded.
- A repeated query id in the queries or retrieved JSONL is now an error. It used to be scored twice (queries) or silently overwritten (retrieved).
- **Breaking:** the default JSON output is now the report envelope. `--legacy-json` restores the pre-1.0 shape for one minor version; `compare` reads both.
- Relicensed from MIT to Apache-2.0. Releases before this change remain available under MIT. Added a `NOTICE` file.
- README capabilities are now labeled Working, Partial or Planned. `overlap` is documented as exact matching after normalization; near-duplicate detection is Planned. Installation is from source, because the package is not on PyPI.
- Dependabot opens one grouped weekly PR per ecosystem.

## [0.2.0] - 2026-03-09

### Added
- NDCG@k (Normalized Discounted Cumulative Gain) metric in retrieval scoring
- MAP@k (Mean Average Precision) metric in retrieval scoring
- `health` CLI subcommand for system health checks
- `--format` flag (json, table) on all subcommands
- `--log-format` flag (text, json) for structured JSON logging
- Security scanning in CI (bandit + pip-audit)
- Dependabot configuration for dependency updates
- Pre-commit configuration (ruff, pyright)
- Comprehensive tests for monitoring, overlap, retrieval, and compare modules

### Changed
- Coverage threshold raised from 60% to 70%
- Monitoring module refactored: removed module-level singleton, added `get_health_status()` API

### Fixed
- `monitoring.py` was entirely unwired and untested — now wired into CLI via `health` subcommand

## [0.1.0] - 2026-03-08

### Added
- Initial release
- 4 CLI subcommands: `score`, `overlap`, `compare`, `validate-report`
- Recall@k, Precision@k, MRR@k, Hit-Rate@k metrics
- Corpus overlap detection with SHA-256 fingerprinting
- CI gating via configurable recall regression budget
- Report validation with schema versioning
- Docker support (Dockerfile + docker-compose.yml)
- GitHub Actions CI pipeline (test, lint, build)
