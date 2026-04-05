"""
CLI command -> ToolSpec mapping for toolkit-rag-quality.

Maps the 5 CLI subcommands (score, overlap, compare, validate-report, health)
to ToolSpec contracts with appropriate permission scope and approval policy.

All commands are READ_ONLY + AUTO -- this toolkit reads retrieval result files
and corpus data, then produces quality metrics; it never modifies external state.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .contracts import ApprovalPolicy, AuthorityBoundary, PermissionScope, ToolSpec


@dataclass
class ToolkitCommandSpec:
    """Maps a CLI subcommand name to its ToolSpec and authority boundary."""

    command: str
    spec: ToolSpec
    boundary: AuthorityBoundary


def _make_spec(
    name: str,
    description: str,
    input_schema: dict[str, Any] | None = None,
) -> ToolSpec:
    """Create a ToolSpec for a read-only CLI command."""
    return ToolSpec(
        name=name,
        description=description,
        category="tool",
        version="0.2.0",
        owner="toolkit-rag-quality",
        permission_scope=PermissionScope.READ_ONLY,
        input_schema=input_schema,
        output_schema=None,
        sandbox_requirement=None,
        aliases=None,
    )


_READ_ONLY_AUTO = AuthorityBoundary(
    scope=PermissionScope.READ_ONLY,
    approval=ApprovalPolicy.AUTO,
)

# -- Per-command specs ---------------------------------------------------------

TOOLKIT_TOOL_SPECS: dict[str, ToolkitCommandSpec] = {
    "score": ToolkitCommandSpec(
        command="score",
        spec=_make_spec(
            name="score",
            description=(
                "Score retrieval results with precision, recall, MRR, NDCG, and MAP. "
                "Read-only; produces a JSON report."
            ),
            input_schema={
                "type": "object",
                "properties": {
                    "results": {"type": "string", "description": "Path to retrieval results JSONL"},
                    "ground_truth": {"type": "string", "description": "Path to ground truth JSONL"},
                    "out": {"type": "string", "description": "Output report path"},
                    "top_k": {"type": "integer"},
                    "format": {"type": "string", "enum": ["json", "table"]},
                },
                "required": ["results", "ground_truth"],
            },
        ),
        boundary=_READ_ONLY_AUTO,
    ),
    "overlap": ToolkitCommandSpec(
        command="overlap",
        spec=_make_spec(
            name="overlap",
            description=(
                "Compute overlap / leakage between two corpora using Jaccard similarity. "
                "Detects training/test contamination. Read-only."
            ),
            input_schema={
                "type": "object",
                "properties": {
                    "corpus_a": {"type": "string", "description": "Path to first corpus JSONL"},
                    "corpus_b": {"type": "string", "description": "Path to second corpus JSONL"},
                    "threshold": {"type": "number", "description": "Jaccard warning threshold"},
                    "format": {"type": "string", "enum": ["json", "table"]},
                },
                "required": ["corpus_a", "corpus_b"],
            },
        ),
        boundary=_READ_ONLY_AUTO,
    ),
    "compare": ToolkitCommandSpec(
        command="compare",
        spec=_make_spec(
            name="compare",
            description=(
                "Compare a candidate RAG quality report against a baseline report. "
                "Read-only; reports regressions and improvements."
            ),
            input_schema={
                "type": "object",
                "properties": {
                    "baseline": {"type": "string", "description": "Baseline report path"},
                    "candidate": {"type": "string", "description": "Candidate report path"},
                    "format": {"type": "string", "enum": ["json", "table"]},
                },
                "required": ["baseline", "candidate"],
            },
        ),
        boundary=_READ_ONLY_AUTO,
    ),
    "validate-report": ToolkitCommandSpec(
        command="validate-report",
        spec=_make_spec(
            name="validate_report",
            description=(
                "Validate a RAG quality report JSON file against the expected schema. Read-only."
            ),
            input_schema={
                "type": "object",
                "properties": {
                    "report": {"type": "string", "description": "Path to report JSON"},
                },
                "required": ["report"],
            },
        ),
        boundary=_READ_ONLY_AUTO,
    ),
    "health": ToolkitCommandSpec(
        command="health",
        spec=_make_spec(
            name="health",
            description=(
                "Show system health status for the RAG quality toolkit. "
                "Reports dependency availability and configuration. Read-only."
            ),
            input_schema={
                "type": "object",
                "properties": {
                    "format": {"type": "string", "enum": ["json", "table"]},
                },
            },
        ),
        boundary=_READ_ONLY_AUTO,
    ),
}


def get_tool_spec(command: str) -> ToolkitCommandSpec | None:
    """Return the ToolkitCommandSpec for a CLI subcommand, or None if unknown."""
    return TOOLKIT_TOOL_SPECS.get(command)


__all__ = ["TOOLKIT_TOOL_SPECS", "ToolkitCommandSpec", "get_tool_spec"]
