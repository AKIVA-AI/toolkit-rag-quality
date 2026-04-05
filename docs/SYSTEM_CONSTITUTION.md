# System Constitution — toolkit-rag-quality

> Akiva Build Standard Phase 0.5 | Archetype 9 — Developer Tool / CLI Utility
> Established: 2026-04-04

## System Identity

**Primary user:** ML/AI engineers evaluating RAG retrieval quality.

**Core purpose:** Deterministic retrieval quality metrics (recall@k, precision@k, MRR@k, NDCG@k, MAP@k) and corpus overlap detection, without model calls.

**Entry point:** `toolkit-rag` CLI.

## Architectural Invariants

These properties must hold at all times. Any change that violates an invariant requires an ADR and explicit approval.

| # | Invariant | Rationale |
|---|-----------|-----------|
| AI-1 | **Zero runtime dependencies** — core package must never add runtime dependencies | Keeps install instant and audit surface minimal |
| AI-2 | **Deterministic output** — same input must always produce exactly the same metrics | No randomness, no model calls; enables CI diffing |
| AI-3 | **Read-only operations** — the tool reads input files and writes reports; it never modifies source data | Users must trust the tool near production corpora |
| AI-4 | **CLI-first** — all functionality accessible via the `toolkit-rag` entry point | Programmatic and CI usage are first-class |
| AI-5 | **JSON-first output** — all commands produce structured JSON by default | Machine-readable for pipeline integration |
| AI-6 | **Schema-versioned reports** — report format carries `schema_version` for forward compatibility | Consumers can detect and adapt to format changes |

## Non-Negotiables

1. **Mathematical correctness** — all retrieval metrics must be verified with known-value tests. A metric implementation that produces wrong numbers is a P0 defect.
2. **Exit code semantics** — `0` = success, `2` = CLI error, `3` = unexpected error, `4` = validation/regression failure. No other exit codes. Scripts depend on these.
3. **Text normalization before fingerprinting** — corpus overlap must strip, lowercase, and collapse whitespace before computing fingerprints. Skipping normalization produces false negatives.
4. **Configurable regression budget** — compare regression budget defaults to 2% max recall regression but must be overridable via CLI flag.

## Failure Mode Boundaries

| # | Boundary | Required behavior |
|---|----------|-------------------|
| FM-1 | **Never silently drop queries** | If a query ID has no matching results, skip it with a logged warning — never ignore silently |
| FM-2 | **Never produce partial reports** | Either compute all metrics for all queries or fail with an error and non-zero exit code |
| FM-3 | **Never exceed memory on large corpora** | Enforce `max_records` limit (default 50,000); reject input that exceeds limit with a clear message |
| FM-4 | **Never return exit 0 on regression** | When regression threshold is exceeded, exit code must be `4` |

## Amendment Process

Changes to this constitution require:
1. An ADR documenting the change and rationale.
2. Review confirming no downstream CI contracts are broken.
3. Update to `schema_version` if report format is affected.
