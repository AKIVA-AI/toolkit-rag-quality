from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path
from typing import Any

from . import __version__
from .adapters import FRAMEWORKS, load_object, query_texts, run_retriever
from .compare import SIGNIFICANCE_TESTS, CompareBudget, compare_reports, metric_name
from .envelope import (
    PREDICATE_TYPE,
    TOOL_NAME,
    build_envelope,
    canonical_json,
    is_envelope,
    resource,
    validate_envelope,
)
from .formats import (
    QRELS_FORMATS,
    RUN_FORMATS,
    load_qrels,
    load_run,
    write_qrels,
    write_run,
)
from .io import read_json, read_jsonl, write_json, write_text
from .leakage import (
    DEFAULT_CONTAINMENT_SHINGLE,
    DEFAULT_CONTAINMENT_THRESHOLD,
    DEFAULT_NEAR_DUP_SHINGLE,
    DEFAULT_NEAR_DUP_THRESHOLD,
    DEFAULT_NUM_PERM,
    containment_leaks,
    near_duplicates,
)
from .overlap import compute_overlap
from .report import RAGReport, load_report, validate_score_report
from .retrieval import score_run

logger = logging.getLogger(__name__)

EXIT_SUCCESS = 0
EXIT_CLI_ERROR = 2
EXIT_UNEXPECTED_ERROR = 3
EXIT_VALIDATION_FAILED = 4

_INPUT_ERRORS = (ValueError, FileNotFoundError, PermissionError, OSError, UnicodeDecodeError)


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
    """Format a plain (non-envelope) payload as JSON, a text table or Markdown."""
    if fmt == "table":
        return _format_table(data)
    if fmt == "markdown":
        return _format_markdown(data)
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


def _flatten(data: dict[str, Any], prefix: str = "") -> list[tuple[str, Any]]:
    rows: list[tuple[str, Any]] = []
    for k, v in sorted(data.items()):
        key = f"{prefix}{k}"
        if isinstance(v, dict):
            rows.extend(_flatten(v, prefix=f"{key}."))
        elif isinstance(v, list):
            rows.append((key, f"[{len(v)} items]"))
        else:
            rows.append((key, v))
    return rows


def _format_markdown(data: Any, title: str = "") -> str:
    """Format a dict as a two-column Markdown table."""
    if not isinstance(data, dict):
        return str(data)
    lines = [f"### {title}", ""] if title else []
    lines += ["| field | value |", "|---|---|"]
    for key, value in _flatten(data):
        if isinstance(value, float):
            value = f"{value:.4f}"
        lines.append(f"| {key} | {value} |")
    return "\n".join(lines)


def _num(value: Any, fmt: str = ".4f") -> str:
    if value is None:
        return "-"
    if isinstance(value, bool):
        return "yes" if value else "no"
    if isinstance(value, float):
        return format(value, fmt)
    return str(value)


def _compare_markdown(pred: dict[str, Any], title: str) -> str:
    """Markdown summary of a compare report (used for CI step summaries)."""
    summ = pred["summary"]
    lines = [f"### {title}", ""]
    lines.append(
        f"Reason: `{summ.get('reason')}`. Queries compared: {summ.get('queries_compared')}."
    )
    alpha = summ.get("alpha")
    if alpha is not None:
        lines.append(f"Significance: {summ.get('test')} test, alpha = {alpha}.")
    lines += [
        "",
        "| metric | baseline | candidate | change % | budget % | p-value | worse / better "
        "| result |",
        "|---|---|---|---|---|---|---|---|",
    ]
    per_query = summ.get("per_query") or {}
    for name, m in (summ.get("metrics") or {}).items():
        pct = m.get("regression_pct")
        change = "-" if pct is None else f"{-pct:+.2f}"
        wb = per_query.get(name)
        counts = f"{wb['worse']} / {wb['better']}" if wb else "-"
        budget = m.get("max_regression_pct")
        result = "pass" if m.get("passed") else "**FAIL**"
        if m.get("passed") and m.get("over_budget"):
            result = "pass (not significant)"
        lines.append(
            f"| {name} | {_num(m.get('baseline'))} | {_num(m.get('candidate'))} | {change} | "
            f"{'off' if budget is None else _num(budget, '.2f')} | {_num(m.get('p_value'))} | "
            f"{counts} | {result} |"
        )
    worst = summ.get("most_regressed") or []
    if worst:
        lines += ["", f"Most regressed queries ({worst[0]['metric']}):", ""]
        lines += ["| query | delta |", "|---|---|"]
        lines += [f"| {w['id']} | {w['delta']:+.4f} |" for w in worst]
    return "\n".join(lines)


