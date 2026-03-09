from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path
from typing import Any

from . import __version__
from .compare import CompareBudget, compare_reports
from .io import read_json, read_jsonl, write_json
from .monitoring import format_health_output, get_health_status
from .overlap import compute_overlap
from .report import RAGReport, write_report_json
from .retrieval import score_retrieval

logger = logging.getLogger(__name__)

EXIT_SUCCESS = 0
EXIT_CLI_ERROR = 2
EXIT_UNEXPECTED_ERROR = 3
EXIT_VALIDATION_FAILED = 4


class _JsonLogFormatter(logging.Formatter):
    """Structured JSON log formatter."""

    def format(self, record: logging.LogRecord) -> str:
        log_entry: dict[str, Any] = {
            "timestamp": self.formatTime(record, self.datefmt),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        if record.exc_info and record.exc_info[1] is not None:
            log_entry["exception"] = self.formatException(record.exc_info)
        return json.dumps(log_entry, sort_keys=True)


def _format_output(data: Any, fmt: str) -> str:
    """Format output data as JSON or table.

    Args:
        data: Data to format (dict or list).
        fmt: Output format — "json" or "table".

    Returns:
        Formatted string.
    """
    if fmt == "table":
        return _format_table(data)
    return json.dumps(data, indent=2, sort_keys=True)


def _format_table(data: Any) -> str:
    """Format data as a simple text table."""
    if isinstance(data, dict):
        lines: list[str] = []
        max_key_len = max((len(str(k)) for k in data), default=0)
        for k, v in sorted(data.items()):
            if isinstance(v, dict):
                lines.append(f"{k}:")
                for sk, sv in sorted(v.items()):
                    lines.append(f"  {str(sk):<{max_key_len}}  {sv}")
            elif isinstance(v, list):
                lines.append(f"{k}: [{len(v)} items]")
            else:
                lines.append(f"{str(k):<{max_key_len}}  {v}")
        return "\n".join(lines)
    return str(data)


def _get_format(args: argparse.Namespace) -> str:
    """Get output format from args, defaulting to json."""
    return str(getattr(args, "format", "json") or "json")


def _cmd_score(args: argparse.Namespace) -> int:
    """Score retrieval results (recall/precision/MRR/NDCG/MAP)."""
    queries_path = Path(args.queries).resolve()
    retrieved_path = Path(args.retrieved).resolve()
    k = int(args.k)
    fmt = _get_format(args)

    logger.info(f"Scoring retrieval results with k={k}")
    logger.debug(f"Queries: {queries_path}")
    logger.debug(f"Retrieved: {retrieved_path}")

    try:
        queries = list(read_jsonl(queries_path))
        logger.info(f"Loaded {len(queries)} queries")
    except (ValueError, FileNotFoundError, PermissionError) as e:
        logger.error(f"Failed to read queries: {e}")
        return EXIT_CLI_ERROR

    try:
        retrieved = list(read_jsonl(retrieved_path))
        logger.info(f"Loaded {len(retrieved)} retrieved results")
    except (ValueError, FileNotFoundError, PermissionError) as e:
        logger.error(f"Failed to read retrieved: {e}")
        return EXIT_CLI_ERROR

    try:
        report = score_retrieval(queries=queries, retrieved=retrieved, k=k)
        logger.info("Scoring completed successfully")
    except Exception as e:
        logger.error(f"Failed to score retrieval: {e}")
        return EXIT_CLI_ERROR

    if args.out:
        out = Path(args.out).resolve()
        try:
            write_report_json(report, out)
            logger.info(f"Wrote report to: {out}")
        except (OSError, PermissionError, ValueError) as e:
            logger.error(f"Failed to write report: {e}")
            return EXIT_CLI_ERROR

    print(_format_output(report.to_dict(), fmt))
    return EXIT_SUCCESS


def _cmd_overlap(args: argparse.Namespace) -> int:
    """Compute overlap/leakage between two corpora."""
    a_path = Path(args.a).resolve()
    b_path = Path(args.b).resolve()
    max_records = int(args.max_records)
    fmt = _get_format(args)

    logger.info(f"Computing overlap (max_records={max_records})")
    logger.debug(f"Corpus A: {a_path}")
    logger.debug(f"Corpus B: {b_path}")

    try:
        a = list(read_jsonl(a_path))
        logger.info(f"Loaded {len(a)} records from corpus A")
    except (ValueError, FileNotFoundError, PermissionError) as e:
        logger.error(f"Failed to read corpus A: {e}")
        return EXIT_CLI_ERROR

    try:
        b = list(read_jsonl(b_path))
        logger.info(f"Loaded {len(b)} records from corpus B")
    except (ValueError, FileNotFoundError, PermissionError) as e:
        logger.error(f"Failed to read corpus B: {e}")
        return EXIT_CLI_ERROR

    try:
        report = compute_overlap(a=a, b=b, max_records=max_records)
        logger.info("Overlap computation completed")
    except Exception as e:
        logger.error(f"Failed to compute overlap: {e}")
        return EXIT_CLI_ERROR

    if args.out:
        out = Path(args.out).resolve()
        try:
            write_json(out, report)
            logger.info(f"Wrote report to: {out}")
        except (OSError, PermissionError, ValueError) as e:
            logger.error(f"Failed to write report: {e}")
            return EXIT_CLI_ERROR

    print(_format_output(report, fmt))
    return EXIT_SUCCESS


def _cmd_compare(args: argparse.Namespace) -> int:
    """Compare candidate report against baseline report."""
    baseline_path = Path(args.baseline).resolve()
    candidate_path = Path(args.candidate).resolve()
    fmt = _get_format(args)

    logger.info("Comparing reports")
    logger.debug(f"Baseline: {baseline_path}")
    logger.debug(f"Candidate: {candidate_path}")

    try:
        baseline_obj = read_json(baseline_path)
        baseline = RAGReport.from_dict(baseline_obj)
        logger.info("Loaded baseline report")
    except (ValueError, FileNotFoundError, PermissionError) as e:
        logger.error(f"Failed to read baseline: {e}")
        return EXIT_CLI_ERROR

    try:
        candidate_obj = read_json(candidate_path)
        candidate = RAGReport.from_dict(candidate_obj)
        logger.info("Loaded candidate report")
    except (ValueError, FileNotFoundError, PermissionError) as e:
        logger.error(f"Failed to read candidate: {e}")
        return EXIT_CLI_ERROR

    try:
        budget = CompareBudget(max_recall_regression_pct=float(args.max_recall_regression_pct))
        result = compare_reports(baseline=baseline, candidate=candidate, budget=budget)

        if result["passed"]:
            logger.info("Comparison passed")
        else:
            logger.error("Comparison failed: recall regression exceeds budget")

    except Exception as e:
        logger.error(f"Failed to compare reports: {e}")
        return EXIT_CLI_ERROR

    print(_format_output(result, fmt))
    return EXIT_SUCCESS if result["passed"] else EXIT_VALIDATION_FAILED


def _cmd_validate_report(args: argparse.Namespace) -> int:
    """Validate a RAG report JSON has the expected shape."""
    report_path = Path(args.report).resolve()
    fmt = _get_format(args)

    logger.info(f"Validating report: {report_path}")

    try:
        obj = read_json(report_path)
    except (ValueError, FileNotFoundError, PermissionError) as e:
        logger.error(f"Failed to read report: {e}")
        return EXIT_CLI_ERROR

    ok = (
        isinstance(obj, dict)
        and isinstance(obj.get("summary"), dict)
        and isinstance(obj.get("per_query"), list)
    )

    if ok:
        logger.info("Report validation passed")
    else:
        logger.error("Report validation failed: missing 'summary' dict or 'per_query' list")

    payload = {"ok": ok, "schema": "toolkit_rag_report", "schema_version": 1}
    print(_format_output(payload, fmt))
    return EXIT_SUCCESS if ok else EXIT_VALIDATION_FAILED


def _cmd_health(args: argparse.Namespace) -> int:
    """Show system health status."""
    fmt = _get_format(args)
    status = get_health_status()
    print(_format_output(status, fmt) if fmt != "json" else format_health_output(status))
    return EXIT_SUCCESS


def _add_format_arg(parser: argparse.ArgumentParser) -> None:
    """Add --format flag to a subcommand parser."""
    parser.add_argument(
        "--format",
        choices=["json", "table"],
        default="json",
        help="Output format (default: json)",
    )


def build_parser() -> argparse.ArgumentParser:
    """Build CLI argument parser."""
    p = argparse.ArgumentParser(
        prog="toolkit-rag",
        description="RAG Quality Toolkit - Evaluate and monitor RAG system quality",
    )
    p.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    p.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Enable verbose logging (DEBUG level)",
    )
    p.add_argument(
        "--log-format",
        choices=["text", "json"],
        default="text",
        help="Log output format (default: text)",
    )
    sub = p.add_subparsers(dest="cmd", required=True)

    score = sub.add_parser("score", help="Score retrieval results (recall/precision/MRR/NDCG/MAP).")
    score.add_argument("--queries", required=True, help="Queries JSONL (id, relevant_ids)")
    score.add_argument("--retrieved", required=True, help="Retrieved JSONL (id, retrieved_ids)")
    score.add_argument("--k", default="5", help="Top-k value for evaluation (default: 5)")
    score.add_argument("--out", default="", help="Optional output report JSON path")
    _add_format_arg(score)
    score.set_defaults(func=_cmd_score)

    overlap = sub.add_parser("overlap", help="Compute overlap/leakage between two corpora.")
    overlap.add_argument("--a", required=True, help="Corpus A JSONL (id, text)")
    overlap.add_argument("--b", required=True, help="Corpus B JSONL (id, text)")
    overlap.add_argument(
        "--max-records",
        default="50000",
        help="Max records to process (default: 50000)",
    )
    overlap.add_argument("--out", default="", help="Optional output report JSON path")
    _add_format_arg(overlap)
    overlap.set_defaults(func=_cmd_overlap)

    compare = sub.add_parser("compare", help="Compare candidate report against baseline report.")
    compare.add_argument("--baseline", required=True, help="Baseline report JSON file path")
    compare.add_argument("--candidate", required=True, help="Candidate report JSON file path")
    compare.add_argument(
        "--max-recall-regression-pct",
        default="2.0",
        help="Max recall regression %% (default: 2.0)",
    )
    _add_format_arg(compare)
    compare.set_defaults(func=_cmd_compare)

    validate_report = sub.add_parser(
        "validate-report", help="Validate a RAG report JSON has the expected shape."
    )
    validate_report.add_argument(
        "--report",
        required=True,
        help="Report JSON file path to validate",
    )
    _add_format_arg(validate_report)
    validate_report.set_defaults(func=_cmd_validate_report)

    health = sub.add_parser("health", help="Show system health status.")
    _add_format_arg(health)
    health.set_defaults(func=_cmd_health)

    return p


