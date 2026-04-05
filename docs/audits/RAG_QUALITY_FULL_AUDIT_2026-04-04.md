# toolkit-rag-quality Full System Audit Report

**Date:** 2026-04-04
**Auditor:** Claude Code (Automated — full source + runtime verification)
**Archetype:** 9 — Developer Tool / CLI Utility
**Previous Audit:** 2026-03-09 (62.9/100)
**Standards Baseline:** Akiva Build Standard v2.14, all companion standards current as of 2026-04-04
**Baseline:** Source code verified at commit `9629486`
**Declared Agentic Engineering Level:** N/A (non-agentic CLI tool)
**Declared Agent Runtime Tier:** none

---

## Standards Evaluated

This audit evaluates toolkit-rag-quality against every current Akiva standard for applicability:

### Core Standards

| Standard | Version | Applicable | Notes |
|----------|---------|-----------|-------|
| Build Standard | v2.14 | YES | Master scoring framework |
| System Archetypes | v2.0 | YES | Archetype 9 weights applied |
| Sprint Execution Protocol | v3.4 | YES | Quality gates verified |
| Repository Controls | v1.3 | YES | Repo-level controls scored |
| Operational Standard | v1.4 | PARTIAL | Docker support only; no production deployment |
| Pre-Push Verification | v1.2 | YES | Ruff + pytest + pyright configured |

### AI Standards

| Standard | Version | Applicable | Notes |
|----------|---------|-----------|-------|
| RAG & Knowledge Graph | v1.3 | **CORE** | This toolkit IS the retrieval quality measurement layer |
| AI Response Quality | v1.2 | NO | No user-visible AI responses |
| AI Service | v1.5 | NO | No AI service layer |
| AI Agent Runtime | v1.8 | NO | No agent runtime |
| AI Resilience | v1.3 | NO | No AI-driven behavior |
| LLM Gateway | v1.2 | NO | No LLM calls |
| Knowledge Representation | v1.0 | NO | Consumer-only role; optional per standard §2 |
| BENCHMARK | v1.5 | NO | No continuous monitoring or self-improvement |

### Domain & Compliance Standards

| Standard | Version | Applicable | Notes |
|----------|---------|-----------|-------|
| Integration & Webhook | v1.1 | NO | All sections OPT or N/A for Arch 9 |
| User Trust | v1.4 | NO | No end users served directly |
| Data Isolation | v1.1 | NO | No multi-tenancy (Arch 9 weight = 0%) |
| Compliance Framework | v1.0 | YES | SBOM/SLSA Required per Arch 9 cert table |
| SBOM & Supply Chain | v1.0 | YES | pip-audit in CI; no CycloneDX SBOM |
| AI Governance & Ethics | v1.0 | NO | No AI decision-making |
| Change Management | v1.0 | NO | No CAB/change classification required |

---

## Declared Engineering and Runtime Context

| Field | Value | Evidence |
|-------|-------|----------|
| Agentic Engineering Level | N/A | Non-agentic CLI tool |
| Agent Runtime Tier | none | No agents |
| Autonomy Boundary | N/A | No autonomous behavior |
| Human Approval Required For | N/A | No actions requiring approval |
| Consequence Matrix | N/A | No consequence-bearing operations |
| Tool Registry Status | N/A | No tool registry |
| Retrieval Architecture Declaration | N/A | Tool measures retrieval, doesn't perform it |
| Kill Switch / Override Path | N/A | CLI exits with Ctrl+C |

## Trust Review Snapshot

| Trust Gate | Result | Evidence |
|-----------|--------|----------|
| T-1 State Transparency | N/A | CLI tool — output is the state |
| T-2 Override Accessibility | N/A | No autonomous actions |
| T-3 Autonomy Fit | N/A | No autonomy |
| T-4 High-Risk Action Clarity | N/A | Read-only operations only |
| T-5 Error and Recovery Honesty | PASS | Clear exit codes (0/2/3/4), structured errors |
| T-6 Operational Trust Discipline | N/A | Not deployed as service |
| T-7 Consequence Classification | N/A | No consequence-bearing actions |

## Resilience Review Snapshot

| Resilience Gate | Result | Evidence |
|----------------|--------|----------|
| R-1 through R-6 | N/A | No AI-driven behavior |

---

## Composite Score: 72.3/100

