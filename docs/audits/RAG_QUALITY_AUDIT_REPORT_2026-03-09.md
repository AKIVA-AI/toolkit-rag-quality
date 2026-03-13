# toolkit-rag-quality System Audit Report

**Date:** 2026-03-09
**Auditor:** Claude Code (Automated — full source verification)
**Archetype:** 9 — Developer Tool / CLI Utility
**Previous Audit:** None (initial audit)
**Baseline:** Source code verified at commit `912c042`

## Composite Score: 62.9/100

| # | Dimension | Weight | Score (0-10) | Weighted | Min | Status |
|---|-----------|--------|-------------|----------|-----|--------|
| 1 | Architecture Integrity | 8% | 8 | 6.40 | — | PASS |
| 2 | Authentication & Authorization | 2% | 1 | 0.20 | — | N/A |
| 3 | Data Isolation & RLS | 0% | 0 | 0.00 | — | N/A |
| 4 | API Surface Quality | 12% | 7 | 8.40 | 7 | PASS |
| 5 | Data Layer Integrity | 2% | 6 | 1.20 | — | — |
| 6 | Frontend Quality | 0% | 0 | 0.00 | — | N/A |
| 7 | Testing & QA | 15% | 7 | 10.50 | 7 | PASS |
| 8 | Security Posture | 10% | 6 | 6.00 | 6 | PASS |
| 9 | Observability & Monitoring | 5% | 5 | 2.50 | — | — |
| 10 | CI/CD & Deployment | 10% | 7 | 7.00 | 6 | PASS |
| 11 | Documentation Accuracy | 10% | 7 | 7.00 | 6 | PASS |
| 12 | Domain Capability Depth | 8% | 7 | 5.60 | 6 | PASS |
| 13 | AI/ML Capability | 5% | 5 | 2.50 | — | — |
| 14 | Connectivity & Channel Interface | 2% | 3 | 0.60 | — | — |
| 15 | Agentic UI/UX | 0% | 0 | 0.00 | — | N/A |
| 16 | User Experience & Interface | 0% | 0 | 0.00 | — | N/A |
| 17 | User Journey & Persona Alignment | 0% | 0 | 0.00 | — | N/A |
| 18 | Zero Trust Architecture | 2% | 3 | 0.60 | — | — |
| 19 | Enterprise Security & Compliance | 5% | 5 | 2.50 | — | — |
| 20 | Operational Readiness | 2% | 5 | 1.00 | — | — |
| 21 | Agentic Workspace | 2% | 2 | 0.40 | — | — |
| | **Total** | **100%** | | **62.40** | | |

**Archetype 9 minimum checks:**

| Dimension | Required | Actual | Status |
|-----------|----------|--------|--------|
| Dim 4 — API Surface Quality | >= 7 | 7 | PASS |
| Dim 7 — Testing & QA | >= 7 | 7 | PASS |
| Dim 8 — Security Posture | >= 6 | 6 | PASS |
| Dim 10 — CI/CD | >= 6 | 7 | PASS |
| Dim 11 — Documentation | >= 6 | 7 | PASS |
| Dim 12 — Domain Capability | >= 6 | 7 | PASS |
| **Composite** | **>= 60** | **62.4** | **PASS** |

All archetype minimums met. Composite exceeds 60 threshold.

---

## Dimension 1: Architecture Integrity — Score: 8/10

**Weight: 8%**

### Evidence

