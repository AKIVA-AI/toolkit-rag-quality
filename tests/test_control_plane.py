"""
Tests for toolkit-rag-quality control_plane adapter.

Coverage:
  - contracts: PermissionScope ordinal, AuthorityBoundary helpers
  - config: build_config_hierarchy (platform defaults, overrides, CLI)
  - tool_specs: TOOLKIT_TOOL_SPECS covers all 5 commands, get_tool_spec lookup
  - Optional framework import: _HAS_EXECUTION_CONTRACTS flag is a bool (no crash)
"""

from __future__ import annotations

from toolkit_rag_quality.control_plane.config import (
    CONFIG_LEVELS,
    ToolkitConfigContract,
    build_config_hierarchy,
)
from toolkit_rag_quality.control_plane.contracts import (
    _HAS_EXECUTION_CONTRACTS,
    ApprovalPolicy,
    AuthorityBoundary,
    PermissionScope,
    ToolSpec,
)
from toolkit_rag_quality.control_plane.tool_specs import (
    TOOLKIT_TOOL_SPECS,
    get_tool_spec,
)

# -- contracts ----------------------------------------------------------------


class TestPermissionScope:
    def test_values_are_strings(self) -> None:
        assert PermissionScope.READ_ONLY.value == "read_only"
        assert PermissionScope.WORKSPACE_WRITE.value == "workspace_write"
        assert PermissionScope.FULL_ACCESS.value == "full_access"

    def test_ordinal_ascending(self) -> None:
        boundary = AuthorityBoundary(
            scope=PermissionScope.FULL_ACCESS, approval=ApprovalPolicy.AUTO
        )
        assert boundary.scope_allows(PermissionScope.READ_ONLY)

    def test_lower_does_not_satisfy_higher(self) -> None:
        boundary = AuthorityBoundary(scope=PermissionScope.READ_ONLY, approval=ApprovalPolicy.AUTO)
        assert not boundary.scope_allows(PermissionScope.WORKSPACE_WRITE)
        assert not boundary.scope_allows(PermissionScope.FULL_ACCESS)


class TestApprovalPolicy:
    def test_values_are_strings(self) -> None:
        assert ApprovalPolicy.AUTO.value == "auto"
        assert ApprovalPolicy.REQUIRE_APPROVAL.value == "require_approval"
        assert ApprovalPolicy.DENY.value == "deny"


class TestAuthorityBoundary:
    def test_is_denied(self) -> None:
        b = AuthorityBoundary(scope=PermissionScope.READ_ONLY, approval=ApprovalPolicy.DENY)
        assert b.is_denied()
        assert not b.needs_approval()

    def test_needs_approval(self) -> None:
        b = AuthorityBoundary(
            scope=PermissionScope.FULL_ACCESS, approval=ApprovalPolicy.REQUIRE_APPROVAL
        )
        assert b.needs_approval()
        assert not b.is_denied()

    def test_auto_neither(self) -> None:
        b = AuthorityBoundary(scope=PermissionScope.WORKSPACE_WRITE, approval=ApprovalPolicy.AUTO)
        assert not b.is_denied()
        assert not b.needs_approval()

    def test_sandbox_defaults_none(self) -> None:
        b = AuthorityBoundary(scope=PermissionScope.READ_ONLY, approval=ApprovalPolicy.AUTO)
        assert b.sandbox is None


class TestToolSpec:
    def test_construction(self) -> None:
        spec = ToolSpec(
            name="score",
            description="test",
            category="tool",
            version="0.1.0",
            owner="toolkit-rag-quality",
            permission_scope=PermissionScope.READ_ONLY,
        )
        assert spec.name == "score"
        assert spec.permission_scope == PermissionScope.READ_ONLY
        assert spec.input_schema is None

    def test_repr_contains_name(self) -> None:
        spec = ToolSpec(
            name="health",
            description="test",
            category="tool",
            version="0.1.0",
            owner="o",
            permission_scope=PermissionScope.READ_ONLY,
        )
        assert "health" in repr(spec)


class TestFrameworkFlag:
    def test_flag_is_bool(self) -> None:
        assert isinstance(_HAS_EXECUTION_CONTRACTS, bool)


# -- config -------------------------------------------------------------------


class TestConfigLevels:
    def test_ordering(self) -> None:
        assert CONFIG_LEVELS["platform_default"] < CONFIG_LEVELS["toolkit_config"]
        assert CONFIG_LEVELS["toolkit_config"] < CONFIG_LEVELS["cli_override"]


