"""
Control-plane contract types for Archetype 9 CLI toolkits.

Attempts to import from akiva_execution_contracts and akiva_policy_runtime.
Falls back to inline minimal definitions when those packages are not installed,
so CI never fails on toolkit repos that don't have the framework installed.

This module is intentionally dependency-free in the fallback path.
"""

from __future__ import annotations

from enum import Enum
from typing import Any

# -- Optional framework import ------------------------------------------------

_HAS_EXECUTION_CONTRACTS = False
_HAS_POLICY_RUNTIME = False


class PermissionScope(str, Enum):
    """Permission scope for tool operations."""

    READ_ONLY = "read_only"
    WORKSPACE_WRITE = "workspace_write"
    FULL_ACCESS = "full_access"


class ApprovalPolicy(str, Enum):
    """Approval policy for tool invocation."""

    AUTO = "auto"
    REQUIRE_APPROVAL = "require_approval"
    DENY = "deny"


class AuthorityBoundary:
    """Minimal AuthorityBoundary -- mirrors Python Pydantic model."""

    def __init__(
        self,
        scope: PermissionScope,
        approval: ApprovalPolicy,
        sandbox: dict[str, Any] | None = None,
    ) -> None:
        self.scope = scope
        self.approval = approval
        self.sandbox = sandbox

    def is_denied(self) -> bool:
        return self.approval == ApprovalPolicy.DENY

    def needs_approval(self) -> bool:
        return self.approval == ApprovalPolicy.REQUIRE_APPROVAL

    def scope_allows(self, required: PermissionScope) -> bool:
        order = [
            PermissionScope.READ_ONLY,
            PermissionScope.WORKSPACE_WRITE,
            PermissionScope.FULL_ACCESS,
        ]
        return order.index(self.scope) >= order.index(required)

    def __repr__(self) -> str:
        return (
            f"AuthorityBoundary(scope={self.scope.value!r}, "
            f"approval={self.approval.value!r}, sandbox={self.sandbox!r})"
        )


class ToolSpec:
    """Minimal ToolSpec -- mirrors Python Pydantic model.

    Note: approval_policy is NOT on ToolSpec; it lives on AuthorityBoundary.
    This mirrors the actual field set in akiva_execution_contracts.ToolSpec.
    """

    def __init__(
        self,
        name: str,
        description: str,
        category: str,
        version: str,
        owner: str,
        permission_scope: PermissionScope,
        input_schema: dict[str, Any] | None = None,
        output_schema: dict[str, Any] | None = None,
        sandbox_requirement: dict[str, Any] | None = None,
        aliases: list[str] | None = None,
    ) -> None:
        self.name = name
        self.description = description
        self.category = category
        self.version = version
        self.owner = owner
        self.permission_scope = permission_scope
        self.input_schema = input_schema
        self.output_schema = output_schema
        self.sandbox_requirement = sandbox_requirement
        self.aliases = aliases

    def __repr__(self) -> str:
        return f"ToolSpec(name={self.name!r}, scope={self.permission_scope.value!r})"


# Try to detect if the full framework is available (for future use)
try:
    __import__("akiva_execution_contracts")
    _HAS_EXECUTION_CONTRACTS = True
except ImportError:
    pass

try:
    __import__("akiva_policy_runtime")
    _HAS_POLICY_RUNTIME = True
except ImportError:
    pass


__all__ = [
    "PermissionScope",
    "ApprovalPolicy",
    "AuthorityBoundary",
    "ToolSpec",
    "_HAS_EXECUTION_CONTRACTS",
    "_HAS_POLICY_RUNTIME",
]
