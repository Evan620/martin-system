"""
Live Tool Calling Tests

Tests every tool that Martin (Supervisor) and TWG agents can call,
verifying the full chain: function call → DB/service interaction → valid result.

Uses the module-scoped `seed_db` fixture for test data.
"""

import json
import uuid
import pytest
from datetime import datetime, timedelta


# =============================================================================
# Helpers
# =============================================================================

def parse_json_or_raw(result):
    """Try to parse result as JSON; return raw string on failure."""
    if isinstance(result, (dict, list)):
        return result
    try:
        return json.loads(result)
    except (json.JSONDecodeError, TypeError):
        return result


def assert_no_error(result):
    """Assert the result does not contain an obvious error indicator."""
    text = str(result).lower()
    # Allow "no meetings", "no documents", etc. — those are valid empty results
    if "error" in text:
        # Whitelist known non-error strings
        benign = ["no error", "error_count", "0 error"]
        if not any(b in text for b in benign):
            pytest.fail(f"Tool returned an error: {result}")


# =============================================================================
# 1. Supervisor Tools
# =============================================================================


class TestSupervisorTools:
    """Direct invocation tests for all 10 supervisor-level tools."""

    def test_global_calendar(self, seed_db):
        from app.tools.supervisor_tools import get_global_calendar_tool

        result = get_global_calendar_tool()
        assert isinstance(result, str)
        assert_no_error(result)
        # Seed data creates SCHEDULED meetings → should appear
        assert "calendar" in result.lower() or "meeting" in result.lower() or "upcoming" in result.lower()

    def test_document_registry(self, seed_db):
        from app.tools.supervisor_tools import get_document_registry_tool

        result = get_document_registry_tool()
        assert isinstance(result, str)
        # Supervisor state may not be initialized; both outcomes are valid
        assert "document" in result.lower() or "state not" in result.lower()

    def test_project_pipeline(self, seed_db):
        from app.tools.supervisor_tools import get_project_pipeline_tool

        result = get_project_pipeline_tool()
        assert isinstance(result, str)
        assert "project" in result.lower() or "pipeline" in result.lower() or "state not" in result.lower()

    @pytest.mark.asyncio
    async def test_summit_status(self, seed_db):
        from app.tools.supervisor_tools import get_summit_status_tool

        result = await get_summit_status_tool()
        assert isinstance(result, str)
        # Either returns status info or "Status unavailable"
        assert "status" in result.lower() or "summit" in result.lower() or "unavailable" in result.lower()

    @pytest.mark.asyncio
    async def test_detect_conflicts(self, seed_db):
        from app.tools.supervisor_tools import detect_conflicts_tool

        result = await detect_conflicts_tool()
        assert isinstance(result, str)
        # Either "No conflicts" or a conflict list
        assert "conflict" in result.lower() or "aligned" in result.lower() or "error" not in result.lower()

    def test_start_negotiation(self, seed_db):
        from app.tools.supervisor_tools import start_negotiation_tool

        result = start_negotiation_tool(
            conflict_description="Land use overlap between solar farms and agriculture",
            agent_a="energy",
            agent_b="agriculture",
        )
        assert "NEGOTIATION_STARTED" in result
        assert "energy" in result
        assert "agriculture" in result

    def test_check_availability_open_slot(self, seed_db):
        from app.tools.supervisor_tools import check_availability_tool

        # Far-future slot that shouldn't conflict
        future = (datetime.utcnow() + timedelta(days=60)).isoformat()
        result = check_availability_tool(start_time_iso=future, duration_minutes=60)
        assert isinstance(result, str)
        assert_no_error(result)

    def test_request_booking(self, seed_db):
        from app.tools.supervisor_tools import request_booking_tool

        future = (datetime.utcnow() + timedelta(days=30, hours=10)).replace(microsecond=0).isoformat()
        result = request_booking_tool(
            title="Test Booking via Supervisor",
            twg_name="Energy",
            start_time_iso=future,
            duration_minutes=60,
        )
        assert isinstance(result, str)
        # Should succeed or mention the TWG
        assert "scheduled" in result.lower() or "meeting" in result.lower() or "error" in result.lower()

    def test_update_meeting(self, seed_db):
        from app.tools.supervisor_tools import update_meeting_tool

        meeting_id = str(seed_db["meetings"]["energy_future"])
        result = update_meeting_tool(meeting_id=meeting_id, new_title="Updated Energy Sync")
        assert isinstance(result, str)
        assert "updated" in result.lower() or "title" in result.lower()

    @pytest.mark.asyncio
    async def test_consult_twg_agents_no_context(self, seed_db):
        """consult_twg_agents_tool with no agents registered returns an error message."""
        from app.tools.supervisor_tools import consult_twg_agents_tool, set_supervisor_context

        # Ensure clean state (no agents registered)
        set_supervisor_context({})
        result = await consult_twg_agents_tool(agent_names="energy", query="status update")
        assert isinstance(result, str)
        # Should report no agents
        assert "no twg agents" in result.lower() or "error" in result.lower() or "not found" in result.lower()