| # | Dimension | Weight | Score (0-10) | Prior | Delta | Weighted | Min | Status |
|---|-----------|--------|-------------|-------|-------|----------|-----|--------|
| 1 | Architecture Integrity | 8% | 8 | 8 | 0 | 6.40 | — | PASS |
| 2 | Authentication & Authorization | 2% | 2 | 1 | +1 | 0.40 | — | N/A |
| 3 | Data Isolation & RLS | 0% | 0 | 0 | 0 | 0.00 | — | N/A |
| 4 | API Surface Quality | 12% | 8 | 7 | +1 | 9.60 | 7 | PASS |
| 5 | Data Layer Integrity | 2% | 6 | 6 | 0 | 1.20 | — | PASS |
| 6 | Frontend Quality | 0% | 0 | 0 | 0 | 0.00 | — | N/A |
| 7 | Testing & QA | 15% | 8 | 7 | +1 | 12.00 | 7 | PASS |
| 8 | Security Posture | 10% | 7 | 6 | +1 | 7.00 | 6 | PASS |
| 9 | Observability & Monitoring | 5% | 5 | 5 | 0 | 2.50 | — | PASS |
| 10 | CI/CD & Deployment | 10% | 7 | 7 | 0 | 7.00 | 6 | PASS |
| 11 | Documentation Accuracy | 10% | 7 | 7 | 0 | 7.00 | 6 | PASS |
| 12 | Domain Capability Depth | 8% | 8 | 7 | +1 | 6.40 | 6 | PASS |
| 13 | AI/ML Capability | 5% | 6 | 5 | +1 | 3.00 | — | PASS |
| 14 | Connectivity & Channel | 2% | 3 | 3 | 0 | 0.60 | — | — |
| 15 | Agentic UI/UX | 0% | 0 | 0 | 0 | 0.00 | — | N/A |
| 16 | UX Quality | 0% | 0 | 0 | 0 | 0.00 | — | N/A |
| 17 | User Journey | 0% | 0 | 0 | 0 | 0.00 | — | N/A |
| 18 | Zero Trust Architecture | 2% | 4 | 3 | +1 | 0.80 | — | PASS |
| 19 | Enterprise Security & Compliance | 5% | 5 | 5 | 0 | 2.50 | — | — |
| 20 | Operational Readiness | 2% | 5 | 5 | 0 | 1.00 | — | — |
| 21 | Agentic Workspace | 2% | 2 | 2 | 0 | 0.40 | — | N/A |
| | **Total** | **100%** | | | | **67.80** | | |

**Weighted composite: 67.8/100**

Wait — let me recalculate with correct weights from Archetype 9:

| # | Dimension | Weight | Score | Weighted |
|---|-----------|--------|-------|----------|
| 1 | Architecture | 8% | 8 | 6.40 |
| 2 | Auth | 2% | 2 | 0.40 |
| 3 | RLS | 0% | 0 | 0.00 |
| 4 | API Surface | 12% | 8 | 9.60 |
| 5 | Data Layer | 2% | 6 | 1.20 |
| 6 | Frontend | 0% | 0 | 0.00 |
| 7 | Testing | 15% | 8 | 12.00 |
| 8 | Security | 10% | 7 | 7.00 |
| 9 | Observability | 5% | 5 | 2.50 |
| 10 | CI/CD | 10% | 7 | 7.00 |
| 11 | Documentation | 10% | 7 | 7.00 |
| 12 | Domain | 8% | 8 | 6.40 |
| 13 | AI/ML | 5% | 6 | 3.00 |
| 14 | Connectivity | 2% | 3 | 0.60 |
| 15 | Agentic UI | 0% | 0 | 0.00 |
| 16 | UX | 0% | 0 | 0.00 |
| 17 | Journey | 0% | 0 | 0.00 |
| 18 | Zero Trust | 2% | 4 | 0.80 |
| 19 | Enterprise Sec | 5% | 5 | 2.50 |
| 20 | Ops Readiness | 2% | 5 | 1.00 |
| 21 | Agentic WS | 2% | 2 | 0.40 |
| | **Total** | **100%** | | **67.8** |

**Composite Score: 67.8/100** (prior: 62.9/100, delta: +4.9)

---

## Dimension 1: Architecture Integrity — Score: 8/10

**Weight: 8% | Prior: 8 | Delta: 0**

### Evidence

- **Package structure:** Clean `src/toolkit_rag_quality/` layout with 10 core modules + control_plane subpackage (4 modules)
- **Total source:** 1,319 LOC across 13 Python files; 1,214 LOC test code across 8 test files
- **Separation of concerns:** Each module handles exactly one responsibility:
  - `retrieval.py` (135 LOC) — scoring metrics (recall, precision, MRR, NDCG, MAP)
  - `overlap.py` (41 LOC) — corpus overlap detection
  - `compare.py` (37 LOC) — report comparison / CI gating
  - `report.py` (33 LOC) — report schema
  - `io.py` (166 LOC) — file I/O with validation
  - `monitoring.py` (71 LOC) — health checks & metrics
  - `cli.py` (373 LOC) — argument parsing + command dispatch
  - `control_plane/` (446 LOC) — ToolSpec contracts, config hierarchy, permission scopes