- **Package structure:** Clean `src/toolkit_rag_quality/` layout with 7 modules: `cli.py` (268 LOC), `io.py` (165 LOC), `retrieval.py` (76 LOC), `overlap.py` (40 LOC), `compare.py` (36 LOC), `report.py` (32 LOC), `monitoring.py` (52 LOC)
- **Total source:** ~697 LOC across 9 Python files (including `__init__.py` and `__main__.py`), 470 LOC test code
- **Separation of concerns:** Each module handles exactly one responsibility — scoring logic, corpus analysis, CI gating, report serialization, file I/O, health checks
- **Public API:** `__init__.py` exports `__all__` with 4 clean symbols: `CompareBudget`, `compare_reports`, `compute_overlap`, `score_retrieval`
- **Entry point:** `toolkit-rag` registered in `pyproject.toml` `[project.scripts]`, `__main__.py` enables `python -m toolkit_rag_quality`
- **Version management:** `importlib.metadata` with `PackageNotFoundError` fallback
- **No circular dependencies detected**
- **Zero runtime dependencies** — `dependencies = []` in `pyproject.toml`
- **`py.typed` marker** present for PEP 561 compliance

### Gaps

- `monitoring.py` uses module-level singleton (`_metrics = Metrics()`) — not thread-safe for concurrent use
- No plugin/extension architecture (acceptable for narrow-scope tool)

---

## Dimension 2: Authentication & Authorization — Score: 1/10

**Weight: 2%**

### Evidence

- Local CLI tool with no authentication — appropriate for archetype
- No signing or integrity verification on reports

### Assessment

Score of 1 reflects that auth is not applicable but no report integrity mechanism exists. Acceptable for Archetype 9 at 2% weight.

---

## Dimension 3: Data Isolation & RLS — Score: 0/10

**Weight: 0% — N/A for CLI tools**

---

## Dimension 4: API Surface Quality — Score: 7/10

**Weight: 12%**

### Evidence

- **4 CLI subcommands:** `score`, `overlap`, `compare`, `validate-report`
- **Consistent exit codes:** `0` (success), `2` (CLI error), `3` (unexpected error), `4` (validation failed) — defined as named constants
- **`--version` flag** works correctly
- **`--verbose` / `-v` flag** for debug logging
- **Schema versioning:** Reports include `schema_version` field
- **Programmatic API:** `score_retrieval()`, `compute_overlap()`, `compare_reports()` all keyword-only with clear signatures
- **`RAGReport` dataclass** with `to_dict()` / `from_dict()` serialization — frozen/immutable
- **`CompareBudget` dataclass** with `max_recall_regression_pct` configurable
- **JSONL input format** well-defined for queries/retrieved/corpora
- **JSON output** with `indent=2, sort_keys=True` for reproducibility
- **Help text** on all arguments

### Gaps

- `overlap` uses `--a` and `--b` — not self-documenting single-letter flags for required args
- No machine-readable error output (errors go to stderr as free text)
- No batch processing mode
- `--k` is a string parsed to int — could use `type=int` in argparse
- No `--format` flag (only JSON output, no CSV/table)

---

## Dimension 5: Data Layer Integrity — Score: 6/10

**Weight: 2%**

### Evidence

- `io.py` (165 LOC): comprehensive path validation with `validate_path_for_read()` and `validate_path_for_write()`
- JSONL parser with line-number error reporting and type checking (rejects non-dict objects)
- UTF-8 encoding enforced throughout (`encoding="utf-8"` on all read/write)
- SHA-256 fingerprinting for overlap detection with text normalization (lowercase + whitespace collapse)
- `write_json()` auto-creates parent directories

### Gaps

- No caching of computed fingerprints
- Text normalization is basic (no Unicode normalization, no punctuation handling)
- No streaming for large files — entire JSONL loaded into memory

---

## Dimension 6: Frontend Quality — Score: 0/10

**Weight: 0% — N/A for CLI tools**

---

## Dimension 7: Testing & QA — Score: 7/10

**Weight: 15%**

### Evidence

- **29 tests pass** in 0.26s — fast, deterministic
- **78.27% coverage** (threshold set at 60%)
- **4 test files:**
  - `test_cli.py` (113 LOC) — CLI integration tests: version flag, score+compare flow, overlap flow
  - `test_enhancements.py` (312 LOC) — path validation, JSON I/O, JSONL parsing, error handling, edge cases
  - `test_overlap.py` (13 LOC) — single overlap unit test
  - `test_retrieval_and_compare.py` (25 LOC) — core logic tests