def _render_envelope(env: dict[str, Any], fmt: str) -> str:
    """Render an envelope: canonical JSON, or a human-readable summary."""
    if fmt == "json":
        return canonical_json(env).rstrip("\n")
    pred = env["predicate"]
    head = {"kind": pred["kind"], "verdict": pred["verdict"], "exit_code": pred["exit_code"]}
    if fmt == "markdown":
        title = f"{TOOL_NAME} {pred['kind']}: {pred['verdict'].upper()}"
        if pred["kind"] == "rag.compare":
            return _compare_markdown(pred, title)
        return _format_markdown(dict(head, **pred["summary"]), title=title)
    return _format_table(dict(head, **pred["summary"]))


def _positive_int(value: str) -> int:
    """argparse type for a strictly positive integer."""
    try:
        n = int(value)
    except ValueError:
        raise argparse.ArgumentTypeError(f"expected a positive integer, got {value!r}") from None
    if n < 1:
        raise argparse.ArgumentTypeError(f"expected a positive integer, got {value!r}")
    return n


def _get_format(args: argparse.Namespace) -> str:
    """Get output format from args, defaulting to json."""
    return str(getattr(args, "format", "json") or "json")


def _name(arg: str) -> str:
    """Name a file in a report the way the user passed it, with forward slashes."""
    return Path(arg).as_posix()


def _descriptors(paths: list[str]) -> list[dict[str, Any]]:
    """Resource descriptors for the given paths that exist as files."""
    out: list[dict[str, Any]] = []
    for p in paths:
        path = Path(p)
        if path.is_file():
            out.append(resource(_name(p), path))
    return out


def _write_out(args: argparse.Namespace, content: str | dict[str, Any]) -> bool:
    """Write ``content`` to ``--out`` if given. Returns False on failure."""
    if not getattr(args, "out", ""):
        return True
    # Not resolved here: the writers reject '..' in the path as given.
    out = Path(args.out)
    try:
        if isinstance(content, str):
            write_text(out, content)
        else:
            write_json(out, content)
        logger.info(f"Wrote report to: {out}")
        return True
    except (OSError, ValueError) as e:
        logger.error(f"Failed to write report: {e}")
        print(f"error: failed to write report: {e}", file=sys.stderr)
        return False


def _emit(
    args: argparse.Namespace,
    *,
    kind: str,
    exit_code: int,
    subject: list[str],
    inputs: list[str],
    summary: dict[str, Any],
    details: dict[str, Any],
    legacy: dict[str, Any],
) -> int:
    """Print the report and write it to ``--out``: an envelope by default, or
    the pre-1.0 JSON shape with ``--legacy-json``."""
    fmt = _get_format(args)
    if getattr(args, "legacy_json", False):
        if not _write_out(args, legacy):
            return EXIT_CLI_ERROR
        print(_format_output(legacy, fmt))
        return exit_code
    env = build_envelope(
        kind=kind,
        exit_code=exit_code,
        subject=_descriptors(subject),
        inputs=_descriptors(inputs),
        summary=summary,
        details=details,
    )
    if not _write_out(args, canonical_json(env)):
        return EXIT_CLI_ERROR
    print(_render_envelope(env, fmt))
    return exit_code


