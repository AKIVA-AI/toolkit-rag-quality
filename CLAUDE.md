# toolkit-rag-quality: guidance for coding agents

Deterministic retrieval metrics, regression gating and corpus leakage checks, shipped as the `toolkit-rag` CLI. Python 3.10+, no runtime dependencies (optional extras: `langchain`, `llamaindex`).

## Commands

| Command | Purpose |
|---|---|
| `pip install -e ".[dev]"` | Install for development |
| `pytest -q` | Tests |
| `ruff check .` | Lint (CI runs exactly this) |
| `ruff format --check src tests` | Format check |
| `pyright src/` | Type check (CI scope is `src/` only) |
| `pytest --cov=toolkit_rag_quality --cov-report=term-missing` | Coverage (floor 70%, set in `pyproject.toml`) |

## Layout

- `src/toolkit_rag_quality/retrieval.py`: `score_run` / `score_retrieval` and the per-query metrics.
- `src/toolkit_rag_quality/formats.py`: qrels and runs in JSONL, TREC and BEIR formats.
- `src/toolkit_rag_quality/compare.py`: `compare_reports` regression gate (budgets, per-query diff, significance) and `CompareBudget`.
- `src/toolkit_rag_quality/stats.py`: paired randomization test and paired t-test; reference values from SciPy in `tests/test_stats.py`.
- `src/toolkit_rag_quality/overlap.py`: exact-duplicate overlap via normalized SHA-256.
- `src/toolkit_rag_quality/leakage.py`: shingles, MinHash-LSH near-duplicates (exact Jaccard verification) and exact containment leakage.
- `src/toolkit_rag_quality/report.py`: `RAGReport`, loading envelope or legacy reports.
- `src/toolkit_rag_quality/envelope.py`: report envelope v1 (in-toto Statement), canonical JSON, validation. Must agree with `schemas/report-envelope.v1.json` (tested).
- `src/toolkit_rag_quality/io.py`: JSON/JSONL reading and path-validated writing.
- `src/toolkit_rag_quality/adapters.py`: `run_retriever` for LangChain / LlamaIndex / callables. Never import those libraries here; they are optional extras, tested in the CI `adapters` job.
- `action.yml`: composite GitHub Action for `compare`; exercised by the CI `action` job with `tests/fixtures/action/`.
- `src/toolkit_rag_quality/cli.py`: argparse entry point and exit codes.
- `tests/test_trec_reference.py`, `tests/test_graded_reference.py`: expected values computed with pytrec_eval and hard-coded.

## Conventions

- No runtime dependencies. Output must be deterministic for the same input.
- Metric semantics follow trec_eval at cutoff k. Any metric change needs a known-value test, and the trec_eval reference test must stay green. To add reference cases, compute them with `pytrec-eval-terrier` and hard-code the numbers; do not add it as a test dependency.
- Never drop or truncate input silently: count it in the report and log a warning, or reject it with an error.
- Exit codes are a contract: 0 success, 2 CLI/input error, 3 unexpected error, 4 gate or validation failure.
- Reports are envelopes (`docs/report-envelope.md`), written as canonical JSON. `docs/report-envelope.md` and `schemas/report-envelope.v1.json` are shared verbatim across the toolkit repos: do not edit them here alone.
- Write output files only through `io.write_text` / `io.write_json`, and pass the path unresolved so its `..` check works.
- pyright runs on `src/` only, because tests import the package through the `sys.path` insertion in `tests/conftest.py`.
