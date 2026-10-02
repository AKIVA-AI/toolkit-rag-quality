# Contributing to toolkit-rag-quality

Thanks for helping. For a large change, please open an issue first so we can
agree on the approach.

## Development setup

```bash
git clone https://github.com/AKIVA-AI/toolkit-rag-quality.git
cd toolkit-rag-quality
python -m venv .venv && . .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -e ".[dev]"
```

## Checks

CI runs these on every pull request; run them before you push:

```bash
pytest
ruff check .
pyright src/
```

CI also runs `bandit -r src/`, `pip-audit` with every optional extra installed,
and builds the sdist and wheel (`twine check --strict`).

## Pull requests

1. Branch from `main`.
2. Write a failing test first, then the change. Tests should exercise real
   behavior (real input files, real CLI calls), not only construction.
3. Update the README for user-visible behavior and add a `CHANGELOG.md` entry
   under `[Unreleased]`.
4. Keep the core free of runtime dependencies; optional features go
   in an extra in `pyproject.toml`.
5. Open the pull request against `main` and fill in the template.

## Project conventions

- Output must be deterministic for the same input.
- Metric semantics follow trec_eval at cutoff k; any metric change needs a
  known-value test, and the trec_eval reference tests must stay green.
- Never drop or truncate input silently: count it in the report and warn, or
  reject it with an error.
- The adapter tests need `pip install -e ".[dev,langchain,llamaindex]"`.

## Conduct, security and license

- Everyone taking part follows the [Code of Conduct](CODE_OF_CONDUCT.md).
- Report security problems privately as described in [SECURITY.md](SECURITY.md),
  not in a public issue.
- Contributions are accepted under the Apache License 2.0 ([LICENSE](LICENSE)):
  by opening a pull request you agree that your contribution is licensed under
  it, as section 5 of the license describes.
- Maintainers: releases are described in [RELEASING.md](RELEASING.md).