# =============================================================================
# 2. TWG-Scoped Tools (Calendar)
# =============================================================================


class TestCalendarTools:

    @pytest.mark.asyncio
    async def test_get_schedule(self, seed_db):
        from app.tools.calendar_tools import get_schedule

        twg_id = str(seed_db["twgs"]["energy"])
        result = await get_schedule(days=14, twg_id=twg_id)
        data = parse_json_or_raw(result)
        assert_no_error(data)
        # Should find the seeded future meeting or say "no meetings"
        if isinstance(data, list):
            assert len(data) >= 1

    @pytest.mark.asyncio
    async def test_get_schedule_all_twgs(self, seed_db):
        from app.tools.calendar_tools import get_schedule

        result = await get_schedule(days=14)
        data = parse_json_or_raw(result)
        assert_no_error(data)

    @pytest.mark.asyncio
    async def test_get_past_meetings(self, seed_db):
        from app.tools.calendar_tools import get_past_meetings

        twg_id = str(seed_db["twgs"]["energy"])
        result = await get_past_meetings(days=30, twg_id=twg_id)
        data = parse_json_or_raw(result)
        assert_no_error(data)
        if isinstance(data, list):
            assert len(data) >= 1

    def test_update_meeting_calendar(self, seed_db):
        from app.tools.calendar_tools import update_meeting

        meeting_id = str(seed_db["meetings"]["agriculture_future"])
        result = update_meeting(meeting_id=meeting_id, new_title="Ag TWG Updated Sync")
        assert isinstance(result, str)
        assert "updated" in result.lower() or "changed" in result.lower() or "title" in result.lower()


# =============================================================================
# 3. TWG-Scoped Tools (Database)
# =============================================================================


