# toolkit-rag-quality -- Codebase Map

**Created:** 2026-04-04
**Updated:** 2026-04-04
**System:** toolkit-rag-quality (Archetype 9 -- Developer Tool / CLI)
**Ontology ID:** TK-04
**Audit Score:** 67.8/100 (2026-04-04, v2.14 baseline)
**Purpose:** Deterministic RAG retrieval quality metrics (recall@k, precision@k, MRR@k, NDCG@k, MAP@k, hit-rate@k) without model calls. AI-readable structural map of the live repository.

---

## Directory Structure

```text
toolkit-rag-quality/
|-- src/
|   `-- toolkit_rag_quality/              # 11 Python source files, 1,319 LOC
|       |-- __init__.py                   # Public API exports (21 LOC)
|       |-- __main__.py                   # python -m entry point (7 LOC)
|       |-- cli.py                        # argparse CLI: score, overlap, compare, validate-report, health (373 LOC)
|       |-- retrieval.py                  # 6 metrics: recall@k, precision@k, MRR@k, NDCG@k, MAP@k, hit-rate@k (135 LOC)
|       |-- overlap.py                    # SHA-256 corpus overlap detection (41 LOC)
|       |-- compare.py                    # Baseline vs candidate regression gating (37 LOC)
|       |-- report.py                     # RAGReport dataclass with schema versioning (33 LOC)
|       |-- io.py                         # JSONL/JSON reading, path validation (166 LOC)
|       |-- monitoring.py                 # HealthCheck, Metrics classes (71 LOC)
|       |-- py.typed                      # PEP 561 marker
|       `-- control_plane/                # Platform integration contracts (435 LOC)
|           |-- __init__.py               # Module exports (47 LOC)
|           |-- config.py                 # 3-tier config hierarchy (107 LOC)
|           |-- contracts.py              # PermissionScope, ApprovalPolicy, AuthorityBoundary, ToolSpec (119 LOC)
|           `-- tool_specs.py             # CLI command -> ToolSpec mapping (162 LOC)
|-- tests/                                # 8 test modules, 100 tests, 1,214 LOC
|   |-- conftest.py
|   |-- test_cli.py                       # 3 tests
|   |-- test_cli_new_features.py          # 15 tests
|   |-- test_control_plane.py             # 31 tests
|   |-- test_enhancements.py              # 22 tests
|   |-- test_monitoring.py                # 8 tests
|   |-- test_overlap.py                   # 10 tests
|   `-- test_retrieval_and_compare.py     # 13 tests
|-- docs/
|   |-- CODEBASE_MAP.md                   # This file
|   `-- audits/                           # Audit reports
|-- .github/
|   |-- workflows/ci.yml                  # CI: test matrix (3.10/3.11/3.12), lint, security, build
|   `-- dependabot.yml
|-- .env.example
|-- .gitignore
|-- .pre-commit-config.yaml
|-- CLAUDE.md
|-- README.md
|-- LICENSE                               # MIT
|-- SECURITY.md
|-- CONTRIBUTING.md
|-- CHANGELOG.md
|-- DEPLOYMENT.md
|-- QUICKSTART.md
|-- Dockerfile                            # python:3.11-slim base
|-- docker-compose.yml
|-- pyproject.toml                        # CLI entry: toolkit-rag (scripts)
`-- requirements-dev.txt
```

---

## Core Modules

| Module | Responsibility |
|--------|---------------|
| `cli.py` | CLI entry point; `score`, `overlap`, `compare`, `validate-report`, `health` sub-commands |
| `retrieval.py` | `score_retrieval()` -- computes recall@k, precision@k, MRR@k, NDCG@k, MAP@k, hit-rate@k |
| `overlap.py` | `compute_overlap()` -- SHA-256-based corpus overlap detection between datasets |
| `compare.py` | `compare_reports()` -- baseline vs candidate regression gate using `CompareBudget` |
| `report.py` | `RAGReport` dataclass with schema versioning and JSON serialization |
| `io.py` | JSONL/JSON file reading, path validation, input normalization |
| `monitoring.py` | `HealthCheck` and `Metrics` classes for operational monitoring |
| `control_plane/config.py` | 3-tier config hierarchy (defaults, file, env) |
| `control_plane/contracts.py` | `PermissionScope`, `ApprovalPolicy`, `AuthorityBoundary`, `ToolSpec` dataclasses |
| `control_plane/tool_specs.py` | Maps CLI commands to `ToolSpec` contracts for platform integration |

---

## Public API

Exported from `__init__.py`:

| Symbol | Type |
|--------|------|
| `__version__` | `str` |
| `CompareBudget` | dataclass |
| `compare_reports` | function |
| `compute_overlap` | function |
| `score_retrieval` | function |

CLI entry point: `toolkit-rag` (configured in `pyproject.toml` scripts).

---

## Test Coverage

| Suite | Files | Tests |
|-------|-------|-------|
| All tests | 8 modules | 100 |
| Coverage | -- | 84.8% (threshold 70%) |

---

## Data Flow

```
queries.jsonl       <- {query_id, retrieved_ids: [...], relevant_ids: [...]} per line

score (retrieval.py)
  -> recall@k, precision@k, MRR@k, NDCG@k, MAP@k, hit-rate@k per query
  -> RAGReport (report.py)

overlap (overlap.py)
  -> SHA-256 set intersection between corpus A and corpus B

compare (compare.py)
  -> pass/fail       <- regression within CompareBudget tolerance
```

---

## Dependencies

**Runtime:** zero (stdlib only).

**Dev only (4):** pytest, pytest-cov, ruff, pyright.

---

## CI/CD

- **GitHub Actions:** test matrix across Python 3.10, 3.11, 3.12; lint (ruff); security scan; build check
- **Docker:** `python:3.11-slim` base image
- **Pre-commit:** configured via `.pre-commit-config.yaml`
- **No release automation** -- no PyPI publish workflow

---

## Known Gaps

- No `SYSTEM_CONSTITUTION.md` yet
- Version mismatch: `pyproject.toml` says 0.1.0, `CHANGELOG.md` says 0.2.0
- `monitoring.py` singleton is not thread-safe
- No release automation (no PyPI publish workflow)
