# RAG Quality Toolkit - Quick Start

## ðŸš€ Installation

```bash
pip install -e ".[dev]"
toolkit-rag --version
```

## ðŸ“ Basic Usage

```bash
# Evaluate RAG system
toolkit-rag evaluate --config eval-config.json --out report.json
```

## ðŸ³ Docker Usage

```bash
docker-compose up -d
docker-compose exec rag-quality toolkit-rag evaluate --config /app/eval-config.json
```

## ðŸ“š Next Steps

- Read [README.md](README.md)
- Check [DEPLOYMENT.md](DEPLOYMENT.md)

---

**Ready to evaluate RAG quality!** ðŸš€