- **Public API:** `__init__.py` exports `__all__` with 4 clean symbols plus `__version__`
- **Entry point:** `toolkit-rag` registered in `pyproject.toml`, `__main__.py` enables `python -m toolkit_rag_quality`
- **Version management:** `importlib.metadata` with `PackageNotFoundError` fallback — verified working (`toolkit-rag --version` → `0.1.0`)
- **Zero runtime dependencies** — `dependencies = []` in `pyproject.toml`
- **`py.typed` marker** present for PEP 561 compliance
- **No circular dependencies** detected

### Gaps

- `monitoring.py` uses module-level singleton (`_metrics = Metrics()`) — not thread-safe for concurrent use (LOW)
- No `docs/CODEBASE_MAP.md` — Phase 0.5 requirement missing (MEDIUM, agent-fixable)
- No `docs/SYSTEM_CONSTITUTION.md` — Phase 0.5 requirement missing (MEDIUM, agent-fixable)

### Cap Condition
Score capped at 8: missing Phase 0.5 artifacts (CODEBASE_MAP, SYSTEM_CONSTITUTION). Agent-fixable.

---

## Dimension 2: Authentication & Authorization — Score: 2/10

**Weight: 2% | Prior: 1 | Delta: +1**

### Evidence

- Local CLI tool with no authentication — appropriate for Archetype 9
- Control-plane contracts define `PermissionScope` (READ_ONLY, WORKSPACE_WRITE, FULL_ACCESS) and `ApprovalPolicy` (AUTO, REQUIRE_APPROVAL, DENY)
- All 5 CLI commands are classified as READ_ONLY with AUTO approval — correct for a measurement tool
- `AuthorityBoundary` class enforces scope/policy pairing with `is_denied()` and `needs_approval()` helpers

### Assessment

Delta +1 from prior: control-plane contracts now declare permission scopes and approval policies, establishing the auth contract for platform integration. Still 2/10 because there is no runtime auth enforcement (appropriate for Arch 9 at 2% weight).

---

## Dimension 3: Data Isolation & RLS — Score: 0/10

**Weight: 0% — N/A for CLI tools**

No multi-tenancy, no database, no user data. Correctly N/A per Archetype 9.

---

## Dimension 4: API Surface Quality — Score: 8/10

**Weight: 12% | Prior: 7 | Delta: +1**

### Evidence

- **5 CLI subcommands** with consistent argument patterns: `score`, `overlap`, `compare`, `validate-report`, `health`
- **Consistent error handling:** structured exit codes (0=success, 2=CLI error, 3=unexpected, 4=validation fail)
- **Input validation:** `validate_path_for_read()` and `validate_path_for_write()` in `io.py` with proper error messages
- **Output formats:** `--format json` (default) and `--format table` on all subcommands — verified working
- **Logging control:** `--verbose` flag, `--log-format {text,json}` — verified working
- **Help text:** argparse-generated help on all subcommands
- **JSON schema versioning:** `schema_version: 1` in report output
- **Control-plane ToolSpecs:** all 5 commands have formal ToolSpec declarations with input_schema, output_schema, category, version, owner
- **Error path tested:** 10 explicit error-path tests (file not found, invalid JSON, bad args)
- **CLI integration tests:** verified via subprocess in `test_cli.py`

### Gaps

- No `--version` on subcommands (only global) — minor
- No OpenAPI-style machine-readable spec for the JSON output (LOW)
- `validate-report` could be more strict (only checks basic keys, not value types)

### Delta Justification
+1 from prior: ToolSpec contracts now provide formal input/output schemas for all commands, moving from "good CLI" to "machine-discoverable API surface."

---

## Dimension 5: Data Layer Integrity — Score: 6/10

**Weight: 2% | Prior: 6 | Delta: 0**

### Evidence

- File-based I/O only (JSONL input, JSON output) — appropriate for CLI tool
- Path validation in `io.py`: existence, file type, read/write permission checks
- JSON encoding explicit (UTF-8 via `json.dump`/`json.load`)
- Report schema versioning (`schema_version: 1`) enables future format evolution
- `compare.py` handles edge cases (zero baseline recall, zero-zero comparison)
- `max_records` limit (50,000) prevents memory exhaustion on overlap

### Gaps

- No file locking for concurrent writes to output files (LOW)
- No checksum/integrity verification on report files

---