def main(argv: list[str] | None = None) -> int:
    """Main entry point for CLI.

    Args:
        argv: Command line arguments (defaults to sys.argv)

    Returns:
        Exit code (0 = success, non-zero = error)
    """
    parser = build_parser()
    args = parser.parse_args(argv)

    log_format: str = getattr(args, "log_format", "text") or "text"
    handler = logging.StreamHandler(sys.stderr)
    if log_format == "json":
        handler.setFormatter(_JsonLogFormatter(datefmt="%Y-%m-%dT%H:%M:%S"))
    else:
        handler.setFormatter(
            logging.Formatter(
                fmt="%(asctime)s | %(levelname)-8s | %(message)s",
                datefmt="%Y-%m-%d %H:%M:%S",
            )
        )

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.WARNING,
        handlers=[handler],
    )

    try:
        return int(args.func(args))
    except (ValueError, FileNotFoundError, PermissionError) as e:
        logger.error(f"{type(e).__name__}: {e}")
        return EXIT_CLI_ERROR
    except KeyboardInterrupt:
        logger.warning("Interrupted by user")
        return EXIT_UNEXPECTED_ERROR
    except Exception as e:
        logger.exception(f"Unexpected error: {e}")
        print(
            "\nAn unexpected error occurred. Please report this issue.",
            file=sys.stderr,
        )
        return EXIT_UNEXPECTED_ERROR
