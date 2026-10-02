# RAG Quality Toolkit: quick start

## Install

```bash
pip install toolkit-rag-quality
toolkit-rag --version
```

## Basic usage

```bash
# Score retrieval results
toolkit-rag score --queries queries.jsonl --retrieved retrieved.jsonl --k 5 --out report.json

# Count exact duplicates between two corpora
toolkit-rag overlap --a corpus_a.jsonl --b corpus_b.jsonl --out overlap.json

# Compare a candidate report to a baseline (CI gating)
toolkit-rag compare --baseline baseline.json --candidate report.json --max-recall-regression-pct 2.0

# Check a report's shape
toolkit-rag validate-report --report report.json
```

## Docker

From a clone of the repository:

```bash
docker-compose up -d
docker-compose exec rag-quality toolkit-rag score --queries /app/evaluations/queries.jsonl --retrieved /app/evaluations/retrieved.jsonl --out /app/reports/report.json
```

## Next steps

- [README.md](README.md) for metric definitions, input handling and exit codes
- [DEPLOYMENT.md](DEPLOYMENT.md) for CI integration