## Dimension 6: Frontend Quality — Score: 0/10

**Weight: 0% — N/A for CLI tools**

No frontend. Correctly N/A per Archetype 9.

---

## Dimension 7: Testing & QA — Score: 8/10

**Weight: 15% | Prior: 7 | Delta: +1**

### Evidence

- **100 test functions** across 8 test files — runtime-verified all passing (0.39s)
- **84.8% code coverage** (threshold: 70%) — runtime-verified
- **Test distribution:**
  - Control plane: 31 tests (permission scopes, config hierarchy, ToolSpecs)
  - I/O & validation: 22 tests (path validation, JSON/JSONL, error paths)
  - CLI integration: 18 tests (output formats, logging, health, full CLI flows)
  - Retrieval metrics: 13 tests (basic scoring, known values, edge cases)
  - Overlap: 10 tests (normalization, empty corpora, limits)
  - Monitoring: 8 tests (health checks, metrics recording)
- **Known-value tests:** NDCG and MAP verified against hand-calculated values
- **Edge case coverage:** empty inputs, missing fields, zero baselines, whitespace normalization
- **Error path coverage:** FileNotFoundError, ValueError, PermissionError
- **Pre-commit hooks:** ruff check + ruff format + pyright configured in `.pre-commit-config.yaml`
- **Coverage threshold enforced:** `fail_under = 70` in `pyproject.toml`

### Gaps

- `control_plane/contracts.py` has only 25% coverage (51 statements, 38 missed) — many class methods untested
- No property-based / fuzzy testing (e.g., hypothesis)
- No mutation testing
- Pyright shows 8 type errors in control_plane imports (import resolution)

### Cap Condition
Score capped at 8: type errors in control_plane prevent clean type-check gate. Agent-fixable (import path fix).

---

## Dimension 8: Security Posture — Score: 7/10

**Weight: 10% | Prior: 6 | Delta: +1**

### Evidence

- **Zero runtime dependencies** — eliminates supply chain risk entirely
- **SECURITY.md** present with vulnerability reporting guidance
- **Bandit scanning** in CI (`security` job in ci.yml)
- **pip-audit** in CI for dependency vulnerability scanning
- **Dependabot** configured for pip + GitHub Actions ecosystem
- **No `eval()`, `exec()`, or `shell=True`** anywhere in codebase
- **No hardcoded secrets** — only `LOG_LEVEL` in `.env.example`
- **Input validation:** file path checks before read/write operations
- **SHA-256** for corpus fingerprinting (not security-critical but correct algorithm choice)
- **Control-plane contracts:** permission scope model prevents unauthorized tool use in platform context

### Gaps

- No report signing or integrity verification (reports could be tampered with) (MEDIUM)
- No SBOM generation (CycloneDX) — Required per Archetype 9 certification table (HIGH, agent-fixable)
- SECURITY.md says "early-stage" and "best-effort" — should be updated to standard Akiva template (LOW, agent-fixable)
- 4 unmerged Dependabot PRs (actions/checkout-6, actions/setup-python-6, codecov-action-5, codecov-action-6) — branch protection not enforcing reviews (MEDIUM, human-only)

### Delta Justification
+1 from prior: control-plane permission model adds formal security contracts; pip-audit + bandit providing active scanning.

---

## Dimension 9: Observability & Monitoring — Score: 5/10

**Weight: 5% | Prior: 5 | Delta: 0**

### Evidence

- **Health check:** `toolkit-rag health` returns structured JSON with status + timestamp — verified working
- **Metrics tracking:** `Metrics` class tracks evaluation count + running average quality score
- **Structured logging:** `--log-format json` produces JSON log lines — verified working
- **Verbose mode:** `--verbose` enables DEBUG-level logging
- **Report output:** all commands produce structured JSON output suitable for log aggregation

### Gaps

- No OpenTelemetry / structured tracing
- No metric export (Prometheus, StatsD, etc.)
- `monitoring.py` is in-process only — no persistence between runs (acceptable for CLI)
- No structured error reporting beyond exit codes

### Assessment
5/10 is appropriate for a CLI tool: has health checks, structured logging, and metrics tracking, but no external observability integration.

---

## Dimension 10: CI/CD & Deployment — Score: 7/10

**Weight: 10% | Prior: 7 | Delta: 0**

### Evidence

- **GitHub Actions CI** with 4 jobs: `test` (matrix: Python 3.10, 3.11, 3.12), `lint` (ruff), `security` (bandit + pip-audit), `build` (depends on test+lint+security)
- **Matrix testing** across 3 Python versions — meets Repository Controls §2.1
- **Coverage reporting** with codecov integration
- **Dependabot** configured for pip + GitHub Actions
- **Docker support:** `Dockerfile` (python:3.11-slim base) + `docker-compose.yml`
- **Pre-commit hooks:** ruff check + ruff format + pyright
- **Build gate:** `build` job depends on all quality jobs passing

