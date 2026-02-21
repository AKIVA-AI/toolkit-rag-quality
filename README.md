# Toolkit RAG Quality Toolkit

A deterministic evaluation and QA utility for retrieval systems (RAG) without requiring model calls.

It focuses on enterprise-friendly metrics you can run in CI:

- **Retrieval metrics**: recall@k, precision@k, MRR, hit-rate@k
- **Corpus QA**: near-exact duplicate detection and overlap between corpora (leakage risk)
- **Reproducible reports**: JSON outputs suitable for gating

This is intentionally lightweight and safe to open source. A Pro version can add dashboards, policy enforcement, multi-tenant governance, and hosted storage for corpora and eval runs.

## Install (dev)

```bash
pip install -e ".[dev]"
pytest -q
```

## Quickstart

Score retrieval results:

```bash
toolkit-rag score --queries examples/queries.jsonl --retrieved examples/retrieved.jsonl --k 5 --out report.json
```

Check overlap/leakage between two corpora:

```bash
toolkit-rag overlap --a examples/corpus_a.jsonl --b examples/corpus_b.jsonl --out overlap.json
```

Compare candidate report to a baseline (CI gating):

```bash
toolkit-rag compare --baseline baseline.json --candidate report.json --max-recall-regression-pct 2.0
```

## Data formats

Queries JSONL (one per line):

```json
{"id":"q1","query":"...","relevant_ids":["doc-1","doc-9"]}
```

Retrieved JSONL (one per line):

```json
{"id":"q1","retrieved_ids":["doc-9","doc-2","doc-1"]}
```

Corpora JSONL (one per line):

```json
{"id":"doc-1","text":"..."}
```

## CLI Commands

- `score` - Score retrieval results against queries
- `overlap` - Check overlap/leakage between corpora
- `compare` - Compare reports for CI gating

## CI exit codes

- `compare`: `0` = passed, `4` = failed budgets

## License

MIT License - see LICENSE file for details.
