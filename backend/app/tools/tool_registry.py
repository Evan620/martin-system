"""
Zero-Trust Tool Registry

Centralizes tool registration, access control, and execution validation.
Every tool execution goes through this registry, which independently validates
the user's access rights before invoking any tool function.

This replaces the tightly-coupled tool registration that was previously
embedded directly in LangGraphBaseAgent.__init__ (~170 lines).
"""

import inspect
import json
import logging
import asyncio
from typing import Dict, List, Optional, Any, Callable, Set
from functools import wraps

logger = logging.getLogger(__name__)


# =============================================================================
# Access Control Policies
# =============================================================================

# Tools that require TWG membership (agent must be scoped to a TWG)
TWG_SCOPED_TOOLS: Set[str] = {
    "get_schedule",
    "get_past_meetings",
    "update_meeting",
    "create_meeting",
    "create_recurring_meeting",
    "search_documents",
    "retrieve_document_content",
    "get_meeting_minutes",
    "get_twg_members",
    "send_email",
    "create_email_draft",
    "request_document_approval_tool",
    "get_action_items",
    "update_action_item_status",
}

# Tools restricted to specific agent roles
SUPERVISOR_ONLY_TOOLS: Set[str] = {
    "get_global_calendar_tool",
    "get_document_registry_tool",
    "get_project_pipeline_tool",
    "get_summit_status_tool",
    "detect_conflicts_tool",
    "start_negotiation_tool",
    "consult_twg_agents_tool",
    "check_availability_tool",
    "request_booking_tool",
    "update_meeting_tool",
}

# Tools restricted to the resource_mobilization agent
DEAL_PIPELINE_TOOLS: Set[str] = {
    "get_project_details",
    "list_flagship_projects",
    "trigger_investor_matching",
    "generate_investment_memo",
    "analyze_project_documents",
}

# Pipeline write tools — gated by user role (not by agent id). Exposed on the supervisor agent.
PIPELINE_WRITE_TOOLS: Set[str] = {
    "advance_project_stage",
    "decline_project",
    "mark_flagship",
    "rescore_project",
    "graduate_from_incubation",
    "create_action_item",
    "bulk_create_action_items",
}

# Pipeline read tools — no role gate beyond TWG scoping where applicable.
PIPELINE_READ_TOOLS: Set[str] = {
    "pipeline_summary",
    "at_risk_projects",
    "incubation_close_to_graduation",
    "my_action_items",
    "next_deadlines",
}

# Tools available to all authenticated agents (no TWG scope needed)
UNRESTRICTED_TOOLS: Set[str] = {
    "search_knowledge_base",
    "get_relevant_context",
    "get_knowledge_base_stats",
}


class ToolAccessDenied(Exception):
    """Raised when a tool execution fails access validation."""
    pass


class ToolRegistration:
    """Represents a single registered tool with its definition and handler."""

    def __init__(
        self,
        name: str,
        description: str,
        parameters: Dict[str, Any],
        handler: Callable,
        is_async: bool = False,
        required_params: Optional[List[str]] = None,
    ):
        self.name = name
        self.description = description
        self.parameters = parameters
        self.handler = handler
        self.is_async = is_async
        self.required_params = required_params or []

    @property
    def openai_tool_def(self) -> Dict[str, Any]:
        """Return the OpenAI-compatible tool definition."""
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": {
                    "type": "object",
                    "properties": self.parameters,
                    "required": self.required_params,
                },
            },
        }