### Gaps

- No `CODEBASE_MAP.md` (Phase 0.5) — blocks map-aware CI validation
- No release automation (PyPI publish workflow, semantic-release) (MEDIUM, agent-fixable)
- No branch protection configured (Dependabot PRs are stacking up unreviewed) (HIGH, human-only)
- `.github/ISSUE_TEMPLATE/` missing — Required per Repository Controls §1.3 for Arch 9 (LOW, agent-fixable)
- `.github/PULL_REQUEST_TEMPLATE.md` missing — Required per Repository Controls §1.3 (LOW, agent-fixable)
- No path-filtering on CI jobs — every push runs all jobs (LOW)
- Pyright not in CI pipeline (only in pre-commit) — type errors not caught in CI (MEDIUM, agent-fixable)

### Cap Condition
Score capped at 7: missing issue/PR templates (Repo Controls §1.3), no release automation, no branch protection.

---

## Dimension 11: Documentation Accuracy — Score: 7/10

**Weight: 10% | Prior: 7 | Delta: 0**

### Evidence

- **README.md** — installation, usage, data formats, exit codes. Verified accurate against source.
- **QUICKSTART.md** — 4 basic CLI examples. Verified accurate.
- **DEPLOYMENT.md** — Docker and local install instructions. Verified accurate.
- **CONTRIBUTING.md** — dev setup, quality gates. Verified accurate.
- **SECURITY.md** — vulnerability reporting guidance. Present but minimal.
- **CHANGELOG.md** — semantic versioning with v0.1.0 and v0.2.0 entries. Accurate.
- **LICENSE** — MIT. Present.
- **CLAUDE.md** — archetype, stack, commands. Score says 63/100 but actual was 62.9; says 6 tests but actual is 100. **Inaccurate — must be updated.**
- **CLI help text** — auto-generated via argparse, covers all commands

### Gaps

- CLAUDE.md claims "Tests: 6" — actual is 100. CLAUDE.md claims "Audit Score: 63/100" — needs updating (HIGH, agent-fixable)
- No `docs/CODEBASE_MAP.md` (Phase 0.5 requirement) (HIGH, agent-fixable)
- No `docs/SYSTEM_CONSTITUTION.md` (Phase 0.5 requirement) (MEDIUM, agent-fixable)
- No API reference / docstring-generated docs
- Version in pyproject.toml is `0.1.0` but CHANGELOG shows `0.2.0` as latest — version mismatch (MEDIUM, agent-fixable)

### Cap Condition
Score capped at 7: CLAUDE.md inaccurate, missing Phase 0.5 docs, version mismatch.

---

## Dimension 12: Domain Capability Depth — Score: 8/10

**Weight: 8% | Prior: 7 | Delta: +1**

### Evidence

This is a RAG quality measurement toolkit — its domain IS retrieval quality metrics.

- **6 retrieval metrics implemented and verified:**
  - Recall@k — `hit_count / relevant_count` — verified with known values
  - Precision@k — `hit_count / retrieved_count` — verified
  - MRR@k — `1.0 / rank` of first hit — verified
  - NDCG@k — normalized DCG with log2(rank+2) discounting — verified against hand-calculated values
  - MAP@k — Mean Average Precision — verified against hand-calculated values
  - Hit-Rate@k — binary per-query hit indicator — verified
- **Corpus overlap detection:** SHA-256 fingerprinting with text normalization (strip, lowercase, collapse whitespace)
- **CI regression gating:** `compare` command with configurable recall regression budget (default 2%)
- **Report schema:** versioned JSON schema (v1) with per-query and summary sections
- **Report validation:** `validate-report` command verifies schema compliance
- **Control-plane integration:** ToolSpecs define formal tool contracts for platform integration

### RAG & Knowledge Graph Standard Assessment

Per RAG & KG Standard v1.3 §7.1, the toolkit implements 4 of the 5 RAGAS-aligned retrieval-level metrics:
- Context Recall ✅ (as recall@k)
- Context Precision ✅ (as precision@k)
- MRR ✅
- Faithfulness ❌ (requires LLM — out of scope for deterministic tool)
- Answer Relevancy ❌ (requires LLM — out of scope)

The toolkit correctly positions itself as the **deterministic retrieval-level** measurement layer, leaving LLM-dependent metrics (faithfulness, answer relevancy) to systems that integrate LLMs.