- **CI matrix testing:** Python 3.10, 3.11, 3.12
- **Linting in CI:** ruff configured with `E`, `F`, `I`, `B`, `UP` rule sets
- **Type checking:** pyright passes with 0 errors, 0 warnings
- **ruff check passes clean** (verified)

### Gaps

- `test_overlap.py` is only 13 lines (1 test case) — very thin coverage of overlap module
- `test_retrieval_and_compare.py` is only 25 lines (2 test cases) — thin coverage of core domain logic
- Coverage threshold at 60% is low for a tool archetype (should be 70%+)
- `monitoring.py` has 0% coverage — completely untested
- No property-based testing
- No performance/benchmark tests for large corpora
- No fuzz testing for JSONL parsing
- `conftest.py` adds `src/` to sys.path manually — fragile path manipulation

---

## Dimension 8: Security Posture — Score: 6/10

**Weight: 10%**

### Evidence

- **No hardcoded secrets** in any source file
- **No `eval()`, `exec()`, `shell=True`** anywhere
- **No network calls** — fully offline tool
- **SECURITY.md** present with disclosure guidance
- **`.env` in `.gitignore`** — secrets not tracked
- **`.env.example`** contains only `LOG_LEVEL=INFO` — no sensitive data
- **Path validation** prevents directory traversal (resolves to absolute paths)
- **Input validation** on JSONL files (type checking each line)

### Gaps

- **No bandit/safety in CI** — no automated security scanning
- **No Dependabot** configuration (`.github/dependabot.yml` missing)
- **No input size limits** on file reads — could OOM on very large files
- **No report signing** — output could be tampered
- `max_records` defaults to 50,000 but no memory guard

---

## Dimension 9: Observability & Monitoring — Score: 5/10

**Weight: 5%**

### Evidence

- Python `logging` module used consistently across `cli.py`, `io.py`
- `--verbose` flag switches from WARNING to DEBUG level
- Logs to stderr (correct for CLI tools that output JSON to stdout)
- Timestamped log format: `%(asctime)s | %(levelname)-8s | %(message)s`
- Dedicated `monitoring.py` module with `HealthCheck` class and `Metrics` class (running average tracking)

### Gaps

- **`monitoring.py` not wired into CLI** — no `health` or `metrics` subcommand
- `monitoring.py` has 0% test coverage
- No structured logging (JSON log format option)
- No OpenTelemetry integration
- No metrics export (Prometheus, StatsD)
- Health check class is trivially simple (always returns "healthy")

**Score adjusted from 6 to 5:** The monitoring module exists but is entirely unwired, untested, and non-functional. Having dead code does not earn observability credit.

---

## Dimension 10: CI/CD & Deployment — Score: 7/10

**Weight: 10%**

### Evidence

- **GitHub Actions CI** (`.github/workflows/ci.yml`):
  - `test` job: matrix across Python 3.10/3.11/3.12, `pytest --cov`, Codecov upload
  - `lint` job: `ruff check .`
  - `build` job: `python -m build` (depends on test + lint passing)
- **Dockerfile** present: `python:3.11-slim`, installs package, creates `evaluations/` and `reports/` dirs
- **docker-compose.yml** with volume mounts for evaluations/reports
- **Package builds successfully** via `python -m build`
- Codecov integration on Python 3.11

### Gaps

- No PyPI publishing step in CI
- No Docker registry publishing
- No semantic versioning automation (no release workflow)
- `docker-compose.yml` uses deprecated `version: '3.8'` key
- Dockerfile does not pin pip or setuptools versions
- No SBOM generation
- `build` job uses `actions/checkout@v4` (not v6 — minor)
- No branch protection or PR gating documented

---

## Dimension 11: Documentation Accuracy — Score: 7/10

**Weight: 10%**