def _error(
    args: argparse.Namespace,
    *,
    kind: str,
    message: str,
    subject: list[str],
    inputs: list[str],
) -> int:
    """Report an input error (exit 2).

    With ``--out``, an ``error`` envelope is written when at least one subject
    file exists to identify it by digest; a missing input gets no report.
    """
    logger.error(message)
    print(f"error: {message}", file=sys.stderr)
    if getattr(args, "out", "") and not getattr(args, "legacy_json", False):
        subj = _descriptors(subject)
        if subj:
            env = build_envelope(
                kind=kind,
                exit_code=EXIT_CLI_ERROR,
                subject=subj,
                inputs=_descriptors(inputs),
                summary={"error": message},
                details={},
            )
            _write_out(args, canonical_json(env))
    return EXIT_CLI_ERROR


def _cmd_score(args: argparse.Namespace) -> int:
    """Score retrieval results (recall/precision/MRR/NDCG/MAP)."""
    k = int(args.k)
    files = [args.queries, args.retrieved]
    logger.info(f"Scoring retrieval results with k={k}")
    try:
        qrels, skipped_q = load_qrels(Path(args.queries), args.queries_format)
        run, skipped_r = load_run(Path(args.retrieved), args.retrieved_format)
        report = score_run(
            qrels=qrels,
            run=run,
            k=k,
            relevance_level=int(args.relevance_level),
            skipped_query_rows=skipped_q,
            skipped_retrieved_rows=skipped_r,
        )
    except _INPUT_ERRORS as e:
        return _error(
            args, kind="rag.score", message=str(e), subject=[args.retrieved], inputs=files
        )

    return _emit(
        args,
        kind="rag.score",
        exit_code=EXIT_SUCCESS,
        subject=[args.retrieved],
        inputs=files,
        summary=report.summary,
        details={"per_query": report.per_query},
        legacy=report.to_dict(),
    )


def _cmd_run_retriever(args: argparse.Namespace) -> int:
    """Run a LangChain / LlamaIndex / callable retriever over queries; write a run file."""
    try:
        retriever = load_object(args.retriever)
        rows = list(read_jsonl(Path(args.queries)))
        fields = tuple(args.query_field) if args.query_field else ("query", "text", "question")
        queries = query_texts(rows, fields)
        if args.qrels:
            judged, _ = load_qrels(Path(args.qrels), "auto")
            queries = [(qid, text) for qid, text in queries if judged.get(qid)]
        run = run_retriever(
            retriever,
            queries,
            k=int(args.k),
            id_key=args.id_key or None,
            framework=args.framework,
        )
        write_run(Path(args.out), run, args.to, tag=args.tag)
    except (*_INPUT_ERRORS, ImportError, TypeError, RuntimeError) as e:
        logger.error(str(e))
        print(f"error: {e}", file=sys.stderr)
        return EXIT_CLI_ERROR
    print(f"wrote a run for {len(run)} queries to {args.out} ({args.to})", file=sys.stderr)
    return EXIT_SUCCESS


def _cmd_convert(args: argparse.Namespace) -> int:
    """Convert qrels or a run between JSONL, TREC and BEIR formats."""
    try:
        if args.what == "qrels":
            qrels, _ = load_qrels(Path(args.input), args.from_format)
            write_qrels(Path(args.out), qrels, args.to)
            count = len(qrels)
        else:
            run, _ = load_run(Path(args.input), args.from_format)
            write_run(Path(args.out), run, args.to, tag=args.tag)
            count = len(run)
    except _INPUT_ERRORS as e:
        logger.error(str(e))
        print(f"error: {e}", file=sys.stderr)
        return EXIT_CLI_ERROR
    print(f"wrote {count} queries to {args.out} ({args.to})", file=sys.stderr)
    return EXIT_SUCCESS