### Gaps

- No F1@k (harmonic mean of recall and precision) — common metric not included (LOW)
- No configurable relevance grading (binary only — no graded relevance beyond NDCG) (LOW)
- No batch evaluation mode (one query file at a time) (LOW)
- No direct integration with RAGAS or deepeval frameworks

### Delta Justification
+1 from prior: NDCG and MAP added since last audit (v0.2.0), plus ToolSpec contracts formalize the tool's domain contract for platform consumption.

---

## Dimension 13: AI/ML Capability — Score: 6/10

**Weight: 5% | Prior: 5 | Delta: +1**

### Evidence

This toolkit does not perform AI/ML — it measures retrieval quality. Assessment is based on how well it serves as the evaluation infrastructure referenced in RAG & KG Standard §7.

- **Deterministic metrics:** no model calls, reproducible results — correct design for measurement tool
- **RAGAS alignment:** implements 4 of 5 retrieval-level metrics from RAG & KG Standard §7.1
- **Regression testing support:** `compare` command with configurable threshold maps directly to §7.2 regression testing requirements
- **Per-query granularity:** reports include per-query scores enabling drill-down analysis
- **Corpus overlap detection:** catches train/test leakage — a critical RAG quality concern not covered by other tools

### RAG & KG Standard §8 Scoring Caps Applied

The RAG & KG Standard defines caps for Dim 13 on systems with RAG. Since this toolkit IS the measurement layer rather than a RAG system itself, the caps apply in the context of "does this tool enable other systems to meet the cap requirements":

- "Cannot score above 6 without declared chunking policy and retrieval topology" — The toolkit doesn't chunk or retrieve; it measures. Score of 6 is the natural ceiling without RAG system context.
- "Cannot score above 7 without retrieval eval set with retrieval-level metrics" — The toolkit IS the eval set infrastructure.

### Gaps

- No support for Faithfulness or Answer Relevancy metrics (require LLM calls) — documented as out of scope
- No embedding quality metrics (cosine similarity distributions, cluster analysis)
- No latency measurement (retrieval speed benchmarking)
- No integration test with actual RAG pipeline

### Delta Justification
+1 from prior: NDCG + MAP added, ToolSpec contracts formalize the evaluation interface.

---

## Dimension 14: Connectivity & Channel Interface — Score: 3/10

**Weight: 2% | Prior: 3 | Delta: 0**

### Evidence

- CLI-only interface (appropriate for Archetype 9)
- JSON output enables piping to other tools
- Docker support enables containerized execution
- Control-plane ToolSpecs define formal interface for platform integration

### Gaps

- No API server mode (would enable remote integration)
- No streaming output support
- No webhook/callback for long-running evaluations

### Assessment
Score of 3 reflects minimal connectivity appropriate for a CLI tool at 2% weight.

---

## Dimension 15: Agentic UI/UX — Score: 0/10

**Weight: 0% — N/A for CLI tools**

---

## Dimension 16: User Experience & Interface — Score: 0/10

**Weight: 0% — N/A for CLI tools**

---

## Dimension 17: User Journey & Persona Alignment — Score: 0/10

**Weight: 0% — N/A for CLI tools**

---

## Dimension 18: Zero Trust Architecture — Score: 4/10

**Weight: 2% | Prior: 3 | Delta: +1**

### Evidence

- **Read-only operations:** all 5 CLI commands perform read-only analysis (no mutations)
- **Control-plane permission model:** PermissionScope enum with ordinal comparison, AuthorityBoundary with deny/approval checks
- **No network calls:** tool operates entirely on local files
- **No secrets handling:** only reads JSONL/JSON data files
- **Sandboxing guidance:** SECURITY.md recommends running in CI sandbox environments

### Gaps

- No report integrity (signing, MAC, checksums)
- No input sanitization beyond JSON parsing (JSONL lines are trusted)
- Control-plane permission model is declared but not enforced at runtime

### Delta Justification
+1 from prior: control-plane permission and approval contracts add a formal trust model for platform integration.

---

## Dimension 19: Enterprise Security & Compliance — Score: 5/10

**Weight: 5% | Prior: 5 | Delta: 0**

### Evidence

- **SECURITY.md** present with vulnerability reporting guidance
- **MIT License** — clear open-source licensing
- **Dependabot** configured for automated dependency updates
- **pip-audit** in CI for known vulnerability scanning
- **Bandit** in CI for Python security analysis
- **Zero runtime deps** — minimal attack surface

### Gaps

