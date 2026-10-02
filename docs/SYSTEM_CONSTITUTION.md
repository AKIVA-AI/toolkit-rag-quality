# Design principles: toolkit-rag-quality

## Identity

**Primary user:** engineers evaluating retrieval quality for search and RAG systems.

**Core purpose:** deterministic retrieval metrics (hit rate, recall, precision, MRR, nDCG and MAP at k) and exact-duplicate corpus overlap, without model calls.

**Entry point:** the `toolkit-rag` CLI.

## Invariants

| # | Invariant | Rationale |
|---|-----------|-----------|
| I-1 | **Zero runtime dependencies.** The core package does not add runtime dependencies. | Instant install and a minimal audit surface. |
| I-2 | **Deterministic output.** The same input always produces the same metrics. | No randomness and no model calls, so CI results can be diffed. |
| I-3 | **Read-only operations.** The tool reads input files and writes reports; it never modifies source data. | Safe to run near production corpora. |
| I-4 | **CLI-first.** All functionality is reachable through `toolkit-rag`. | Programmatic and CI use are first-class. |
| I-5 | **JSON-first output.** Every command prints structured JSON by default. | Machine-readable for pipelines. |
| I-6 | **Versioned reports.** Reports are report-envelope v1 statements (`docs/report-envelope.md`); the predicate type ends in `/report/v1`. | Consumers can detect format changes. |

## Non-negotiables

1. **Mathematical correctness.** Metrics follow trec_eval semantics at cutoff k and are verified with known-value tests, including a fixture cross-checked against trec_eval. A metric that produces wrong numbers is a release-blocking defect.
2. **Exit code semantics.** `0` success, `2` CLI or input error, `3` unexpected error, `4` gate or validation failure. Scripts depend on these.
3. **Text normalization before fingerprinting.** Overlap strips, lowercases and collapses whitespace before hashing.
4. **Configurable regression budgets.** `compare` defaults to a 2% maximum relative regression for every metric; `--budget METRIC=PCT` (or `off`) overrides it per metric.

## Failure-mode boundaries

| # | Boundary | Required behavior |
|---|----------|-------------------|
| FM-1 | **Never silently drop input.** | Rows without an `id`, and queries without `relevant_ids`, are counted in the report and logged as warnings. Judged queries with no retrieved row score zero and are counted. |
| FM-2 | **Never produce partial reports.** | Either compute all metrics for all judged queries or fail with an error and a non-zero exit code. |
| FM-3 | **Never truncate large inputs.** | `overlap` rejects a corpus larger than `max_records` (default 50,000) with a clear message. |
| FM-4 | **Never return exit 0 on regression.** | When any gated metric exceeds its budget, or the reports are not comparable, `compare` exits `4`. |

## Changing these principles

Open a pull request that explains the change and its effect on existing CI users. If the report format changes, bump the predicate type version.