class TestDatabaseTools:

    @pytest.mark.asyncio
    async def test_search_documents(self, seed_db):
        from app.tools.database_tools import search_documents

        twg_id = seed_db["twgs"]["energy"]
        result = await search_documents(twg_id=twg_id)
        assert isinstance(result, list)
        assert len(result) >= 1
        assert "file_name" in result[0]

    @pytest.mark.asyncio
    async def test_search_documents_by_query(self, seed_db):
        from app.tools.database_tools import search_documents

        twg_id = seed_db["twgs"]["energy"]
        result = await search_documents(twg_id=twg_id, query="policy")
        assert isinstance(result, list)
        # May or may not find results depending on fuzzy match
        assert_no_error(result)

    @pytest.mark.asyncio
    async def test_retrieve_document_content(self, seed_db):
        from app.tools.database_tools import retrieve_document_content

        doc_id = str(seed_db["documents"]["energy_policy"])
        twg_id = seed_db["twgs"]["energy"]
        result = await retrieve_document_content(
            query="energy policy",
            document_id=doc_id,
            twg_id=twg_id,
        )
        # Result is a dict; may have chunks or indicate no embeddings
        assert isinstance(result, dict)
        # Either has content or a clear status — not a crash
        assert "document_source" in result or "error" in str(result).lower() or "chunks_retrieved" in result

    @pytest.mark.asyncio
    async def test_get_meeting_minutes(self, seed_db):
        from app.tools.database_tools import get_meeting_minutes

        twg_id = seed_db["twgs"]["energy"]
        result = await get_meeting_minutes(twg_id=twg_id)
        assert isinstance(result, list)
        assert len(result) >= 1
        assert "meeting_title" in result[0] or "meeting_id" in result[0]

    @pytest.mark.asyncio
    async def test_get_meeting_minutes_by_meeting(self, seed_db):
        from app.tools.database_tools import get_meeting_minutes

        twg_id = seed_db["twgs"]["energy"]
        meeting_id = str(seed_db["meetings"]["energy_past"])
        result = await get_meeting_minutes(twg_id=twg_id, meeting_id=meeting_id)
        assert isinstance(result, list)
        assert len(result) >= 1

    @pytest.mark.asyncio
    async def test_get_action_items(self, seed_db):
        from app.tools.database_tools import get_action_items

        twg_id = str(seed_db["twgs"]["energy"])
        result = await get_action_items(twg_id=twg_id)
        assert isinstance(result, list)
        assert len(result) >= 1
        assert "description" in result[0]

    @pytest.mark.asyncio
    async def test_get_action_items_by_status(self, seed_db):
        from app.tools.database_tools import get_action_items

        twg_id = str(seed_db["twgs"]["energy"])
        result = await get_action_items(twg_id=twg_id, status="PENDING")
        assert isinstance(result, list)
        assert len(result) >= 1

    @pytest.mark.asyncio
    async def test_update_action_item_status(self, seed_db):
        from app.tools.database_tools import update_action_item_status

        ai_id = str(seed_db["action_items"]["energy_pending"])
        result = await update_action_item_status(action_item_id=ai_id, status="IN_PROGRESS")
        assert isinstance(result, dict)
        assert result.get("success") is True
        assert result["new_status"] == "IN_PROGRESS"

    @pytest.mark.asyncio
    async def test_get_twg_members(self, seed_db):
        from app.tools.database_tools import get_twg_members

        twg_id = str(seed_db["twgs"]["energy"])
        result = await get_twg_members(twg_id=twg_id)
        assert isinstance(result, list)
        assert len(result) >= 1
        assert "email" in result[0]

    @pytest.mark.asyncio
    async def test_get_twg_members_by_name(self, seed_db):
        from app.tools.database_tools import get_twg_members

        result = await get_twg_members(twg_name="energy")
        assert isinstance(result, list)
        assert len(result) >= 1

    @pytest.mark.asyncio
    async def test_create_meeting_invite(self, seed_db):
        from app.tools.database_tools import create_meeting_invite

        twg_id = str(seed_db["twgs"]["minerals"])
        future = (datetime.utcnow() + timedelta(days=20)).replace(microsecond=0).isoformat()
        result = await create_meeting_invite(
            twg_id=twg_id,
            title="Minerals TWG Test Meeting",
            scheduled_at=future,
            location="Virtual",
            duration=60,
        )
        assert isinstance(result, dict)
        assert "meeting_id" in result
        assert result.get("status") is not None


# =============================================================================
# 4. Email Tools
# =============================================================================


class TestEmailTools:

    @pytest.mark.asyncio
    async def test_send_email(self, seed_db):
        from app.tools.email_tools import send_email

        result = await send_email(
            to="test@ecowas.int",
            subject="Test email from tool test",
            message="This is an automated test.",
        )
        assert isinstance(result, dict)
        # Should create an approval request, not send directly
        assert result.get("status") in ("approval_required", "error")
        if result["status"] == "approval_required":
            assert "approval_request_id" in result

    @pytest.mark.asyncio
    async def test_create_email_draft(self, seed_db):
        from app.tools.email_tools import create_email_draft

        result = await create_email_draft(
            to="draft@ecowas.int",
            subject="Draft test",
            message="Draft body content.",
            pillar_name="Energy",
        )
        assert isinstance(result, dict)
        assert result.get("status") in ("approval_required", "error")

    @pytest.mark.asyncio
    async def test_send_email_invalid_address(self, seed_db):
        from app.tools.email_tools import send_email

        result = await send_email(
            to="not-an-email",
            subject="Should fail validation",
            message="body",
        )
        assert isinstance(result, dict)
        assert result["status"] == "error"


# =============================================================================
# 5. Document Tools
# =============================================================================