### Evidence

- **README.md** (73 lines): installation, quickstart with all 3 main commands, data format examples (JSONL for queries/retrieved/corpora), CLI command list, exit code docs, license
- **QUICKSTART.md**: step-by-step install + usage + Docker commands
- **CONTRIBUTING.md**: dev setup, quality gate commands (ruff, pyright, pytest)
- **DEPLOYMENT.md**: Docker deployment, local install, CI/CD integration YAML example, monitoring code snippet
- **SECURITY.md**: disclosure policy, untrusted input guidance
- **Docstrings** on all `io.py` functions with Args/Returns/Raises
- **`py.typed` marker** for downstream type checker support

### Gaps

- No API documentation for programmatic use (only CLI documented)
- No changelog / CHANGELOG.md
- Report output format not documented (input formats are, output is not)
- `monitoring.py` capabilities referenced in DEPLOYMENT.md but the module is unwired
- No architecture/design doc
- README title says "Toolkit RAG Quality Toolkit" (redundant)

---

## Dimension 12: Domain Capability Depth — Score: 7/10

**Weight: 8%**

### Evidence

- **4 standard IR metrics:** recall@k, precision@k, MRR@k, hit-rate@k
- **Per-query breakdown** in reports with individual recall, precision, MRR, hit count
- **Corpus overlap detection:** SHA-256 fingerprint with text normalization (whitespace + case)
- **CI gating:** configurable recall regression budget with `CompareBudget`
- **Report validation:** schema shape checking via `validate-report` command
- **Schema versioning** on reports for forward compatibility
- **`max_records` parameter** on overlap to bound computation

### Gaps

- **Missing NDCG@k** — a standard and important IR ranking metric
- **Missing MAP** (Mean Average Precision) — another standard IR metric
- Overlap detection is exact-match only (no fuzzy/embedding-based similarity)
- No chunking quality metrics
- No latency/throughput measurement
- No dataset drift detection
- No answer quality metrics (faithfulness, relevance, groundedness)
- Compare only gates on recall regression — no precision or MRR gating

---

## Dimension 13: AI/ML Capability — Score: 5/10

**Weight: 5%**

### Evidence

- Designed for RAG evaluation — squarely in the ML tooling domain
- Deterministic metrics (no model calls needed — a feature, not a bug)
- Zero-dependency design means it runs anywhere without GPU/API keys

### Gaps

- No embedding computation or semantic similarity
- No LLM-as-judge evaluation
- No answer quality metrics (faithfulness, relevance)
- No RAGAS integration
- No model-based near-duplicate detection

---

## Dimension 14: Connectivity & Channel Interface — Score: 3/10

**Weight: 2%**

### Evidence

- CLI interface with JSON/JSONL file I/O
- Programmatic Python API via `__init__.py` exports

### Gaps

- No REST API server mode
- No webhook integration
- No MCP tool integration
- Monitoring module not exposed as endpoint

---

## Dimensions 15-17: Agentic UI/UX, UX Quality, User Journey — Score: 0/10 each

**Weight: 0% each — N/A for CLI tools**

---

## Dimension 18: Zero Trust Architecture — Score: 3/10

**Weight: 2%**

### Evidence

- Path validation: `validate_path_for_read()` / `validate_path_for_write()` resolve to absolute paths
- No network access — no external trust boundaries
- `max_records` parameter bounds overlap computation size

### Gaps

- No input size limits on JSONL file reads
- No memory bounds enforcement
- No resource limits in Docker configuration
- `max_records` defaults to 50,000 (could be large)

---

## Dimension 19: Enterprise Security & Compliance — Score: 5/10

**Weight: 5%**

### Evidence

- MIT license
- SECURITY.md with disclosure guidance
- No network access reduces attack surface
- Clean `.gitignore` excludes `.env` files

### Gaps

