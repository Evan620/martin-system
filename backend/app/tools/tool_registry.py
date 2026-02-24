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
    "search_documents",
    "get_meeting_minutes",
    "get_twg_members",
    "send_email",
    "create_email_draft",
    "request_document_approval_tool",
}

# Tools restricted to specific agent roles
SUPERVISOR_ONLY_TOOLS: Set[str] = {
    "get_global_calendar_tool",
    "get_document_registry_tool",
    "get_project_pipeline_tool",
    "get_summit_status_tool",
    "detect_conflicts_tool",
    "start_negotiation_tool",
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

    def _register_email_tools(self) -> None:
        """Register email tools, converting their custom schema to standard format."""
        from app.tools.email_tools import send_email, create_email_draft

        # send_email
        self.register(
            name="send_email",
            description=(
                "Send a beautifully formatted email via Resend (triggers approval workflow). "
                "Emails are automatically wrapped in professional ECOWAS branding with AI badge."
            ),
            parameters={
                "to": {
                    "anyOf": [{"type": "string"}, {"type": "array", "items": {"type": "string"}}],
                    "description": "Recipient email address(es)",
                },
                "subject": {"type": "string", "description": "Email subject line"},
                "message": {"type": "string", "description": "Plain text email body"},
                "html_body": {
                    "anyOf": [{"type": "string"}, {"type": "null"}],
                    "description": "Optional HTML formatted email body",
                },
                "cc": {
                    "anyOf": [{"type": "string"}, {"type": "null"}],
                    "description": "Optional CC recipient(s)",
                },
                "bcc": {
                    "anyOf": [{"type": "string"}, {"type": "null"}],
                    "description": "Optional BCC recipient(s)",
                },
                "attachments": {
                    "anyOf": [
                        {"type": "array", "items": {"type": "string"}},
                        {"type": "string"},
                        {"type": "null"},
                    ],
                    "description": "Optional list of file paths to attach",
                },
                "pillar_name": {
                    "anyOf": [{"type": "string"}, {"type": "null"}],
                    "description": "Optional TWG pillar name for branding",
                },
            },
            handler=send_email,
            required_params=[],
        )

        # create_email_draft
        self.register(
            name="create_email_draft",
            description="Create an email draft for human approval.",
            parameters={
                "to": {
                    "anyOf": [{"type": "string"}, {"type": "array", "items": {"type": "string"}}],
                    "description": "Recipient email address(es)",
                },
                "subject": {"type": "string", "description": "Email subject line"},
                "message": {"type": "string", "description": "Plain text email body"},
                "html_body": {
                    "anyOf": [{"type": "string"}, {"type": "null"}],
                    "description": "Optional HTML formatted email body",
                },
                "pillar_name": {
                    "anyOf": [{"type": "string"}, {"type": "null"}],
                    "description": "Optional TWG pillar name for branding",
                },
            },
            handler=create_email_draft,
            required_params=[],
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
            GET_MEETING_MINUTES_TOOL_DEF, get_meeting_minutes,
            get_twg_members,
        )
        for tool_def, handler in [
            (SEARCH_DOCUMENTS_TOOL_DEF, search_documents),
            (GET_MEETING_MINUTES_TOOL_DEF, get_meeting_minutes),
        ]:
            func_def = tool_def["function"]
            self.register(
                name=func_def["name"],
                description=func_def["description"],
                parameters=func_def["parameters"].get("properties", {}),
                handler=handler,
                required_params=func_def["parameters"].get("required", []),
            )

        # get_twg_members — lets agents look up member names and emails
        # twg_id is auto-injected for TWG agents; supervisor can use twg_name instead
        self.register(
            name="get_twg_members",
            description="Fetch all members of a TWG with their names and email addresses. Use this when you need to send emails to TWG members, check membership, or look up who belongs to a working group. TWG agents: twg_id is auto-injected. Supervisor: pass twg_name (e.g. 'energy', 'agriculture').",
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
        # Supervisor can access everything
        if agent_id == "supervisor":
            return True
        
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
        # 1. Validate access
        self.validate_tool_access(tool_name, agent_id, twg_id)

        # 2. Get handler
        registration = self._tools.get(tool_name)
        if not registration:
            return json.dumps({"error": f"Tool '{tool_name}' not found in registry"})

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
