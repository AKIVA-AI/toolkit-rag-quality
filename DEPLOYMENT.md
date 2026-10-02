# RAG Quality Toolkit: deployment guide

The toolkit is a command-line tool with no service component. "Deploying" it means installing it where your CI job runs.

## Local installation (from source)

```bash
pip install -e ".[dev]"
toolkit-rag --version
pytest
```

## Docker

```bash
docker-compose up -d
docker-compose exec rag-quality toolkit-rag score --queries /app/evaluations/queries.jsonl --retrieved /app/evaluations/retrieved.jsonl --out /app/reports/report.json
```

The compose file mounts `./evaluations` and `./reports` into the container.

## Configuration

There are no environment variables or config files. All options are CLI flags; run `toolkit-rag <command> --help`. Use `--verbose` for debug logging and `--log-format json` for structured logs on stderr.

## CI integration

```yaml
- name: Score retrieval
  run: toolkit-rag score --queries queries.jsonl --retrieved retrieved.jsonl --k 5 --out report.json

- name: Gate on regression
  run: toolkit-rag compare --baseline baseline.json --candidate report.json --max-recall-regression-pct 2.0
```

`compare` exits `4` when any gated metric regresses beyond its budget or the two reports are not comparable (different k, relevance level or query set), which fails the job. For a ready-made step with a Markdown summary, use the composite action in `action.yml` (see the README's GitHub Action section).

## Support

- Documentation: [README.md](README.md)
- Issues: https://github.com/AKIVA-AI/toolkit-rag-quality/issues
