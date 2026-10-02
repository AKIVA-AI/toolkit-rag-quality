"""Report envelope v1: every machine-readable report is an in-toto Statement v1.

The shared convention is documented in ``docs/report-envelope.md`` and the
JSON Schema is ``schemas/report-envelope.v1.json``. This module builds
envelopes, writes them as canonical JSON, and checks their structure without
any third-party dependency.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

STATEMENT_TYPE = "https://in-toto.io/Statement/v1"
PREDICATE_TYPE = "https://github.com/AKIVA-AI/toolkit-rag-quality/report/v1"
TOOL_NAME = "toolkit-rag-quality"

VERDICTS = ("pass", "fail", "error")

_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
_KIND_RE = re.compile(r"^[a-z0-9]+(\.[a-z0-9_-]+)+$")
_PREDICATE_TYPE_RE = re.compile(r"^https://github\.com/AKIVA-AI/[A-Za-z0-9._-]+/report/v1$")
_CREATED_AT_RE = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(\.\d+)?Z$")


def canonical_json(obj: Any) -> str:
    """Serialize ``obj`` as canonical JSON: sorted keys, no insignificant
    whitespace, UTF-8 (non-ASCII kept as is), and a trailing newline.

    NaN and infinity are rejected because they are not valid JSON.
    """
    return (
        json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False)
        + "\n"
    )


def sha256_file(path: Path) -> str:
    """Return the hex SHA-256 of a file's bytes."""
    h = hashlib.sha256()
    with Path(path).open("rb") as fh:
        for block in iter(lambda: fh.read(1 << 16), b""):
            h.update(block)
    return h.hexdigest()


def resource(name: str, path: Path) -> dict[str, Any]:
    """An in-toto ResourceDescriptor for a file: its name and SHA-256."""
    return {"name": name, "digest": {"sha256": sha256_file(path)}}


def created_at(now: datetime | None = None) -> str:
    """RFC 3339 UTC timestamp with second precision.

    When ``SOURCE_DATE_EPOCH`` is set (the reproducible-builds convention),
    it is used instead of the clock, so the same inputs give byte-identical
    reports.
    """
    if now is None:
        epoch = os.environ.get("SOURCE_DATE_EPOCH", "").strip()
        if epoch:
            now = datetime.fromtimestamp(int(epoch), tz=timezone.utc)
        else:
            now = datetime.now(tz=timezone.utc)
    return now.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def verdict_for_exit_code(exit_code: int) -> str:
    """Map this tool's exit codes to a verdict: 0 pass, 4 fail, anything else error."""
    if exit_code == 0:
        return "pass"
    if exit_code == 4:
        return "fail"
    return "error"


def build_envelope(
    *,
    kind: str,
    exit_code: int,
    subject: list[dict[str, Any]],
    inputs: list[dict[str, Any]],
    summary: dict[str, Any],
    details: dict[str, Any] | None = None,
    tool_version: str | None = None,
    now: datetime | None = None,
) -> dict[str, Any]:
    """Build a report envelope. The verdict is derived from ``exit_code``."""
    if tool_version is None:
        from . import __version__

        tool_version = __version__
    return {
        "_type": STATEMENT_TYPE,
        "subject": subject,
        "predicateType": PREDICATE_TYPE,
        "predicate": {
            "tool": {"name": TOOL_NAME, "version": tool_version},
            "kind": kind,
            "created_at": created_at(now),
            "verdict": verdict_for_exit_code(exit_code),
            "exit_code": int(exit_code),
            "inputs": inputs,
            "summary": summary,
            "details": details or {},
        },
    }


def is_envelope(obj: Any) -> bool:
    """True when ``obj`` looks like an in-toto Statement (not a legacy report)."""
    return isinstance(obj, dict) and obj.get("_type") == STATEMENT_TYPE


def _check_descriptor(item: Any, where: str, errors: list[str]) -> None:
    if not isinstance(item, dict):
        errors.append(f"{where}: must be an object")
        return
    name = item.get("name")
    if not isinstance(name, str) or not name:
        errors.append(f"{where}.name: must be a non-empty string")
    digest = item.get("digest")
    if not isinstance(digest, dict):
        errors.append(f"{where}.digest: must be an object")
        return
    sha = digest.get("sha256")
    if not isinstance(sha, str) or not _SHA256_RE.match(sha):
        errors.append(f"{where}.digest.sha256: must be 64 lowercase hex characters")


def validate_envelope(obj: Any) -> list[str]:
    """Check ``obj`` against the envelope v1 rules. Returns a list of errors.

    Mirrors ``schemas/report-envelope.v1.json`` (the tests check the two agree)
    and adds nothing tool-specific.
    """
    errors: list[str] = []
    if not isinstance(obj, dict):
        return ["statement: must be an object"]
    # Unknown fields are allowed and ignored, as in-toto Statement v1 intends
    # (forward compatibility); the shared schema does the same.
    if obj.get("_type") != STATEMENT_TYPE:
        errors.append(f"_type: must be {STATEMENT_TYPE!r}")
    subject = obj.get("subject")
    if not isinstance(subject, list) or not subject:
        errors.append("subject: must be a non-empty list")
    else:
        for i, item in enumerate(subject):
            _check_descriptor(item, f"subject[{i}]", errors)
    ptype = obj.get("predicateType")
    if not isinstance(ptype, str) or not _PREDICATE_TYPE_RE.match(ptype):
        errors.append("predicateType: must be https://github.com/AKIVA-AI/<repo>/report/v1")
    pred = obj.get("predicate")
    if not isinstance(pred, dict):
        errors.append("predicate: must be an object")
        return errors
    allowed_pred = {
        "tool",
        "kind",
        "created_at",
        "verdict",
        "exit_code",
        "inputs",
        "summary",
        "details",
    }
    for key in sorted(allowed_pred - set(pred)):
        errors.append(f"predicate.{key}: missing")
    tool = pred.get("tool")
    if not isinstance(tool, dict) or not all(
        isinstance(tool.get(k), str) and tool.get(k) for k in ("name", "version")
    ):
        errors.append("predicate.tool: must have non-empty string name and version")
    kind = pred.get("kind")
    if "kind" in pred and (not isinstance(kind, str) or not _KIND_RE.match(kind)):
        errors.append("predicate.kind: must look like 'area.command'")
    ts = pred.get("created_at")
    if "created_at" in pred and (not isinstance(ts, str) or not _CREATED_AT_RE.match(ts)):
        errors.append("predicate.created_at: must be an RFC 3339 UTC timestamp ending in 'Z'")
    verdict = pred.get("verdict")
    if "verdict" in pred and verdict not in VERDICTS:
        errors.append(f"predicate.verdict: must be one of {', '.join(VERDICTS)}")
    code = pred.get("exit_code")
    code_ok = isinstance(code, int) and not isinstance(code, bool) and code >= 0
    if "exit_code" in pred and not code_ok:
        errors.append("predicate.exit_code: must be a non-negative integer")
    if code_ok and verdict in VERDICTS and (verdict == "pass") != (code == 0):
        errors.append("predicate: verdict 'pass' if and only if exit_code is 0")
    inputs = pred.get("inputs")
    if "inputs" in pred:
        if not isinstance(inputs, list):
            errors.append("predicate.inputs: must be a list")
        else:
            for i, item in enumerate(inputs):
                _check_descriptor(item, f"predicate.inputs[{i}]", errors)
    for key in ("summary", "details"):
        if key in pred and not isinstance(pred.get(key), dict):
            errors.append(f"predicate.{key}: must be an object")
    return errors