- No CI security scanning (bandit/safety/pip-audit)
- No Dependabot configuration
- No SBOM generation
- No audit logging of tool invocations
- No report signing for integrity verification
- No compliance documentation

---

## Dimension 20: Operational Readiness — Score: 5/10

**Weight: 2%**

### Evidence

- Docker deployment option (Dockerfile + docker-compose.yml)
- CI pipeline functional with 3-job workflow
- Health check module exists (though unwired)
- Zero-dependency install reliability

### Gaps

- Health/metrics not exposed via CLI
- No production deployment evidence
- No runbook / operational documentation
- No resource limits in Docker config

---

## Dimension 21: Agentic Workspace — Score: 2/10

**Weight: 2%**

### Evidence

- Standalone CLI tool — not designed as an agentic component

### Gaps

- No MCP server/tool integration
- No agent loop capability
- Expected for archetype — agentic integration is optional but would raise score

---

## Summary

### Strengths

1. **Zero-dependency design** — `dependencies = []` makes this trivially installable and CI-safe
2. **Clean architecture** — well-separated modules, frozen dataclasses, keyword-only APIs
3. **Full type safety** — pyright passes with 0 errors, `py.typed` marker present
4. **Fast test suite** — 29 tests in 0.26s, 78% coverage
5. **CI matrix** — tests across Python 3.10/3.11/3.12
6. **Deterministic metrics** — no model calls, fully reproducible

### Critical Gaps (P0)

1. No security scanning in CI (bandit/safety/pip-audit)
2. No Dependabot configuration

### High Priority Gaps (P1)

3. `monitoring.py` untested (0% coverage) and unwired to CLI
4. Missing NDCG@k and MAP metrics (standard IR evaluation)
5. Coverage threshold too low (60%, should be 70%+)
6. Thin test coverage on core modules (`test_overlap.py` = 13 LOC, `test_retrieval_and_compare.py` = 25 LOC)
7. No changelog

### Medium Priority Gaps (P2)

8. No PyPI publishing in CI
9. No structured logging option
10. No API documentation for programmatic use
11. Rename `--a` / `--b` to `--corpus-a` / `--corpus-b`
12. Overlap detection is exact-match only (no fuzzy/semantic)
13. Compare only gates on recall — no precision/MRR gating
14. Report output format not documented

### Low Priority Gaps (P3)

15. No SBOM generation
16. No report signing
17. No REST API server mode
18. docker-compose deprecated version key
19. No MCP tool integration
20. README title redundancy ("Toolkit RAG Quality Toolkit")

---

## Sprint Plan

### Sprint 0 — Security (3 tasks)

1. Add bandit + pip-audit to CI pipeline
2. Add `.github/dependabot.yml`
3. Raise coverage threshold from 60% to 70%

### Sprint 1 — Domain Depth + Testing (7 tasks)

4. Add NDCG@k metric to `retrieval.py`
5. Add MAP metric to `retrieval.py`
6. Expand `test_overlap.py` — edge cases (empty corpora, single doc, all duplicates, no text field)
7. Expand `test_retrieval_and_compare.py` — edge cases (zero relevant, all hits, missing IDs, empty retrieved)
8. Add tests for `monitoring.py` (currently 0% coverage)
9. Wire `monitoring.py` into CLI as `health` subcommand or remove it
10. Add precision and MRR regression gating to `compare`

### Sprint 2 — Documentation + DevEx (5 tasks)

11. Document report output format in README
12. Rename `--a` / `--b` to `--corpus-a` / `--corpus-b`
13. Add CHANGELOG.md
14. Add programmatic API documentation section to README
15. Fix README title redundancy

### Sprint 3 — CI/CD + Polish (4 tasks)

16. Add PyPI publish workflow (on tag)
17. Add SBOM generation step
18. Remove deprecated `version` key from docker-compose.yml
19. Add structured JSON logging option (`--log-format json`)

---

_Audit completed 2026-03-09 by Claude Code. All scores verified against source code at commit 912c042._