def _cmd_overlap(args: argparse.Namespace) -> int:
    """Compute overlap/leakage between two corpora."""
    files = [args.a, args.b]
    max_records = int(args.max_records)
    logger.info(f"Computing overlap (max_records={max_records})")
    details: dict[str, Any] = {}
    try:
        a = list(read_jsonl(Path(args.a)))
        b = list(read_jsonl(Path(args.b)))
        if args.method == "exact":
            result = compute_overlap(a=a, b=b, max_records=max_records)
        else:
            _reject_oversized({"A": a, "B": b}, max_records)
            near = near_duplicates(
                a=a,
                b=b,
                threshold=_threshold(args.threshold, DEFAULT_NEAR_DUP_THRESHOLD),
                shingle=int(args.shingle or DEFAULT_NEAR_DUP_SHINGLE),
                num_perm=int(args.num_perm),
                seed=int(args.seed),
            )
            result = near["summary"]
            details = {"pairs": near["pairs"]}
    except _INPUT_ERRORS as e:
        return _error(args, kind="rag.overlap", message=str(e), subject=files, inputs=files)

    return _emit(
        args,
        kind="rag.overlap",
        exit_code=EXIT_SUCCESS,
        subject=files,
        inputs=files,
        summary=result,
        details=details,
        legacy=dict(result, **details),
    )


def _threshold(value: float | None, default: float) -> float:
    return default if value is None else float(value)


def _reject_oversized(corpora: dict[str, list[dict[str, Any]]], max_records: int) -> None:
    for label, rows in corpora.items():
        if len(rows) > max_records:
            raise ValueError(
                f"{label} has {len(rows)} records, more than max_records={max_records}; "
                "raise --max-records to process all of it"
            )


def _cmd_leakage(args: argparse.Namespace) -> int:
    """Flag eval texts contained in corpus documents."""
    files = [args.corpus, args.items]
    fields = tuple(args.field) if args.field else ("query", "question", "answer", "text")
    try:
        corpus = list(read_jsonl(Path(args.corpus)))
        items = list(read_jsonl(Path(args.items)))
        _reject_oversized({"corpus": corpus, "items": items}, int(args.max_records))
        result = containment_leaks(
            items=items,
            corpus=corpus,
            fields=fields,
            threshold=_threshold(args.threshold, DEFAULT_CONTAINMENT_THRESHOLD),
            shingle=int(args.shingle),
        )
    except _INPUT_ERRORS as e:
        return _error(args, kind="rag.leakage", message=str(e), subject=[args.items], inputs=files)

    summary = dict(result["summary"], max_leaks=int(args.max_leaks))
    leaked = summary["leaked_items"]
    passed = leaked <= int(args.max_leaks)
    if not passed:
        logger.error(f"{leaked} eval item(s) leak into the corpus (allowed: {args.max_leaks})")
    return _emit(
        args,
        kind="rag.leakage",
        exit_code=EXIT_SUCCESS if passed else EXIT_VALIDATION_FAILED,
        subject=[args.items],
        inputs=files,
        summary=summary,
        details={"leaks": result["leaks"]},
        legacy=dict(summary, leaks=result["leaks"]),
    )


def _load_score_report(path: str) -> RAGReport:
    obj = read_json(Path(path))
    return load_report(obj)


def _cmd_compare(args: argparse.Namespace) -> int:
    """Compare candidate report against baseline report."""
    files = [args.baseline, args.candidate]
    try:
        baseline = _load_score_report(args.baseline)
        candidate = _load_score_report(args.candidate)
        other = args.max_regression_pct
        budget = CompareBudget(
            max_recall_regression_pct=float(args.max_recall_regression_pct),
            max_regression_pct=None if other is None else float(other),
            per_metric=_parse_budgets(args.budget or []),
        )
        result = compare_reports(
            baseline=baseline,
            candidate=candidate,
            budget=budget,
            alpha=args.alpha,
            test=args.test,
            n_resamples=int(args.permutations),
            seed=int(args.seed),
            primary_metric=args.primary_metric,
            top_n=int(args.top),
        )
    except _INPUT_ERRORS as e:
        return _error(
            args, kind="rag.compare", message=str(e), subject=[args.candidate], inputs=files
        )

    if result["passed"]:
        logger.info("Comparison passed")
    else:
        failed = ", ".join(result["failed_metrics"]) or result["reason"]
        logger.error(f"Comparison failed: {failed}")

    diff = result.pop("per_query_diff", [])
    return _emit(
        args,
        kind="rag.compare",
        exit_code=EXIT_SUCCESS if result["passed"] else EXIT_VALIDATION_FAILED,
        subject=[args.candidate],
        inputs=files,
        summary=result,
        details={"per_query_diff": diff},
        legacy=dict(result, per_query_diff=diff),
    )


