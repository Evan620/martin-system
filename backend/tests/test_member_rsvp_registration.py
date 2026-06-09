"""rsvp_meeting is registered and granted to the member agent, denied to a random agent."""
from app.tools.tool_registry import ToolAccessDenied
import pytest


def test_rsvp_meeting_registered(fresh_registry):
    assert "rsvp_meeting" in fresh_registry.list_tools()


def test_member_agent_granted_rsvp(fresh_registry):
    assert fresh_registry.validate_tool_access("rsvp_meeting", agent_id="member") is True


def test_other_agent_denied_rsvp(fresh_registry):
    with pytest.raises(ToolAccessDenied):
        fresh_registry.validate_tool_access("rsvp_meeting", agent_id="energy")