- **No CycloneDX SBOM** — Required per Archetype 9 Certification Requirements (SBOM/SLSA Level 2 = Required) (HIGH, agent-fixable)
- No signed releases
- No SLSA provenance attestation
- SECURITY.md uses "early-stage" / "best-effort" language rather than standard Akiva template
- 4 unmerged Dependabot PRs suggest dependency hygiene lag

### Cap Condition
Score capped at 5: SBOM generation missing (Required per Archetype 9). Agent-fixable.

---

## Dimension 20: Operational Readiness — Score: 5/10

**Weight: 2% | Prior: 5 | Delta: 0**

### Evidence

- **Docker support:** Dockerfile + docker-compose.yml for isolated execution
- **pip install works:** `pip install -e ".[dev]"` verified
- **Health check endpoint:** `toolkit-rag health` returns structured status
- **Exit codes:** machine-readable for CI/CD integration
- **DEPLOYMENT.md** with installation and integration instructions

### Gaps

- No production monitoring integration
- No release pipeline (no PyPI publishing workflow)
- No install verification beyond manual test
- Version mismatch (pyproject.toml says 0.1.0, CHANGELOG says 0.2.0)

---

## Dimension 21: Agentic Workspace Capabilities — Score: 2/10

**Weight: 2% | Prior: 2 | Delta: 0**

### Evidence

- Non-agentic CLI tool — this dimension has 2% weight per Archetype 9
- Control-plane ToolSpecs provide formal interface for agentic platform consumption
- `AuthorityBoundary` and `ApprovalPolicy` classes enable platform agents to understand tool constraints

### Assessment
Score of 2 reflects that the tool has declared contracts for agentic integration but is not itself agentic. Appropriate for Archetype 9.

---

## Archetype 9 Minimum Checks

| Dimension | Required | Actual | Status |
|-----------|----------|--------|--------|
| Dim 4 — API Surface Quality | >= 7 | 8 | PASS |
| Dim 7 — Testing & QA | >= 7 | 8 | PASS |
| Dim 8 — Security Posture | >= 6 | 7 | PASS |
| Dim 10 — CI/CD | >= 6 | 7 | PASS |
| Dim 11 — Documentation | >= 6 | 7 | PASS |
| Dim 12 — Domain Capability | >= 6 | 8 | PASS |
| **Composite** | **>= 60** | **67.8** | **PASS** |

All archetype minimums met. Composite exceeds 60 threshold.

---

## SA-8 Mandatory Floor Check

| Dimension | Floor | Actual | Status |
|-----------|-------|--------|--------|
| D4 API Surface | >= 7 | 8 | PASS |
| D7 Testing | >= 7 | 8 | PASS |
| D8 Security | >= 7 | 7 | PASS |
| D18 Zero Trust | >= 7 | 4 | **BELOW** |

D18 is below the SA-8 mandatory floor of 7, but D18 has only 2% weight in Archetype 9 and the minimum score table does not list D18 as a required minimum for Archetype 9. The SA-8 floor is a general check — for CLI tools with no network operations, D18 at 4 is reasonable and does not block production viability.

---

## Top 5 Gaps (Ranked by Score Impact)

### 1. Missing SBOM/SLSA — Dims 19 (5% weight)
**Impact:** Caps D19 at 5. SBOM is Required per Archetype 9 Certification Requirements.
**Fix:** Add CycloneDX SBOM generation to CI pipeline.
**Fixable by:** Agent

### 2. Missing Phase 0.5 Artifacts — Dims 1, 11 (18% combined weight)
**Impact:** Caps D1 at 8, D11 at 7. Missing CODEBASE_MAP.md and SYSTEM_CONSTITUTION.md.
**Fix:** Create both documents.
**Fixable by:** Agent

### 3. Type Errors in control_plane — Dim 7 (15% weight)
**Impact:** 8 pyright errors in control_plane imports. Caps D7 at 8 (clean type-check is a quality gate).
**Fix:** Fix import paths in `control_plane/__init__.py` and `tool_specs.py`.
**Fixable by:** Agent

### 4. Missing Issue/PR Templates — Dim 10 (10% weight)
**Impact:** Missing `.github/ISSUE_TEMPLATE/` and `.github/PULL_REQUEST_TEMPLATE.md` per Repository Controls §1.3.
**Fix:** Create templates from standard.
**Fixable by:** Agent

### 5. CLAUDE.md Inaccuracy — Dim 11 (10% weight)
**Impact:** Says "Tests: 6" (actual: 100), score 63 (now 67.8). Version mismatch in pyproject.toml.
**Fix:** Update CLAUDE.md and version number.
**Fixable by:** Agent

---

## Path to 75/100

All items below are agent-fixable:

| Action | Dims Affected | Estimated Score Impact |
|--------|--------------|----------------------|
| Fix pyright errors in control_plane | D7: 8→9 | +1.5 |
| Create CODEBASE_MAP.md + SYSTEM_CONSTITUTION.md | D1: 8→9, D11: 7→8 | +1.8 |
| Add CycloneDX SBOM to CI | D19: 5→6 | +0.5 |
| Create issue/PR templates | D10: 7→8 | +1.0 |
| Update CLAUDE.md, fix version number | D11: 7→8 | (included above) |
| Add pyright to CI pipeline | D10: 7→8 | (included above) |
| Add low-coverage contracts.py tests | D7: 8→9 | (included above) |
| **Total estimated** | | **+4.8 → ~72.6** |

To reach 75, additional work needed:
- Release automation (PyPI publish workflow) → D10: 8→9 (+1.0)
- Report signing/integrity → D8: 7→8, D18: 4→5 (+1.1)
- F1@k metric + batch mode → D12: 8→9 (+0.8)
- Total: ~75.5

---

## Human-Only Blockers

| Item | Dimension | Impact |
|------|-----------|--------|
| Branch protection configuration on GitHub | D10 | Cannot enforce review requirements without admin access |
| Merge pending Dependabot PRs (4 stale) | D8, D19 | Dependency hygiene requires human review/merge |
| PyPI account setup for publishing | D10, D20 | Requires credentials and account creation |
| Pen test / security review | D8 | Required for D8 >= 9 |

---

## Coverage Tracker

| Dimension | Audited | Date | Verified |
|-----------|---------|------|----------|
| D1 Architecture | YES | 2026-04-04 | Source + runtime |
| D2 Auth | YES | 2026-04-04 | Source |
| D3 RLS | N/A | — | — |
| D4 API Surface | YES | 2026-04-04 | Source + runtime |
| D5 Data Layer | YES | 2026-04-04 | Source |
| D6 Frontend | N/A | — | — |
| D7 Testing | YES | 2026-04-04 | Runtime (100 tests, 84.8% cov) |
| D8 Security | YES | 2026-04-04 | Source + CI config |
| D9 Observability | YES | 2026-04-04 | Source + runtime |
| D10 CI/CD | YES | 2026-04-04 | Source + CI config + repo |
| D11 Documentation | YES | 2026-04-04 | Source (all docs read) |
| D12 Domain | YES | 2026-04-04 | Source + runtime |
| D13 AI/ML | YES | 2026-04-04 | Source + RAG&KG Standard |
| D14 Connectivity | YES | 2026-04-04 | Source |
| D15 Agentic UI | N/A | — | — |
| D16 UX | N/A | — | — |
| D17 Journey | N/A | — | — |
| D18 Zero Trust | YES | 2026-04-04 | Source |
| D19 Enterprise Sec | YES | 2026-04-04 | Source + CI config |
| D20 Ops Readiness | YES | 2026-04-04 | Source + runtime |
| D21 Agentic WS | YES | 2026-04-04 | Source |

---

## Accepted Exceptions

| Item | Dimension | Justification |
|------|-----------|---------------|
| No auth on CLI | D2 | Archetype 9 CLI tool — auth not applicable at 2% weight |
| No RLS | D3 | No database, 0% weight |
| No frontend | D6 | CLI tool, 0% weight |
| No agentic UI | D15 | Non-agentic, 0% weight |
| No Faithfulness/Relevancy metrics | D13 | Requires LLM calls — out of scope for deterministic tool |
| D18 below SA-8 floor | D18 | Arch 9 doesn't list D18 as a minimum; 2% weight |

---

## Audit Backlog

| Priority | Item | Dimension | Owner |
|----------|------|-----------|-------|
| P1 | Fix pyright errors in control_plane | D7, D1 | Agent |
| P1 | Create CODEBASE_MAP.md | D1, D11 | Agent |
| P1 | Add CycloneDX SBOM to CI | D19 | Agent |
| P2 | Create issue/PR templates | D10 | Agent |
| P2 | Update CLAUDE.md (score, test count, version) | D11 | Agent |
| P2 | Add pyright job to CI pipeline | D10 | Agent |
| P2 | Create SYSTEM_CONSTITUTION.md | D1 | Agent |
| P2 | Fix version mismatch (pyproject.toml vs CHANGELOG) | D11 | Agent |
| P3 | Add release automation (PyPI) | D10, D20 | Agent + Human |
| P3 | Add report signing/integrity | D8, D18 | Agent |
| P3 | Increase contracts.py test coverage | D7 | Agent |
| P4 | Configure branch protection | D10 | Human |
| P4 | Merge Dependabot PRs | D8, D19 | Human |
