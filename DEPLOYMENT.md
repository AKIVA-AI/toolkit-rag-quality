# RAG Quality Toolkit - Deployment Guide

## ðŸš€ Quick Start

### Docker Deployment (Recommended)

```bash
cd rag-quality-toolkit
docker-compose up -d
docker-compose exec rag-quality toolkit-rag evaluate --config eval-config.json
```

### Local Installation

```bash
pip install -e ".[dev]"
toolkit-rag --version
pytest
```

## ðŸ”§ Configuration

See `.env.example` for all options.

**Key Settings:**
- `EVALUATE_RETRIEVAL`: Enable retrieval evaluation
- `EVALUATE_GENERATION`: Enable generation evaluation
- `EVALUATE_END_TO_END`: Enable end-to-end evaluation

## ðŸ“Š Production Deployment

### CI/CD Integration

```yaml
- name: Evaluate RAG Quality
  run: toolkit-rag evaluate --config $CONFIG_FILE
```

### Monitoring

```python
from toolkit_rag_quality.monitoring import get_health_status
status = get_health_status()
```

## ðŸ“ž Support

- Documentation: [README.md](README.md)
- Support: <support-email>



