"""
Tests for the Zero-Trust Tool Registry.

Verifies:
1. Tool registration and schema generation
2. Access control enforcement (TWG-scoped, supervisor-only, deal-pipeline)
3. Agent scoping (agents only get their permitted tools)
"""

import pytest
import json
from unittest.mock import patch, AsyncMock, MagicMock
from app.tools.tool_registry import (
    ToolRegistry,
    ToolAccessDenied,
    TWG_SCOPED_TOOLS,
    SUPERVISOR_ONLY_TOOLS,
    DEAL_PIPELINE_TOOLS,
    UNRESTRICTED_TOOLS,
)


@pytest.fixture
def registry():
    """Create a fresh ToolRegistry for each test."""
    reg = ToolRegistry()
    reg.register_all()
    return reg


class TestToolRegistration:
    """Test tool registration and schema generation."""

    def test_register_all_populates_tools(self, registry):
        """All tools should be registered after register_all()."""
        tools = registry.list_tools()
        assert len(tools) > 0, "No tools were registered"
        
        # Verify core tools are present
        expected_tools = [
            "get_schedule", "get_past_meetings", "update_meeting",
            "send_email", "create_email_draft",
            "request_document_approval_tool",
            "search_documents", "get_meeting_minutes",
        ]
        for tool_name in expected_tools:
            assert tool_name in tools, f"Expected tool '{tool_name}' not registered"

    def test_register_all_is_idempotent(self, registry):
        """Calling register_all() multiple times should not duplicate tools."""
        count_before = len(registry.list_tools())
        registry._registered = False  # Force re-registration
        registry.register_all()
        count_after = len(registry.list_tools())
        # Since register_all checks _registered flag, counts should be the same
        assert count_before == count_after

    def test_tool_info_returns_metadata(self, registry):
        """get_tool_info should return description and parameters."""
        info = registry.get_tool_info("get_schedule")
        assert info is not None
        assert "description" in info
        assert "parameters" in info
        assert info["name"] == "get_schedule"

    def test_unknown_tool_returns_none(self, registry):
        """get_tool_info for a non-existent tool should return None."""
        info = registry.get_tool_info("nonexistent_tool")
        assert info is None


class TestAccessControl:
    """Test zero-trust access control validation."""

    def test_supervisor_has_full_access(self, registry):
        """Supervisor agent should be able to access all tools."""
        for tool_name in registry.list_tools():
            assert registry.validate_tool_access(tool_name, "supervisor", twg_id=None) is True

    def test_twg_agent_denied_supervisor_tools(self, registry):
        """TWG agents should be denied access to supervisor-only tools."""
        for tool_name in SUPERVISOR_ONLY_TOOLS:
            if tool_name in registry.list_tools():
                with pytest.raises(ToolAccessDenied):
                    registry.validate_tool_access(tool_name, "energy", twg_id="some-twg-id")

    def test_non_resource_agent_denied_deal_pipeline(self, registry):
        """Non-resource_mobilization agents should be denied deal pipeline tools."""
        for tool_name in DEAL_PIPELINE_TOOLS:
            if tool_name in registry.list_tools():
                with pytest.raises(ToolAccessDenied):
                    registry.validate_tool_access(tool_name, "energy", twg_id="some-twg-id")

    def test_resource_agent_can_access_deal_pipeline(self, registry):
        """resource_mobilization agent should access deal pipeline tools."""
        for tool_name in DEAL_PIPELINE_TOOLS:
            if tool_name in registry.list_tools():
                assert registry.validate_tool_access(
                    tool_name, "resource_mobilization", twg_id="some-twg-id"
                ) is True

    def test_twg_scoped_tool_denied_without_twg_id(self, registry):
        """TWG-scoped tools should be denied if agent has no twg_id."""
        for tool_name in TWG_SCOPED_TOOLS:
            if tool_name in registry.list_tools():
                with pytest.raises(ToolAccessDenied):
                    registry.validate_tool_access(tool_name, "energy", twg_id=None)

    def test_twg_scoped_tool_allowed_with_twg_id(self, registry):
        """TWG-scoped tools should be allowed if agent has a twg_id."""
        for tool_name in TWG_SCOPED_TOOLS:
            if tool_name in registry.list_tools():
                assert registry.validate_tool_access(
                    tool_name, "energy", twg_id="some-twg-id"
                ) is True

    def test_unrestricted_tools_always_allowed(self, registry):
        """Unrestricted tools should be accessible to any agent."""
        for tool_name in UNRESTRICTED_TOOLS:
            # Even without twg_id
            assert registry.validate_tool_access(tool_name, "energy", twg_id=None) is True
            assert registry.validate_tool_access(tool_name, "agriculture", twg_id="some-id") is True


class TestToolRetrieval:
    """Test filtered tool retrieval for different agents."""

    def test_supervisor_gets_all_tools(self, registry):
        """Supervisor should receive all registered tools."""
        tool_defs, tool_map = registry.get_tools_for_agent("supervisor", twg_id=None)
        assert len(tool_defs) == len(registry.list_tools())
        assert len(tool_map) == len(registry.list_tools())

    def test_twg_agent_gets_filtered_tools(self, registry):
        """TWG agents should receive a subset of tools."""
        tool_defs, tool_map = registry.get_tools_for_agent("energy", twg_id="some-twg-id")
        
        # Should NOT have supervisor-only tools
        tool_names = [td["function"]["name"] for td in tool_defs]
        for supervisor_tool in SUPERVISOR_ONLY_TOOLS:
            assert supervisor_tool not in tool_names, f"TWG agent should not have '{supervisor_tool}'"
        
        # Should NOT have deal pipeline tools
        for dp_tool in DEAL_PIPELINE_TOOLS:
            assert dp_tool not in tool_names, f"TWG agent should not have '{dp_tool}'"
        
        # Should have standard TWG tools
        assert "get_schedule" in tool_names
        assert "send_email" in tool_names

    def test_tool_defs_are_openai_compatible(self, registry):
        """Tool definitions should be valid OpenAI function calling format."""
        tool_defs, _ = registry.get_tools_for_agent("supervisor", twg_id=None)
        
        for td in tool_defs:
            assert td["type"] == "function"
            assert "function" in td
            func = td["function"]
            assert "name" in func
            assert "description" in func
            assert "parameters" in func
            assert func["parameters"]["type"] == "object"


class TestSecureExecution:
    """Test secure tool execution with auto-injection."""

    @pytest.mark.asyncio
    async def test_access_denied_raises_exception(self, registry):
        """Executing a supervisor-only tool as a TWG agent should raise ToolAccessDenied."""
        with pytest.raises(ToolAccessDenied):
            await registry.execute_tool(
                tool_name="get_global_calendar_tool",
                tool_args={},
                agent_id="energy",
                twg_id="some-twg-id",
            )

    @pytest.mark.asyncio
    async def test_unknown_tool_returns_error(self, registry):
        """Executing an unknown tool should return an error JSON."""
        result = await registry.execute_tool(
            tool_name="nonexistent_tool",
            tool_args={},
            agent_id="supervisor",
        )
        error = json.loads(result)
        assert "error" in error
        assert "not found" in error["error"]
