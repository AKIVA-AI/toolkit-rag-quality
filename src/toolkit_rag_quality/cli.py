from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path

from . import __version__
from .compare import CompareBudget, compare_reports
from .io import read_json, read_jsonl, write_json
from .overlap import compute_overlap
from .report import RAGReport, write_report_json
from .retrieval import score_retrieval

logger = logging.getLogger(__name__)

EXIT_SUCCESS = 0
EXIT_CLI_ERROR = 2
EXIT_UNEXPECTED_ERROR = 3
EXIT_VALIDATION_FAILED = 4


def _cmd_score(args: argparse.Namespace) -> int:
    """Score retrieval results (recall/precision/MRR)."""
    queries_path = Path(args.queries).resolve()
    retrieved_path = Path(args.retrieved).resolve()
    k = int(args.k)
    
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
    
    print(json.dumps(report.to_dict(), indent=2, sort_keys=True))
    return EXIT_SUCCESS


def _cmd_overlap(args: argparse.Namespace) -> int:
    """Compute overlap/leakage between two corpora."""
    a_path = Path(args.a).resolve()
    b_path = Path(args.b).resolve()
    max_records = int(args.max_records)
    
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
    
    print(json.dumps(report, indent=2, sort_keys=True))
    return EXIT_SUCCESS


def _cmd_compare(args: argparse.Namespace) -> int:
    """Compare candidate report against baseline report."""
    baseline_path = Path(args.baseline).resolve()
    candidate_path = Path(args.candidate).resolve()
    
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
    
    print(json.dumps(result, indent=2, sort_keys=True))
    return EXIT_SUCCESS if result["passed"] else EXIT_VALIDATION_FAILED


def _cmd_validate_report(args: argparse.Namespace) -> int:
    """Validate a RAG report JSON has the expected shape."""
    report_path = Path(args.report).resolve()
    
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
    print(json.dumps(payload, indent=2, sort_keys=True))
    return EXIT_SUCCESS if ok else EXIT_VALIDATION_FAILED


def build_parser() -> argparse.ArgumentParser:
    """Build CLI argument parser."""
    p = argparse.ArgumentParser(
        prog="toolkit-rag",
        description="Toolkit RAG Quality Toolkit - Evaluate and monitor RAG system quality",
    )
    p.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    p.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Enable verbose logging (DEBUG level)",
    )
    sub = p.add_subparsers(dest="cmd", required=True)

    score = sub.add_parser("score", help="Score retrieval results (recall/precision/MRR).")
    score.add_argument("--queries", required=True, help="Queries JSONL (id, relevant_ids)")
    score.add_argument("--retrieved", required=True, help="Retrieved JSONL (id, retrieved_ids)")
    score.add_argument("--k", default="5", help="Top-k value for evaluation (default: 5)")
    score.add_argument("--out", default="", help="Optional output report JSON path")
    score.set_defaults(func=_cmd_score)

    overlap = sub.add_parser("overlap", help="Compute overlap/leakage between two corpora.")
    overlap.add_argument("--a", required=True, help="Corpus A JSONL (id, text)")
    overlap.add_argument("--b", required=True, help="Corpus B JSONL (id, text)")
    overlap.add_argument(
        "--max-records", default="50000", help="Max records to process (default: 50000)",
    )
    overlap.add_argument("--out", default="", help="Optional output report JSON path")
    overlap.set_defaults(func=_cmd_overlap)

    compare = sub.add_parser("compare", help="Compare candidate report against baseline report.")
    compare.add_argument("--baseline", required=True, help="Baseline report JSON file path")
    compare.add_argument("--candidate", required=True, help="Candidate report JSON file path")
    compare.add_argument(
        "--max-recall-regression-pct", default="2.0",
        help="Max recall regression %% (default: 2.0)",
    )
    compare.set_defaults(func=_cmd_compare)

    validate_report = sub.add_parser(
        "validate-report", help="Validate a RAG report JSON has the expected shape."
    )
    validate_report.add_argument(
        "--report", required=True, help="Report JSON file path to validate",
    )
    validate_report.set_defaults(func=_cmd_validate_report)

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
    
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.WARNING,
        format="%(asctime)s | %(levelname)-8s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        stream=sys.stderr,
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