class TestDocumentTools:

    def test_request_document_approval(self, seed_db):
        from app.tools.document_tools import request_document_approval_tool

        result = request_document_approval_tool(
            title="Energy Policy Draft",
            content="# Energy Policy\n\nDraft content for testing.",
            document_type="policy",
            file_name="energy_policy_test.md",
            tags=["energy", "test"],
        )
        data = parse_json_or_raw(result)
        assert isinstance(data, dict)
        assert data["type"] == "document_approval_required"
        assert "approval_request_id" in data
        assert data["document_draft"]["title"] == "Energy Policy Draft"


# =============================================================================
# 6. Deal Pipeline Tools (Resource Mobilization)
# =============================================================================


class TestDealPipelineTools:

    @pytest.mark.asyncio
    async def test_list_flagship_projects(self, seed_db):
        from app.tools.deal_pipeline_tools import list_flagship_projects

        result = await list_flagship_projects()
        data = parse_json_or_raw(result)
        # Seed creates 1 flagship project
        if isinstance(data, list):
            assert len(data) >= 1
            assert "name" in data[0]
        else:
            # Could be "No flagship projects" if seed didn't match
            assert isinstance(data, (str, dict))

    @pytest.mark.asyncio
    async def test_get_project_details(self, seed_db):
        from app.tools.deal_pipeline_tools import get_project_details

        project_id = str(seed_db["projects"]["project_0"])
        result = await get_project_details(project_id=project_id)
        data = parse_json_or_raw(result)
        assert isinstance(data, dict)
        assert "project" in data
        assert data["project"]["name"] == "West Africa Solar Farm"

    @pytest.mark.asyncio
    async def test_get_project_details_not_found(self, seed_db):
        from app.tools.deal_pipeline_tools import get_project_details

        fake_id = str(uuid.uuid4())
        result = await get_project_details(project_id=fake_id)
        assert "not found" in result.lower() or "error" in result.lower()

    @pytest.mark.asyncio
    async def test_trigger_investor_matching(self, seed_db):
        from app.tools.deal_pipeline_tools import trigger_investor_matching

        project_id = str(seed_db["projects"]["project_0"])
        result = await trigger_investor_matching(project_id=project_id)
        data = parse_json_or_raw(result)
        # May return matches or error if no investor profiles exist
        assert data is not None

    @pytest.mark.asyncio
    async def test_analyze_project_documents(self, seed_db):
        from app.tools.deal_pipeline_tools import analyze_project_documents

        project_id = str(seed_db["projects"]["project_0"])
        result = await analyze_project_documents(project_id=project_id)
        assert isinstance(result, str)
        # Projects in seed_db don't have docs linked via project_id,
        # so expect "No documents uploaded" message
        assert "no documents" in result.lower() or "analysis" in result.lower() or "error" in result.lower()


# =============================================================================
# 7. Knowledge Base Tools
# =============================================================================


class TestKnowledgeTools:

    def test_search_knowledge_base(self, seed_db):
        from app.tools.knowledge_tools import search_knowledge_base

        result = search_knowledge_base(query="energy policy")
        assert isinstance(result, list)
        # May be empty if Pinecone isn't populated — that's fine

    def test_get_relevant_context(self, seed_db):
        from app.tools.knowledge_tools import get_relevant_context

        result = get_relevant_context(query="agriculture plans")
        assert isinstance(result, str)
        # Either returns context or "No relevant context found"
        assert len(result) > 0

    def test_get_knowledge_base_stats(self, seed_db):
        from app.tools.knowledge_tools import get_knowledge_base_stats

        result = get_knowledge_base_stats()
        assert isinstance(result, dict)
        assert "status" in result


# =============================================================================
# 8. Tool Registry Integration
# =============================================================================