def _parse_budgets(items: list[str]) -> dict[str, float | None]:
    """Parse repeated ``--budget METRIC=PCT`` (``PCT`` may be ``off``)."""
    budgets: dict[str, float | None] = {}
    for item in items:
        name, sep, value = item.partition("=")
        if not sep:
            raise ValueError(f"--budget expects METRIC=PCT, got {item!r}")
        metric = metric_name(name)
        value = value.strip().lower()
        if value in ("off", "none"):
            budgets[metric] = None
            continue
        try:
            pct = float(value)
        except ValueError:
            raise ValueError(f"--budget {item!r}: {value!r} is not a number or 'off'") from None
        if pct < 0:
            raise ValueError(f"--budget {item!r}: the budget must not be negative")
        budgets[metric] = pct
    return budgets


def _cmd_validate_report(args: argparse.Namespace) -> int:
    """Validate a report: an envelope (default output) or a legacy report."""
    report_path = Path(args.report)
    fmt = _get_format(args)
    logger.info(f"Validating report: {report_path}")

    try:
        obj = read_json(report_path)
    except _INPUT_ERRORS as e:
        logger.error(f"Failed to read report: {e}")
        print(f"error: {e}", file=sys.stderr)
        return EXIT_CLI_ERROR

    errors: list[str]
    kind: str | None = None
    if is_envelope(obj):
        report_format = "envelope"
        errors = validate_envelope(obj)
        pred = obj.get("predicate") if isinstance(obj.get("predicate"), dict) else {}
        kind = pred.get("kind") if isinstance(pred, dict) else None
        if obj.get("predicateType") != PREDICATE_TYPE:
            errors.append(f"predicateType: expected {PREDICATE_TYPE}")
        if not errors and kind == "rag.score" and pred.get("verdict") != "error":
            errors.extend(validate_score_report(load_report(obj)))
    else:
        report_format = "legacy"
        errors = []
        if not (
            isinstance(obj, dict)
            and isinstance(obj.get("summary"), dict)
            and isinstance(obj.get("per_query"), list)
        ):
            errors.append("legacy report: missing 'summary' object or 'per_query' list")

    ok = not errors
    if ok:
        logger.info("Report validation passed")
    else:
        logger.error("Report validation failed: " + "; ".join(errors))
    payload = {"ok": ok, "format": report_format, "kind": kind, "errors": errors}
    print(_format_output(payload, fmt))
    return EXIT_SUCCESS if ok else EXIT_VALIDATION_FAILED


def _add_format_arg(parser: argparse.ArgumentParser) -> None:
    """Add --format flag to a subcommand parser."""
    parser.add_argument(
        "--format",
        choices=["json", "table", "markdown"],
        default="json",
        help="Output format on stdout (default: json). --out is always JSON.",
    )


def _add_report_args(parser: argparse.ArgumentParser) -> None:
    """--out and --legacy-json for commands that produce a report."""
    parser.add_argument(
        "--out", default="", help="Write the report (canonical JSON envelope) to this path"
    )
    parser.add_argument(
        "--legacy-json",
        action="store_true",
        help="Emit the pre-1.0 JSON shape instead of the envelope (deprecated; removed in 1.1)",
    )
    _add_format_arg(parser)