class TestBuildConfigHierarchy:
    def test_defaults(self) -> None:
        cfg = build_config_hierarchy()
        assert cfg.toolkit_id == "TK-RQ"
        assert cfg.toolkit_name == "toolkit-rag-quality"
        assert cfg.log_format == "json"
        assert cfg.structured_logging is True
        assert cfg.top_k == 10
        assert cfg.overlap_threshold == 0.8

    def test_toolkit_config_overrides_defaults(self) -> None:
        cfg = build_config_hierarchy(toolkit_config={"top_k": 20, "overlap_threshold": 0.9})
        assert cfg.top_k == 20
        assert cfg.overlap_threshold == 0.9
        assert cfg.toolkit_id == "TK-RQ"

    def test_cli_overrides_toolkit_config(self) -> None:
        cfg = build_config_hierarchy(
            toolkit_config={"top_k": 20},
            cli_overrides={"top_k": 5},
        )
        assert cfg.top_k == 5

    def test_unknown_keys_go_to_extra(self) -> None:
        cfg = build_config_hierarchy(toolkit_config={"custom_flag": True})
        assert cfg.extra.get("custom_flag") is True

    def test_returns_toolkit_config_contract(self) -> None:
        cfg = build_config_hierarchy()
        assert isinstance(cfg, ToolkitConfigContract)


# -- tool_specs ---------------------------------------------------------------


class TestToolkitToolSpecs:
    def test_all_five_commands_present(self) -> None:
        expected = {"score", "overlap", "compare", "validate-report", "health"}
        assert set(TOOLKIT_TOOL_SPECS.keys()) == expected

    def test_all_commands_are_read_only(self) -> None:
        for name, cmd_spec in TOOLKIT_TOOL_SPECS.items():
            assert cmd_spec.spec.permission_scope == PermissionScope.READ_ONLY, (
                f"command '{name}' should be READ_ONLY"
            )

    def test_all_commands_are_auto_approved(self) -> None:
        for name, cmd_spec in TOOLKIT_TOOL_SPECS.items():
            assert cmd_spec.boundary.approval == ApprovalPolicy.AUTO, (
                f"command '{name}' should have AUTO approval"
            )

    def test_boundary_scope_matches_spec_scope(self) -> None:
        for name, cmd_spec in TOOLKIT_TOOL_SPECS.items():
            assert cmd_spec.boundary.scope == cmd_spec.spec.permission_scope, name

    def test_no_sandbox_required(self) -> None:
        for name, cmd_spec in TOOLKIT_TOOL_SPECS.items():
            assert cmd_spec.spec.sandbox_requirement is None, name

    def test_score_requires_results_and_ground_truth(self) -> None:
        schema = TOOLKIT_TOOL_SPECS["score"].spec.input_schema
        assert schema is not None
        required = schema.get("required", [])
        assert "results" in required
        assert "ground_truth" in required

    def test_overlap_requires_corpus_a_and_b(self) -> None:
        schema = TOOLKIT_TOOL_SPECS["overlap"].spec.input_schema
        assert schema is not None
        required = schema.get("required", [])
        assert "corpus_a" in required
        assert "corpus_b" in required

    def test_compare_requires_baseline_and_candidate(self) -> None:
        schema = TOOLKIT_TOOL_SPECS["compare"].spec.input_schema
        assert schema is not None
        required = schema.get("required", [])
        assert "baseline" in required
        assert "candidate" in required

    def test_all_have_input_schema(self) -> None:
        for name, cmd_spec in TOOLKIT_TOOL_SPECS.items():
            assert cmd_spec.spec.input_schema is not None, (
                f"command '{name}' should have an input schema"
            )

    def test_command_name_matches_key(self) -> None:
        for key, cmd_spec in TOOLKIT_TOOL_SPECS.items():
            assert cmd_spec.command == key

    def test_owner_is_toolkit(self) -> None:
        for cmd_spec in TOOLKIT_TOOL_SPECS.values():
            assert cmd_spec.spec.owner == "toolkit-rag-quality"


class TestGetToolSpec:
    def test_returns_spec_for_known_command(self) -> None:
        spec = get_tool_spec("score")
        assert spec is not None
        assert spec.command == "score"

    def test_returns_none_for_unknown_command(self) -> None:
        assert get_tool_spec("nonexistent") is None

    def test_returns_none_for_empty_string(self) -> None:
        assert get_tool_spec("") is None
