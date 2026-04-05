# RAG Quality — Deterministic retrieval metrics (recall@k, MRR, NDCG, MAP) without model calls

**Archetype:** 9 — Developer Tool / CLI Utility
**Standards:** Akiva Build Standard v2.14
**Ontology ID:** TK-04
**Version:** 0.2.0

## Stack

- Language: Python 3.10+
- Test: `pytest -xvs`
- Lint: `ruff check src/ tests/`
- Type check: `pyright src/`
- Build: `pip install -e .`

## Verification Commands

| Command | Purpose |
|---------|---------|
| `pytest -xvs` | Run tests |
| `ruff check src/ tests/` | Lint |
| `pyright src/` | Type check |
| `pytest --cov=toolkit_rag_quality --cov-report=term-missing` | Coverage |

## Current State

- Audit Score: 67.8/100 (2026-04-04, v2.14 baseline)
- Prior Score: 62.9/100 (2026-03-09)
- Tests: 125+
- Coverage: 84.8% (threshold: 70%)

## Key Rules

- Archetype 9: single-purpose CLI tool, zero runtime dependencies
- Tests first, security fixes before features
- One task at a time, verified before moving to next
- Deterministic output: same input must produce identical metrics
- Read-only operations: never modify source data files
- JSON-first: all commands produce structured JSON by default

## Learned Corrections

- pyright scope is `src/` only — tests use `sys.path` insertion via conftest.py which pyright cannot follow
- `from __future__ import annotations` + conditional class redefs causes pyright `reportAttributeAccessIssue` — define classes unconditionally, detect framework with `__import__()` instead
- control_plane contracts.py: always define PermissionScope/ApprovalPolicy/AuthorityBoundary/ToolSpec inline; only set `_HAS_EXECUTION_CONTRACTS` flag when framework is installed