def build_parser() -> argparse.ArgumentParser:
    """Build CLI argument parser."""
    p = argparse.ArgumentParser(
        prog="toolkit-rag",
        description="RAG Quality Toolkit: deterministic retrieval metrics and corpus overlap",
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
    score.add_argument(
        "--queries",
        required=True,
        help="Relevance judgments: JSONL queries, TREC qrels or BEIR qrels TSV",
    )
    score.add_argument(
        "--queries-format",
        choices=QRELS_FORMATS,
        default="auto",
        help="Format of --queries (default: auto-detect)",
    )
    score.add_argument("--retrieved", required=True, help="Ranked results: JSONL or TREC run")
    score.add_argument(
        "--retrieved-format",
        choices=RUN_FORMATS,
        default="auto",
        help="Format of --retrieved (default: auto-detect)",
    )
    score.add_argument(
        "--k", type=_positive_int, default=5, help="Top-k cutoff, a positive integer (default: 5)"
    )
    score.add_argument(
        "--relevance-level",
        type=_positive_int,
        default=1,
        help="Minimum grade that counts as relevant, as trec_eval -l (default: 1)",
    )
    _add_report_args(score)
    score.set_defaults(func=_cmd_score)

    runr = sub.add_parser(
        "run-retriever",
        help="Run a LangChain, LlamaIndex or callable retriever over queries to make a run file.",
    )
    runr.add_argument(
        "--retriever",
        required=True,
        help="module:attr of a retriever object, or module:factory() to call a factory. "
        "Imports and runs that code.",
    )
    runr.add_argument("--queries", required=True, help="Queries JSONL (id or _id, query text)")
    runr.add_argument(
        "--query-field",
        action="append",
        help="Field holding the query text (repeatable; default: query, text, question)",
    )
    runr.add_argument(
        "--qrels", default="", help="Only run queries that have judgments in this qrels file"
    )
    runr.add_argument("--k", type=_positive_int, default=100, help="Results kept per query (100)")
    runr.add_argument(
        "--id-key",
        default="",
        help="Metadata key holding the doc id (default: Document.id / node.node_id)",
    )
    runr.add_argument("--framework", choices=FRAMEWORKS, default="auto", help="Default: auto")
    runr.add_argument("--out", required=True, help="Run file to write")
    runr.add_argument("--to", choices=["jsonl", "trec"], default="trec", help="Default: trec")
    runr.add_argument("--tag", default="toolkit-rag", help="Run tag for TREC output")
    runr.set_defaults(func=_cmd_run_retriever)

    convert = sub.add_parser(
        "convert", help="Convert qrels or a run between JSONL, TREC and BEIR formats."
    )
    convert.add_argument("what", choices=["qrels", "run"], help="What the input file holds")
    convert.add_argument("--in", dest="input", required=True, help="Input file")
    convert.add_argument(
        "--from",
        dest="from_format",
        default="auto",
        help="Input format: auto, jsonl, trec, or beir (qrels only) (default: auto)",
    )
    convert.add_argument("--out", required=True, help="Output file")
    convert.add_argument("--to", required=True, choices=["jsonl", "trec"], help="Output format")
    convert.add_argument(
        "--tag", default="toolkit-rag", help="Run tag for TREC run output (default: toolkit-rag)"
    )
    convert.set_defaults(func=_cmd_convert)

    overlap = sub.add_parser(
        "overlap",
        help="Find exact or near-duplicate documents between two corpora.",
    )
    overlap.add_argument("--a", required=True, help="Corpus A JSONL (id, text)")
    overlap.add_argument("--b", required=True, help="Corpus B JSONL (id, text)")
    overlap.add_argument(
        "--method",
        choices=["exact", "minhash"],
        default="exact",
        help=(
            "exact: identical text after case/whitespace normalization. minhash: Jaccard "
            "similarity of word shingles >= --threshold (default: exact)"
        ),
    )
    overlap.add_argument(
        "--threshold",
        type=float,
        default=None,
        help=f"minhash: Jaccard threshold (default: {DEFAULT_NEAR_DUP_THRESHOLD})",
    )
    overlap.add_argument(
        "--shingle",
        type=_positive_int,
        default=None,
        help=f"minhash: words per shingle (default: {DEFAULT_NEAR_DUP_SHINGLE})",
    )
    overlap.add_argument(
        "--num-perm",
        type=_positive_int,
        default=DEFAULT_NUM_PERM,
        help=f"minhash: signature length (default: {DEFAULT_NUM_PERM})",
    )
    overlap.add_argument("--seed", type=int, default=1, help="minhash: hash seed (default: 1)")
    overlap.add_argument(
        "--max-records",
        type=_positive_int,
        default=50000,
        help="Reject a corpus with more records than this (default: 50000)",
    )
    _add_report_args(overlap)
    overlap.set_defaults(func=_cmd_overlap)

    leakage = sub.add_parser(
        "leakage",
        help="Flag eval queries/answers whose text is contained in a corpus document.",
    )
    leakage.add_argument(
        "--corpus", required=True, help="Corpus JSONL (id or _id, text, optional title)"
    )
    leakage.add_argument("--items", required=True, help="Eval items JSONL (id or _id, text fields)")
    leakage.add_argument(
        "--field",
        action="append",
        help="Item field to check (repeatable; default: query, question, answer, text)",
    )
    leakage.add_argument(
        "--threshold",
        type=float,
        default=None,
        help=f"Containment threshold (default: {DEFAULT_CONTAINMENT_THRESHOLD})",
    )
    leakage.add_argument(
        "--shingle",
        type=_positive_int,
        default=DEFAULT_CONTAINMENT_SHINGLE,
        help=f"Words per shingle (default: {DEFAULT_CONTAINMENT_SHINGLE})",
    )
    leakage.add_argument(
        "--max-leaks",
        type=int,
        default=0,
        help="Fail (exit 4) when more eval items than this leak (default: 0)",
    )
    leakage.add_argument(
        "--max-records",
        type=_positive_int,
        default=50000,
        help="Reject a corpus or item file with more records than this (default: 50000)",
    )
    _add_report_args(leakage)
    leakage.set_defaults(func=_cmd_leakage)

    compare = sub.add_parser("compare", help="Compare candidate report against baseline report.")
    compare.add_argument("--baseline", required=True, help="Baseline report JSON file path")
    compare.add_argument("--candidate", required=True, help="Candidate report JSON file path")
    compare.add_argument(
        "--max-recall-regression-pct",
        default="2.0",
        help="Max relative recall@k regression in %% (default: 2.0)",
    )
    compare.add_argument(
        "--max-regression-pct",
        default=None,
        help=(
            "Max relative regression in %% for precision, nDCG, MRR, MAP and hit rate "
            "(default: same as --max-recall-regression-pct)"
        ),
    )
    compare.add_argument(
        "--budget",
        action="append",
        metavar="METRIC=PCT",
        help=(
            "Per-metric budget in %% (repeatable), e.g. --budget ndcg=1 --budget hit_rate=off. "
            "Overrides the two flags above; 'off' reports the metric without gating it."
        ),
    )
    compare.add_argument(
        "--alpha",
        type=float,
        default=None,
        help=(
            "Significance level. When set, a metric over budget fails only if the paired "
            "test gives p < alpha (default: off, any over-budget drop fails)"
        ),
    )
    compare.add_argument(
        "--test",
        choices=SIGNIFICANCE_TESTS,
        default="permutation",
        help="Paired significance test (default: permutation)",
    )
    compare.add_argument(
        "--permutations",
        type=_positive_int,
        default=10000,
        help="Random sign patterns for the permutation test above 16 queries (default: 10000)",
    )
    compare.add_argument(
        "--seed", type=int, default=0, help="Seed for the permutation test (default: 0)"
    )
    compare.add_argument(
        "--primary-metric",
        default="ndcg_at_k",
        help="Metric used to rank the most regressed queries (default: ndcg_at_k)",
    )
    compare.add_argument(
        "--top", type=_positive_int, default=10, help="How many regressed queries to list"
    )
    _add_report_args(compare)
    compare.set_defaults(func=_cmd_compare)

    validate_report = sub.add_parser(
        "validate-report", help="Validate a report envelope (or a legacy report)."
    )
    validate_report.add_argument(
        "--report",
        required=True,
        help="Report JSON file path to validate",
    )
    _add_format_arg(validate_report)
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
