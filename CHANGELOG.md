# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.2.0] - 2026-03-09

### Added
- NDCG@k (Normalized Discounted Cumulative Gain) metric in retrieval scoring
- MAP@k (Mean Average Precision) metric in retrieval scoring
- `health` CLI subcommand for system health checks
- `--format` flag (json, table) on all subcommands
- `--log-format` flag (text, json) for structured JSON logging
- Security scanning in CI (bandit + pip-audit)
- Dependabot configuration for dependency updates
- Pre-commit configuration (ruff, pyright)
- Comprehensive tests for monitoring, overlap, retrieval, and compare modules

### Changed
- Coverage threshold raised from 60% to 70%
- Monitoring module refactored: removed module-level singleton, added `get_health_status()` API

### Fixed
- `monitoring.py` was entirely unwired and untested — now wired into CLI via `health` subcommand

## [0.1.0] - 2026-03-08

### Added
- Initial release
- 4 CLI subcommands: `score`, `overlap`, `compare`, `validate-report`
- Recall@k, Precision@k, MRR@k, Hit-Rate@k metrics
- Corpus overlap detection with SHA-256 fingerprinting
- CI gating via configurable recall regression budget
- Report validation with schema versioning
- Docker support (Dockerfile + docker-compose.yml)
- GitHub Actions CI pipeline (test, lint, build)
