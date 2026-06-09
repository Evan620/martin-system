"""The member agent is gated to MEMBER_TOOLS and gets TWG-scoped reads with a twg_id."""
import uuid
import pytest
from app.tools.tool_registry import get_tool_registry, ToolAccessDenied, MEMBER_TOOLS


def test_member_prompt_loads():
    from app.agents.prompts import get_prompt, AVAILABLE_AGENTS
    assert "member" in AVAILABLE_AGENTS
    assert isinstance(get_prompt("member"), str) and get_prompt("member").strip()


def test_member_toolset_is_subset_of_member_tools():
    reg = get_tool_registry()
    twg = str(uuid.uuid4())
    _defs, tool_map = reg.get_tools_for_agent(agent_id="member", twg_id=twg)
    assert set(tool_map.keys()).issubset(MEMBER_TOOLS)
    # with a twg_id, TWG-scoped member reads are granted
    assert "get_schedule" in tool_map


def test_member_denied_facilitator_tool():
    reg = get_tool_registry()
    with pytest.raises(ToolAccessDenied):
        reg.validate_tool_access("create_meeting", agent_id="member", twg_id=str(uuid.uuid4()))