class ToolRegistry:
    """
    Centralized, zero-trust tool registry.
    
    Responsibilities:
    1. Register all available tools with their OpenAI function schemas.
    2. Provide filtered tool lists based on agent role / TWG scope.
    3. Validate access before every tool execution.
    4. Auto-inject contextual parameters (twg_id, user_timezone).
    """

    def __init__(self):
        self._tools: Dict[str, ToolRegistration] = {}
        self._registered = False

    # -------------------------------------------------------------------------
    # Registration
    # -------------------------------------------------------------------------

    def register(
        self,
        name: str,
        description: str,
        parameters: Dict[str, Any],
        handler: Callable,
        required_params: Optional[List[str]] = None,
    ) -> None:
        """Register a single tool."""
        is_async = inspect.iscoroutinefunction(handler)
        self._tools[name] = ToolRegistration(
            name=name,
            description=description,
            parameters=parameters,
            handler=handler,
            is_async=is_async,
            required_params=required_params or [],
        )

    def register_all(self) -> None:
        """
        Register all system tools.
        
        This is called once at startup. It imports every tool module and
        registers their functions + schemas into the central registry.
        """
        if self._registered:
            return

        self._register_calendar_tools()
        self._register_email_tools()
        self._register_document_tools()
        self._register_database_tools()
        self._register_deal_pipeline_tools()
        self._register_supervisor_tools()
        self._register_whatsapp_tools()
        # Note: knowledge_tools are used for RAG in _process_query_node,
        # not as LLM-callable tools. They remain separate for now.

        self._registered = True
        logger.info(f"[ToolRegistry] Registered {len(self._tools)} tools")

    def _register_calendar_tools(self) -> None:
        """Register calendar tools from their module."""
        from app.tools.calendar_tools import (
            GET_SCHEDULE_TOOL_DEF, get_schedule,
            GET_PAST_MEETINGS_TOOL_DEF, get_past_meetings,
            UPDATE_MEETING_TOOL_DEF, update_meeting,
            CREATE_MEETING_TOOL, create_meeting,
            CREATE_RECURRING_MEETING_TOOL, create_recurring_meeting,
        )

        for tool_def, handler in [
            (GET_SCHEDULE_TOOL_DEF, get_schedule),
            (GET_PAST_MEETINGS_TOOL_DEF, get_past_meetings),
            (UPDATE_MEETING_TOOL_DEF, update_meeting),
        ]:
            func_def = tool_def["function"]
            self.register(
                name=func_def["name"],
                description=func_def["description"],
                parameters=func_def["parameters"].get("properties", {}),
                handler=handler,
                required_params=func_def["parameters"].get("required", []),
            )

        # create_meeting and create_recurring_meeting use input_schema (Anthropic) format
        for tool_def, handler in [
            (CREATE_MEETING_TOOL, create_meeting),
            (CREATE_RECURRING_MEETING_TOOL, create_recurring_meeting),
        ]:
            schema = tool_def["input_schema"]
            self.register(
                name=tool_def["name"],
                description=tool_def["description"],
                parameters=schema.get("properties", {}),
                handler=handler,
                required_params=schema.get("required", []),
            )

    def _register_whatsapp_tools(self) -> None:
        """Register WhatsApp tools (sends are confirm-then-execute)."""
        from app.tools.whatsapp_tools import WHATSAPP_TOOLS

        for tool_def, handler in WHATSAPP_TOOLS:
            func_def = tool_def["function"]
            self.register(
                name=func_def["name"],
                description=func_def["description"],
                parameters=func_def["parameters"].get("properties", {}),
                handler=handler,
                required_params=func_def["parameters"].get("required", []),
            )

    def _register_email_tools(self) -> None:
        """Register email tools, converting their custom schema to standard format."""
        from app.tools.email_tools import send_email, create_email_draft

        # send_email
        self.register(
            name="send_email",
            description=(
                "Send a professionally formatted email via Resend with ECOWAS branding. Triggers approval workflow before sending. "
                "Returns confirmation with email status. "
                "IMPORTANT: You MUST call get_twg_members FIRST to get real email addresses — NEVER use placeholder emails like 'user@example.com'. "
                "Example: User asks 'email the team about Friday's deadline' → 1) call get_twg_members() 2) call send_email(to='john@real.com,jane@real.com', subject='Friday Deadline Reminder', message='...')."
            ),
            parameters={
                "to": {
                    "type": "string",
                    "description": "Recipient email address (comma-separated for multiple)",
                },
                "subject": {"type": "string", "description": "Email subject line"},
                "message": {"type": "string", "description": "Plain text email body"},
                "cc": {
                    "type": "string",
                    "description": "Optional CC recipient email(s), comma-separated",
                },
                "pillar_name": {
                    "type": "string",
                    "description": "Optional TWG pillar name for branding (e.g. 'Energy', 'Agriculture')",
                },
            },
            handler=send_email,
            required_params=["to", "subject", "message"],
        )

        # create_email_draft
        self.register(
            name="create_email_draft",
            description="Create an email draft for human approval without sending. Returns the draft for review. IMPORTANT: First call get_twg_members to get actual email addresses — NEVER use placeholder emails. Example: User asks 'draft an email to the Agriculture team' → 1) call get_twg_members(twg_name='agriculture') 2) call create_email_draft(to='...', subject='...', message='...').",
            parameters={
                "to": {
                    "type": "string",
                    "description": "Recipient email address (comma-separated for multiple)",
                },
                "subject": {"type": "string", "description": "Email subject line"},
                "message": {"type": "string", "description": "Plain text email body"},
                "pillar_name": {
                    "type": "string",
                    "description": "Optional TWG pillar name for branding",
                },
            },
            handler=create_email_draft,
            required_params=["to", "subject", "message"],
        )

    def _register_document_tools(self) -> None:
        """Register document approval tools."""
        from app.tools.document_tools import (
            REQUEST_DOCUMENT_APPROVAL_TOOL_DEF,
            request_document_approval_tool,
        )
        func_def = REQUEST_DOCUMENT_APPROVAL_TOOL_DEF["function"]
        self.register(
            name=func_def["name"],
            description=func_def["description"],
            parameters=func_def["parameters"].get("properties", {}),
            handler=request_document_approval_tool,
            required_params=func_def["parameters"].get("required", []),
        )

    def _register_database_tools(self) -> None:
        """Register database query tools."""
        from app.tools.database_tools import (
            SEARCH_DOCUMENTS_TOOL_DEF, search_documents,
            RETRIEVE_DOCUMENT_CONTENT_TOOL_DEF, retrieve_document_content,
            GET_MEETING_MINUTES_TOOL_DEF, get_meeting_minutes,
            GET_ACTION_ITEMS_TOOL_DEF, get_action_items,
            UPDATE_ACTION_ITEM_STATUS_TOOL_DEF, update_action_item_status,
            get_twg_members,
        )
        for tool_def, handler in [
            (SEARCH_DOCUMENTS_TOOL_DEF, search_documents),
            (RETRIEVE_DOCUMENT_CONTENT_TOOL_DEF, retrieve_document_content),
            (GET_MEETING_MINUTES_TOOL_DEF, get_meeting_minutes),
            (GET_ACTION_ITEMS_TOOL_DEF, get_action_items),
            (UPDATE_ACTION_ITEM_STATUS_TOOL_DEF, update_action_item_status),
        ]:
            func_def = tool_def["function"]
            self.register(
                name=func_def["name"],
                description=func_def["description"],
                parameters=func_def["parameters"].get("properties", {}),
                handler=handler,
                required_params=func_def["parameters"].get("required", []),
            )

        # create_meeting_invite — lets TWG agents schedule new meetings
        from app.tools.database_tools import create_meeting_invite
        self.register(
            name="create_meeting_invite",
            description=(
                "[WHEN] User asks to schedule/create a new meeting for a TWG. "
                "[WHAT] Creates a meeting in the database with auto-added participants and returns meeting_id, status, and scheduled time. "
                "[IMPORTANT] scheduled_at MUST be the user's LOCAL time — do NOT convert to UTC. The timezone param handles conversion. "
                "[EXAMPLE] 'Schedule energy meeting for tomorrow at 4pm EAT' → create_meeting_invite(twg_id='energy', title='Energy TWG Meeting', scheduled_at='2026-03-02T16:00:00', timezone='Africa/Nairobi')"
            ),
            parameters={
                "twg_id": {"type": "string", "description": "TWG UUID or name (e.g. 'energy', 'agriculture'). Auto-injected for TWG agents."},
                "title": {"type": "string", "description": "Meeting title"},
                "scheduled_at": {"type": "string", "description": "ISO 8601 datetime in the user's LOCAL time (e.g. '2026-03-02T16:00:00' for 4pm). Do NOT convert to UTC."},
                "location": {"type": "string", "description": "Location or meeting link (default: Virtual)"},
                "duration": {"type": "integer", "description": "Duration in minutes (default: 60)"},
                "timezone": {"type": "string", "description": "IANA timezone of the scheduled_at time. EAT='Africa/Nairobi', WAT='Africa/Lagos'. Default: Africa/Nairobi."},
            },
            handler=create_meeting_invite,
            required_params=["twg_id", "title", "scheduled_at"],
        )

        # get_twg_members — lets agents look up member names and emails
        # twg_id is auto-injected for TWG agents; supervisor can use twg_name instead
        self.register(
            name="get_twg_members",
            description="Fetch all members of a TWG with their names and email addresses. Returns JSON array of {name, email, role}. MUST be called before send_email to get real email addresses. Use when the user asks to email the team, look up members, or check who belongs to a TWG. Example: User asks 'send an email to the team' → FIRST call get_twg_members() to get emails, THEN call send_email with those addresses.",
            parameters={
                "twg_id": {"type": "string", "description": "TWG UUID (auto-injected for TWG agents)"},
                "twg_name": {"type": "string", "description": "TWG name to search for (e.g. 'energy', 'agriculture', 'minerals', 'digital', 'protocol', 'resource')"},
            },
            handler=get_twg_members,
            required_params=[],
        )

    def _register_deal_pipeline_tools(self) -> None:
        """Register deal pipeline tools for resource mobilization agent."""
        from app.tools.deal_pipeline_tools import DEAL_PIPELINE_TOOLS as DP_TOOLS

        for tool in DP_TOOLS:
            # Convert the simple {param_name: description} format to JSON Schema
            properties = {}
            for param_name, param_desc in tool["parameters"].items():
                properties[param_name] = {
                    "type": "string",
                    "description": param_desc,
                }

            handler = tool.get("function") or tool.get("coroutine")
            self.register(
                name=tool["name"],
                description=tool["description"],
                parameters=properties,
                handler=handler,
                required_params=list(tool["parameters"].keys()),
            )

        # Pipeline write tools (Tier 1) — confirm-then-execute moves on projects.
        from app.tools.pipeline_write_tools import (
            advance_project_stage, decline_project, mark_flagship, rescore_project,
            graduate_from_incubation, create_action_item, bulk_create_action_items,
        )
        # Pipeline read tools (Tier 1) — read-only aggregates and lists.
        from app.tools.pipeline_read_tools import (
            pipeline_summary, at_risk_projects, incubation_close_to_graduation,
            my_action_items, next_deadlines,
        )

        pipeline_extras = [
            (advance_project_stage, "advance_project_stage",
             "Move a project to a new pipeline stage. Returns confirmation_required on first call."),
            (decline_project, "decline_project",
             "Decline a project with a reason. Confirm-then-execute."),
            (mark_flagship, "mark_flagship",
             "Mark or unmark a project as flagship. Confirm-then-execute."),
            (rescore_project, "rescore_project",
             "Update a project's score. Confirm-then-execute."),
            (graduate_from_incubation, "graduate_from_incubation",
             "Graduate a project from incubation to the next stage. Confirm-then-execute."),
            (create_action_item, "create_action_item",
             "Create an action item / task linked to a project or meeting."),
            (bulk_create_action_items, "bulk_create_action_items",
             "Create several action items in one call."),
            (pipeline_summary, "pipeline_summary",
             "Counts by stage, total investment, and period delta. Scope: all|twg|mine."),
            (at_risk_projects, "at_risk_projects",
             "List projects that are stalled or otherwise at risk."),
            (incubation_close_to_graduation, "incubation_close_to_graduation",
             "List incubation projects close to graduating."),
            (my_action_items, "my_action_items",
             "List action items assigned to the calling user."),
            (next_deadlines, "next_deadlines",
             "Upcoming project / action-item deadlines within a window."),
        ]
        for fn, name, desc in pipeline_extras:
            sig = inspect.signature(fn)
            properties: Dict[str, Any] = {}
            required: List[str] = []
            for param_name, param in sig.parameters.items():
                # Skip auto-injected / framework params
                if param_name in {"user_id", "user_role"}:
                    continue
                properties[param_name] = {
                    "type": "string",
                    "description": f"{param_name} parameter",
                }
                if param.default is inspect.Parameter.empty:
                    required.append(param_name)
            self.register(
                name=name,
                description=desc,
                parameters=properties,
                handler=fn,
                required_params=required,
            )

    def _register_supervisor_tools(self) -> None:
        """Register supervisor-only tools with proper schemas."""
        from app.tools.supervisor_tools import SUPERVISOR_TOOL_DEFS, SUPERVISOR_TOOL_HANDLERS

        for tool_def in SUPERVISOR_TOOL_DEFS:
            func_def = tool_def["function"]
            tool_name = func_def["name"]
            handler = SUPERVISOR_TOOL_HANDLERS.get(tool_name)
            if not handler:
                logger.warning(f"[ToolRegistry] No handler for supervisor tool '{tool_name}'")
                continue

            self.register(
                name=tool_name,
                description=func_def["description"],
                parameters=func_def["parameters"].get("properties", {}),
                handler=handler,
                required_params=func_def["parameters"].get("required", []),
            )

    # -------------------------------------------------------------------------
    # Access Control
    # -------------------------------------------------------------------------

    def validate_tool_access(
        self,
        tool_name: str,
        agent_id: str,
        twg_id: Optional[str] = None,
    ) -> bool:
        """
        Zero-trust validation: check if the agent is allowed to use this tool.
        
        Args:
            tool_name: Name of the tool being called
            agent_id: ID of the agent requesting access
            twg_id: The TWG ID the agent is scoped to (None for supervisor)
            
        Returns:
            True if access is allowed
            
        Raises:
            ToolAccessDenied: If access is denied
        """
        # Pipeline write/read tools — checked first so supervisor + TWG agents both get them.
        # User-role gating happens inside each tool body via _rbac.require_role.
        if tool_name in PIPELINE_WRITE_TOOLS or tool_name in PIPELINE_READ_TOOLS:
            if agent_id in {"supervisor", "supervisor_v1"} or (agent_id and agent_id.startswith("twg_")) or agent_id in {
                "energy", "agriculture", "minerals", "digital", "protocol", "resource_mobilization",
            }:
                return True
            raise ToolAccessDenied(
                f"Tool '{tool_name}' is restricted to supervisor / TWG agents. "
                f"Agent '{agent_id}' does not have access."
            )

        # Supervisor: only gets its own tools + unrestricted + email/meeting creation
        # It delegates TWG-scoped reads via consult_twg_agents_tool
        if agent_id == "supervisor":
            if tool_name in SUPERVISOR_ONLY_TOOLS:
                return True
            if tool_name in UNRESTRICTED_TOOLS:
                return True
            # Supervisor can send emails, create meetings, and search/retrieve documents directly
            if tool_name in {"send_email", "create_email_draft", "create_meeting_invite", "create_meeting", "create_recurring_meeting", "search_documents", "retrieve_document_content"}:
                return True
            raise ToolAccessDenied(
                f"Supervisor delegates '{tool_name}' to TWG agents via consult_twg_agents_tool."
            )
        
        # Check supervisor-only tools
        if tool_name in SUPERVISOR_ONLY_TOOLS:
            raise ToolAccessDenied(
                f"Tool '{tool_name}' is restricted to the Supervisor agent. "
                f"Agent '{agent_id}' does not have access."
            )

        # Check deal pipeline tools
        if tool_name in DEAL_PIPELINE_TOOLS and agent_id != "resource_mobilization":
            raise ToolAccessDenied(
                f"Tool '{tool_name}' is restricted to the Resource Mobilization agent. "
                f"Agent '{agent_id}' does not have access."
            )

        # Check TWG-scoped tools
        if tool_name in TWG_SCOPED_TOOLS:
            if not twg_id:
                raise ToolAccessDenied(
                    f"Tool '{tool_name}' requires TWG scope. "
                    f"Agent '{agent_id}' has no TWG ID assigned."
                )
            # Access granted — TWG ID is present and will be auto-injected
            return True

        # Unrestricted tools — always allowed
        if tool_name in UNRESTRICTED_TOOLS:
            return True

        # Unknown tool — allow but log warning
        logger.warning(f"[ToolRegistry] Unknown tool '{tool_name}' access by '{agent_id}' — allowing by default")
        return True

    # -------------------------------------------------------------------------
    # Tool Retrieval
    # -------------------------------------------------------------------------

    def get_tools_for_agent(
        self,
        agent_id: str,
        twg_id: Optional[str] = None,
    ) -> tuple[List[Dict[str, Any]], Dict[str, Callable]]:
        """
        Get the filtered tool definitions and handler map for a specific agent.
        
        Args:
            agent_id: The agent requesting tools
            twg_id: The TWG scope of the agent (None for supervisor)
            
        Returns:
            Tuple of (tool_definitions_list, tool_handler_map)
        """
        if not self._registered:
            self.register_all()

        tool_defs = []
        tool_map = {}

        for name, registration in self._tools.items():
            try:
                self.validate_tool_access(name, agent_id, twg_id)
                tool_defs.append(registration.openai_tool_def)
                tool_map[name] = registration.handler
            except ToolAccessDenied:
                # This agent is not allowed to use this tool — skip it
                continue

        logger.info(
            f"[ToolRegistry] Agent '{agent_id}' (twg={twg_id}) "
            f"granted {len(tool_defs)}/{len(self._tools)} tools"
        )
        return tool_defs, tool_map

    # -------------------------------------------------------------------------
    # Secure Execution
    # -------------------------------------------------------------------------

    async def execute_tool(
        self,
        tool_name: str,
        tool_args: Dict[str, Any],
        agent_id: str,
        twg_id: Optional[str] = None,
        user_timezone: Optional[str] = None,
    ) -> str:
        """
        Execute a tool with zero-trust validation and auto-injection.
        
        This is the single entry point for all tool executions in the system.
        
        Args:
            tool_name: Name of the tool to execute
            tool_args: Arguments from the LLM
            agent_id: Agent requesting execution
            twg_id: TWG scope for access control + auto-injection
            user_timezone: User's timezone for calendar tools
            
        Returns:
            String result of tool execution
            
        Raises:
            ToolAccessDenied: If the agent is not allowed to use this tool
        """
        # 1. Check tool exists before access validation
        registration = self._tools.get(tool_name)
        if not registration:
            return json.dumps({"error": f"Tool '{tool_name}' not found in registry"})

        # 2. Validate access
        self.validate_tool_access(tool_name, agent_id, twg_id)

        # 3. Auto-inject contextual parameters
        func = registration.handler
        sig = inspect.signature(func)
        
        if "twg_id" in sig.parameters and twg_id and "twg_id" not in tool_args:
            logger.info(f"[ToolRegistry] Auto-injecting twg_id={twg_id} into {tool_name}")
            tool_args["twg_id"] = twg_id

        if "user_timezone" in sig.parameters and user_timezone and "user_timezone" not in tool_args:
            tool_args["user_timezone"] = user_timezone

        # 4. Execute
        logger.info(f"[ToolRegistry] Executing {tool_name} for agent '{agent_id}'")

        if registration.is_async:
            result = await func(**tool_args)
        else:
            result = await asyncio.to_thread(func, **tool_args)

        # Use json.dumps for dict/list results so downstream json.loads() works correctly.
        # str(dict) produces Python repr (single quotes, True/False) which is not valid JSON.
        if isinstance(result, (dict, list)):
            return json.dumps(result, default=str)
        return str(result)

    # -------------------------------------------------------------------------
    # Introspection
    # -------------------------------------------------------------------------

    def list_tools(self) -> List[str]:
        """List all registered tool names."""
        return list(self._tools.keys())

    def get_tool_info(self, tool_name: str) -> Optional[Dict[str, Any]]:
        """Get information about a specific tool."""
        reg = self._tools.get(tool_name)
        if not reg:
            return None
        return {
            "name": reg.name,
            "description": reg.description,
            "is_async": reg.is_async,
            "parameters": reg.parameters,
        }


# =============================================================================
# Singleton
# =============================================================================

_registry_instance: Optional[ToolRegistry] = None


def get_tool_registry() -> ToolRegistry:
    """Get or create the global ToolRegistry singleton."""
    global _registry_instance
    if _registry_instance is None:
        _registry_instance = ToolRegistry()
        _registry_instance.register_all()
    return _registry_instance
