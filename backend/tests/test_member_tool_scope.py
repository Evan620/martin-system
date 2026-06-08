"""
Proof that the `member` agent scope grants ONLY the member toolset and is
denied every facilitator/admin tool (spec 2026-06-08-member-mobile-app-design §3, §6).
"""
import pytest
from app.tools.tool_registry import (
    ToolRegistry,
    ToolAccessDenied,
    MEMBER_TOOLS,
    SUPERVISOR_ONLY_TOOLS,
    DEAL_PIPELINE_TOOLS,
    PIPELINE_WRITE_TOOLS,
    PIPELINE_READ_TOOLS,
)
# Import the WhatsApp tool names from their SOURCE module (derived from
# WHATSAPP_TOOLS) so this test can never drift from the actually-registered
# names. See Task 1's whatsapp_tools.py export step.
from app.tools.whatsapp_tools import WHATSAPP_TOOL_NAMES

MEMBER_TWG = "11111111-1111-1111-1111-111111111111"

# Tools a member must NEVER get, regardless of twg scope (spec §6 "Never exposed").
# These are the facilitator/admin write + directory tools that ARE registered as
# callable today, so they are the realistic leak vectors.
BLOCKED_FOR_MEMBER = {
    "create_meeting", "create_recurring_meeting", "create_meeting_invite",
    "update_meeting", "send_email", "create_email_draft",
    "request_document_approval_tool", "get_twg_members",
}

# WhatsApp tools — explicitly BLOCKED for members (spec §6 "Never exposed"
# interpretation + §29 no-broadcast principle; see the "Why WhatsApp tools are
# blocked" note above). They ARE registered today (_register_whatsapp_tools in
# tool_registry.py), so they are real leak vectors and CAN be asserted denied.
# WHATSAPP_TOOL_NAMES is imported above from app.tools.whatsapp_tools (derived
# from WHATSAPP_TOOLS) — do NOT redefine it here; that would reintroduce drift.

# The FULL set of names a member must never be granted — the explicit blocklist
# UNION every restricted policy group (including WhatsApp). Iterated by the
# leakage + denial tests so that ANY future tool added to these groups is
# automatically asserted absent from a member session.
FULL_BLOCKED_UNION = (
    BLOCKED_FOR_MEMBER
    | WHATSAPP_TOOL_NAMES
    | SUPERVISOR_ONLY_TOOLS
    | DEAL_PIPELINE_TOOLS
    | PIPELINE_WRITE_TOOLS
    | PIPELINE_READ_TOOLS
)


@pytest.fixture
def registry():
    reg = ToolRegistry()
    reg.register_all()
    return reg


def test_member_granted_only_allowlisted_registered_tools(registry):
    """A member session is granted exactly MEMBER_TOOLS ∩ registered tools — nothing else."""
    _defs, tool_map = registry.get_tools_for_agent("member", twg_id=MEMBER_TWG)
    granted = set(tool_map.keys())
    expected = MEMBER_TOOLS & set(registry.list_tools())
    assert granted == expected, (
        f"member granted unexpected extra tools: {granted - expected}; "
        f"member missing expected tools: {expected - granted}"
    )
    assert granted, "member must be granted at least the registered allowlist"


def test_member_denied_facilitator_and_admin_tools(registry):
    """Every registered blocked tool raises ToolAccessDenied for a member, even with a twg_id."""
    # We can only assert DENIAL for tools that are actually REGISTERED — a tool
    # not in `registry.list_tools()` is never offered to any agent, so it can't
    # leak to a member. The `& registered` intersection scopes the assertion to
    # registered blocked tools (the ones that could realistically appear).
    registered = set(registry.list_tools())
    checked = FULL_BLOCKED_UNION & registered
    assert checked, "expected at least one registered blocked tool to assert against"
    for tool_name in checked:
        with pytest.raises(ToolAccessDenied):
            registry.validate_tool_access(tool_name, "member", twg_id=MEMBER_TWG)


def test_member_denied_blocked_tools_appear_in_no_session(registry):
    """No tool from the FULL blocked union ever leaks into the member's granted tool map."""
    _defs, tool_map = registry.get_tools_for_agent("member", twg_id=MEMBER_TWG)
    leaked = FULL_BLOCKED_UNION & set(tool_map.keys())
    assert not leaked, f"blocked tools leaked into member session: {leaked}"


def test_member_denied_whatsapp_tools(registry):
    """WhatsApp tools are BLOCKED for members.

    Rationale (see Task 1's "Why WhatsApp tools are blocked" note): spec §6 lists
    "broadcasts" + "invite or email people" in *Never exposed*, and §29 states the
    no-outward-communication / no-broadcast principle. WhatsApp send/group are an
    outward broadcast channel and the two read tools expose the org WhatsApp
    directory (not in the §6 member allow-list) — so all four are blocked. This is
    a plan-level interpretation of the spec, not a spec-named line item.

    Dedicated proof for the WhatsApp tool names (imported via WHATSAPP_TOOL_NAMES).
    They are registered today, so we both (a) assert each registered WhatsApp tool
    raises ToolAccessDenied for a member and (b) assert none leak into the member's
    granted tool map. The denial works because WhatsApp tools are absent from
    MEMBER_TOOLS, so the member branch's catch-all `raise ToolAccessDenied` fires.
    """
    registered = set(registry.list_tools())
    checked = WHATSAPP_TOOL_NAMES & registered
    assert checked, "expected WhatsApp tools to be registered to assert against"
    for tool_name in checked:
        with pytest.raises(ToolAccessDenied):
            registry.validate_tool_access(tool_name, "member", twg_id=MEMBER_TWG)
    _defs, tool_map = registry.get_tools_for_agent("member", twg_id=MEMBER_TWG)
    assert not (WHATSAPP_TOOL_NAMES & set(tool_map.keys())), (
        "WhatsApp tools leaked into member session"
    )


def test_member_allowlist_tools_validate_true(registry):
    """Allowlisted, registered tools validate True for a member with a twg_id."""
    for tool_name in MEMBER_TOOLS & set(registry.list_tools()):
        assert registry.validate_tool_access(tool_name, "member", twg_id=MEMBER_TWG) is True