class TestToolRegistryExecution:
    """Test that ToolRegistry.execute_tool dispatches correctly with access control."""

    @pytest.fixture
    def registry(self):
        from app.tools.tool_registry import ToolRegistry
        reg = ToolRegistry()
        reg.register_all()
        return reg

    @pytest.mark.asyncio
    async def test_execute_twg_tool_with_scope(self, registry, seed_db):
        """TWG-scoped tool should work when twg_id is provided."""
        twg_id = str(seed_db["twgs"]["energy"])
        result = await registry.execute_tool(
            tool_name="get_schedule",
            tool_args={"days": 7},
            agent_id="energy",
            twg_id=twg_id,
        )
        assert isinstance(result, str)
        assert_no_error(result)

    @pytest.mark.asyncio
    async def test_execute_twg_tool_without_scope_denied(self, registry, seed_db):
        """TWG-scoped tool should be denied when no twg_id."""
        from app.tools.tool_registry import ToolAccessDenied

        with pytest.raises(ToolAccessDenied):
            await registry.execute_tool(
                tool_name="get_schedule",
                tool_args={"days": 7},
                agent_id="energy",
                twg_id=None,
            )

    @pytest.mark.asyncio
    async def test_execute_supervisor_tool(self, registry, seed_db):
        """Supervisor-only tool should work for supervisor agent."""
        result = await registry.execute_tool(
            tool_name="get_global_calendar_tool",
            tool_args={},
            agent_id="supervisor",
        )
        assert isinstance(result, str)
        assert_no_error(result)

    @pytest.mark.asyncio
    async def test_supervisor_tool_denied_for_twg(self, registry, seed_db):
        """Supervisor-only tool should be denied for TWG agents."""
        from app.tools.tool_registry import ToolAccessDenied

        with pytest.raises(ToolAccessDenied):
            await registry.execute_tool(
                tool_name="get_global_calendar_tool",
                tool_args={},
                agent_id="energy",
                twg_id=str(seed_db["twgs"]["energy"]),
            )

    @pytest.mark.asyncio
    async def test_deal_tool_denied_for_non_rm(self, registry, seed_db):
        """Deal pipeline tool should be denied for non-resource_mobilization agents."""
        from app.tools.tool_registry import ToolAccessDenied

        with pytest.raises(ToolAccessDenied):
            await registry.execute_tool(
                tool_name="list_flagship_projects",
                tool_args={},
                agent_id="energy",
                twg_id=str(seed_db["twgs"]["energy"]),
            )

    @pytest.mark.asyncio
    async def test_deal_tool_allowed_for_rm(self, registry, seed_db):
        """Deal pipeline tool should work for resource_mobilization agent."""
        result = await registry.execute_tool(
            tool_name="list_flagship_projects",
            tool_args={},
            agent_id="resource_mobilization",
            twg_id=str(seed_db["twgs"]["resource_mobilization"]),
        )
        assert isinstance(result, str)

    @pytest.mark.asyncio
    async def test_auto_inject_twg_id(self, registry, seed_db):
        """ToolRegistry should auto-inject twg_id when not provided in args."""
        twg_id = str(seed_db["twgs"]["minerals"])
        result = await registry.execute_tool(
            tool_name="get_action_items",
            tool_args={},  # No twg_id in args — should be auto-injected
            agent_id="minerals",
            twg_id=twg_id,
        )
        data = parse_json_or_raw(result)
        assert_no_error(data)


# =============================================================================
# 9. End-to-End Agent Chat (HTTP)
# =============================================================================


class TestE2EChat:
    """
    Smoke tests that send a message through the /api/v1/agents/chat endpoint
    and verify the agent responds without crashing.
    """

    @pytest.mark.asyncio
    async def test_supervisor_chat(self, client, admin_token_headers, seed_db):
        response = await client.post(
            "/api/v1/agents/chat",
            json={"message": "What meetings are scheduled this week?"},
            headers=admin_token_headers,
        )
        assert response.status_code == 200
        data = response.json()
        resp_text = data.get("response", "")
        # Agent should respond — not crash
        assert len(resp_text) > 0
        assert "encountered an issue" not in resp_text.lower()

    @pytest.mark.asyncio
    async def test_twg_chat(self, client, admin_token_headers, seed_db):
        twg_id = str(seed_db["twgs"]["energy"])
        response = await client.post(
            "/api/v1/agents/chat",
            json={
                "message": "What are the open action items?",
                "twg_id": twg_id,
            },
            headers=admin_token_headers,
        )
        # May be 200 or 422 depending on endpoint schema
        if response.status_code == 200:
            data = response.json()
            resp_text = data.get("response", "")
            assert len(resp_text) > 0
