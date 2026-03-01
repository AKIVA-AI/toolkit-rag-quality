# RAG Quality Toolkit - Deployment Guide

## Quick Start

### Docker Deployment (Recommended)

```bash
docker-compose up -d
docker-compose exec rag-quality toolkit-rag score --queries /app/evaluations/queries.jsonl --retrieved /app/evaluations/retrieved.jsonl --out /app/reports/report.json
```

### Local Installation

```bash
pip install -e ".[dev]"
toolkit-rag --version
pytest
```

## Configuration

See `.env.example` for all options.

**Key Settings:**

- `LOG_LEVEL`: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)

## Production Deployment

### CI/CD Integration

```yaml
- name: Score RAG Retrieval
  run: toolkit-rag score --queries queries.jsonl --retrieved retrieved.jsonl --k 5 --out report.json

- name: Gate on Recall Regression
  run: toolkit-rag compare --baseline baseline.json --candidate report.json --max-recall-regression-pct 2.0
```

### Monitoring

```python
from toolkit_rag_quality.monitoring import get_health_status
status = get_health_status()
```

## Support

- Documentation: [README.md](README.md)
