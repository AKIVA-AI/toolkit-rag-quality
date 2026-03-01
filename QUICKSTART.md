# RAG Quality Toolkit - Quick Start

## Installation

```bash
pip install -e ".[dev]"
toolkit-rag --version
```

## Basic Usage

```bash
# Score retrieval results
toolkit-rag score --queries queries.jsonl --retrieved retrieved.jsonl --k 5 --out report.json

# Check overlap/leakage between two corpora
toolkit-rag overlap --a corpus_a.jsonl --b corpus_b.jsonl --out overlap.json

# Compare candidate report to baseline (CI gating)
toolkit-rag compare --baseline baseline.json --candidate report.json --max-recall-regression-pct 2.0

# Validate a report file
toolkit-rag validate-report --report report.json
```

## Docker Usage

```bash
docker-compose up -d
docker-compose exec rag-quality toolkit-rag score --queries /app/evaluations/queries.jsonl --retrieved /app/evaluations/retrieved.jsonl --out /app/reports/report.json
```

## Next Steps

- Read [README.md](README.md)
- Check [DEPLOYMENT.md](DEPLOYMENT.md)
