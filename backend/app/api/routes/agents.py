from fastapi import APIRouter, Depends, HTTPException, status, Request, BackgroundTasks
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, AsyncGenerator
import uuid
import asyncio
import json
import logging
import re as _re
import uuid as _uuid_mod
from datetime import datetime, timedelta
from pydantic import BaseModel
from langgraph.errors import GraphInterrupt

logger = logging.getLogger(__name__)

from app.api.deps import get_current_active_user
from app.core.database import get_db
from app.models.models import User, UserRole
from app.schemas.schemas import AgentChatRequest, AgentChatResponse, AgentTaskRequest, AgentStatus
from app.schemas.chat_messages import (
    EnhancedChatRequest,
    EnhancedChatResponse,
    ChatMessage,
    ChatMessageType,
    AgentSuggestion,
    ToolExecution
)
# Use LangGraph supervisor via API adapter
from app.agents.supervisor_api_adapter import SupervisorWithTools
from app.services.command_parser import CommandParser, MessageParseType
from app.services.email_approval_service import get_email_approval_service
from app.services.resend_service import get_resend_service
from app.schemas.email_approval import (
    EmailApprovalRequest,
    EmailApprovalResponse,
    EmailApprovalResult
)
from app.services.audit_service import audit_service

router = APIRouter(prefix="/agents", tags=["Agents"])

# ---------------------------------------------------------------------------
# Pending action store — module-level dict, TTL-based (no Redis/DB required)
# ---------------------------------------------------------------------------
_pending_actions: dict[str, dict] = {}  # action_id → {payload, user_id, action_type, expires_at}

_ACTION_TTL_MINUTES = 10


def _store_action(action_id: str, user_id: str, action_type: str, payload: dict) -> None:
    """Store a pending action with a TTL of 10 minutes."""
    _pending_actions[action_id] = {
        "action_id": action_id,
        "user_id": user_id,
        "action_type": action_type,
        "payload": payload,
        "expires_at": (datetime.utcnow() + timedelta(minutes=_ACTION_TTL_MINUTES)).isoformat(),
    }


def _get_action(action_id: str, user_id: str) -> dict | None:
    """Retrieve a pending action, returning None if missing, expired, or user mismatch."""
    entry = _pending_actions.get(action_id)
    if not entry:
        return None
    if datetime.utcnow() > datetime.fromisoformat(entry["expires_at"]):
        _finalize_action(action_id)
        return None
    if entry["user_id"] != str(user_id):
        return None
    return entry


def _finalize_action(action_id: str) -> None:
    """Drop the action from both the legacy in-route store and the shared
    _rbac store. Used by all _execute_* helpers post-success so neither store
    leaks the entry, regardless of which one held it."""
    _pending_actions.pop(action_id, None)
    try:
        from app.tools._rbac import drop_pending_action as _drop
        _drop(action_id)
    except Exception:
        pass


def _extract_meeting_title(text: str) -> str:
    """Extract a meeting title from response text."""
    match = _re.search(r'"([^"]{5,60})"', text)
    if match:
        return match.group(1)
    match = _re.search(r'meeting (?:for|about|on) ([A-Z][^.]{5,40})', text)
    if match:
        return match.group(1).strip()
    return "TWG Meeting"


def _extract_action_title(text: str) -> str:
    """Extract an action item title from response text."""
    match = _re.search(r'"([^"]{5,60})"', text)
    if match:
        return match.group(1)
    return "Action Item"


def _detect_action_intent(response_text: str, twg_id: str | None) -> dict | None:
    """Detect if the response contains a schedulable/actionable intent."""
    text_lower = response_text.lower()

    # Detect meeting scheduling intent
    if any(kw in text_lower for kw in ["schedule", "book", "arrange", "set up"]) and \
       any(kw in text_lower for kw in ["meeting", "session", "call", "sync"]):
        action_id = str(_uuid_mod.uuid4())[:8]
        return {
            "type": "action_required",
            "action_id": action_id,
            "action_type": "schedule_meeting",
            "payload": {
                "title": _extract_meeting_title(response_text),
                "twg_id": twg_id,
                "duration_minutes": 60,
            },
            "confirm_endpoint": "/api/v1/agents/execute",
        }

    # Detect action item creation intent
    if any(kw in text_lower for kw in ["create", "add", "assign", "track"]) and \
       any(kw in text_lower for kw in ["action item", "task", "todo", "follow-up"]):
        action_id = str(_uuid_mod.uuid4())[:8]
        return {
            "type": "action_required",
            "action_id": action_id,
            "action_type": "create_action_item",
            "payload": {
                "title": _extract_action_title(response_text),
                "twg_id": twg_id,
                "priority": "medium",
            },
            "confirm_endpoint": "/api/v1/agents/execute",
        }

    return None

# Initialize the supervisor agent (singleton)
supervisor_agent = None
command_parser = CommandParser()

def get_supervisor() -> SupervisorWithTools:
    """Get or create the supervisor agent instance."""
    global supervisor_agent
    if supervisor_agent is None:
        supervisor_agent = SupervisorWithTools()
    return supervisor_agent


def has_twg_access(user: User, twg_id: uuid.UUID) -> bool:
    """
    Check if user has access to the specified TWG.
    
    Args:
        user: The user to check
        twg_id: The TWG ID to verify access for
        
    Returns:
        True if user has access, False otherwise
    """
    from app.models.models import UserRole
    
    # Admins have access to all TWGs
    if user.role == UserRole.ADMIN:
        return True
    
    # Check if user is a member or facilitator of this TWG
    user_twg_ids = user.twg_ids  # Property, not a method
    return twg_id in user_twg_ids


# Command and Mention Handlers (Phase 2)

async def handle_command(supervisor: SupervisorWithTools, parsed: dict, original_message: str, twg_id: str = None, thread_id: str = None) -> str:
    """Handle slash command execution."""
    command = parsed["command"]
    params = parsed["parameters"]
    clean_query = parsed["clean_query"]

    # Map commands to supervisor methods
    if command == "/search":
        query = params.get("query", clean_query)
        return await supervisor.chat_with_tools(f"Search the knowledge base for: {query}", twg_id=twg_id, thread_id=thread_id)

    elif command == "/email":
        # Check if it's a send or search operation
        if "to" in params:
            # Send email
            to = params.get("to")
            subject = params.get("subject", "Message from ECOWAS TWG System")
            body = params.get("body", clean_query)
            cc = params.get("cc")
            return await supervisor.chat_with_tools(
                f"Send an email to {to} with subject '{subject}' and message: {body}" +
                (f" and CC {cc}" if cc else ""),
                twg_id=twg_id,
                thread_id=thread_id
            )
        else:
            # Search emails
            search_term = params.get("search", clean_query)
            return await supervisor.chat_with_tools(f"Search my emails for: {search_term}", twg_id=twg_id, thread_id=thread_id)

    elif command == "/schedule":
        return await supervisor.chat_with_tools(f"Help me with scheduling: {clean_query}", twg_id=twg_id, thread_id=thread_id)

    elif command == "/draft":
        doc_type = params.get("type", "document")
        topic = params.get("topic", clean_query)
        return await supervisor.chat_with_tools(f"Draft a {doc_type} about: {topic}", twg_id=twg_id, thread_id=thread_id)

    elif command == "/analyze":
        target = params.get("target", clean_query)
        return await supervisor.chat_with_tools(f"Analyze: {target}", twg_id=twg_id, thread_id=thread_id)

    elif command == "/broadcast":
        message = params.get("message", clean_query)
        return await supervisor.chat_with_tools(f"Broadcast this message to all TWGs: {message}", twg_id=twg_id, thread_id=thread_id)

    elif command == "/summarize":
        target = params.get("target", clean_query)
        return await supervisor.chat_with_tools(f"Summarize: {target}", twg_id=twg_id, thread_id=thread_id)

    else:
        return f"Command {command} recognized but handler not implemented yet. Query: {clean_query}"


async def handle_mention(supervisor: SupervisorWithTools, parsed: dict, twg_id: str = None, thread_id: str = None) -> str:
    """Handle @mention routing to specific agents."""
    agent_ids = parsed["agent_mentions"]
    clean_query = parsed["clean_query"]

    if not clean_query:
        # No query, just return info about mentioned agents
        agent_names = [command_parser.AGENT_MENTIONS[f"@{aid.title()}Agent"]["name"]
                      for aid in agent_ids if f"@{aid.title()}Agent" in command_parser.AGENT_MENTIONS]
        return f"You mentioned: {', '.join(agent_names)}. How can they help you?"

    # For now, route to supervisor with context about which agent was mentioned
    # TODO: Implement actual agent delegation in supervisor_with_tools.py
    if len(agent_ids) == 1:
        agent_id = agent_ids[0]
        return await supervisor.chat_with_tools(
            f"[ROUTING TO {agent_id.upper()} TWG AGENT] {clean_query}",
            twg_id=twg_id,
            thread_id=thread_id
        )
    else:
        return await supervisor.chat_with_tools(
            f"[ROUTING TO MULTIPLE AGENTS: {', '.join(agent_ids)}] {clean_query}",
            twg_id=twg_id,
            thread_id=thread_id
        )


@router.post("/chat", response_model=AgentChatResponse)
async def chat_with_martin(
    chat_in: AgentChatRequest,
    current_user: User = Depends(get_current_active_user),
    request: Request = None
):
    """
    Chat with AI agents - routes based on user role and context.
    
    - Admins: Access Supervisor agent (full cross-TWG access)
    - TWG Facilitators/Members: Access their TWG-specific agent (restricted to their TWG)
    """
    from langgraph.errors import GraphInterrupt
    from app.models.models import UserRole
    from app.tools._rbac import set_user_context, set_user_for_thread

    # Bind user context for the lifetime of this request so role-gated tools
    # see who's calling them (auto-injected into tool kwargs by agent_loop).
    set_user_context(str(current_user.id), current_user.role)

    # Extract user timezone from header
    user_timezone = request.headers.get("X-User-Timezone") if request else None

    conv_id = chat_in.conversation_id or uuid.uuid4()
    # Thread-id-keyed fallback survives supervisor → TWG delegation hops.
    set_user_for_thread(str(conv_id), str(current_user.id), current_user.role)

    try:
        # ROLE-BASED ROUTING
        if current_user.role == UserRole.ADMIN:
            # Admins always get Supervisor access with full permissions
            supervisor = get_supervisor()
            twg_context = str(chat_in.twg_id) if chat_in.twg_id else None
            # Call supervisor (now returns dict or str)
            raw_response = await supervisor.chat_with_tools(chat_in.message, twg_id=twg_context, thread_id=str(conv_id), user_timezone=user_timezone)
            agent_id = "supervisor_v1"
            
        elif current_user.role in [UserRole.TWG_FACILITATOR, UserRole.TWG_MEMBER]:
            # TWG users must provide twg_id and can only access their TWG agent
            if not chat_in.twg_id:
                raise HTTPException(
                    status_code=400,
                    detail="TWG ID required for TWG member access. Please access the agent from your TWG page."
                )
            
            # Verify user has access to this TWG
            if not has_twg_access(current_user, chat_in.twg_id):
                raise HTTPException(
                    status_code=403,
                    detail="You do not have access to this TWG"
                )
            
            # Route to TWG-specific agent (using Supervisor with strict TWG context).
            # SAFETY LINE: TWG_MEMBER chats run under the member-scoped agent
            # (agent_id="member", gated to MEMBER_TOOLS) bound to the caller's twg_id —
            # NOT the facilitator/pillar agent. Facilitators keep the existing routing.
            supervisor = get_supervisor()
            force_agent_id = "member" if current_user.role == UserRole.TWG_MEMBER else None
            raw_response = await supervisor.chat_with_tools(
                chat_in.message,
                twg_id=str(chat_in.twg_id),
                thread_id=str(conv_id),
                user_timezone=user_timezone,
                force_agent_id=force_agent_id,
            )
            agent_id = "member" if current_user.role == UserRole.TWG_MEMBER else f"twg_{chat_in.twg_id}_agent"
            
        else:
            # Other roles (e.g., SECRETARIAT_LEAD) don't have agent access yet
            raise HTTPException(
                status_code=403,
                detail="Insufficient permissions to access AI agents"
            )

        # Process Response (Handle Dict vs Str)
        citations = []
        if isinstance(raw_response, dict):
            response_text = raw_response.get("response", "")
            citations = raw_response.get("citations", [])
        else:
            response_text = str(raw_response)

        # Extract suggestions from response text if present
        suggestions = []
        if "<<SUGGESTIONS>>" in response_text and "<</SUGGESTIONS>>" in response_text:
            try:
                start_tag = "<<SUGGESTIONS>>"
                end_tag = "<</SUGGESTIONS>>"
                start_index = response_text.find(start_tag)
                end_index = response_text.find(end_tag)
                
                json_str = response_text[start_index + len(start_tag):end_index]
                suggestions = json.loads(json_str)
                
                # Remove the suggestions block from the visible response
                response_text = response_text[:start_index].strip()
            except Exception as e:
                logger.error(f"Failed to parse suggestions: {e}")

        return {
            "response": response_text,
            "conversation_id": conv_id,
            "citations": citations,
            "agent_id": agent_id,
            "suggestions": suggestions
        }
    except HTTPException:
        # Re-raise HTTP exceptions (access control errors)
        raise
    except GraphInterrupt as gi:
        # Graph was interrupted for human approval
        # Extract the interrupt payload - GraphInterrupt stores it in args[0]
        interrupt_value = gi.args[0] if gi.args else {}
        
        logger.info(f"[CHAT] GraphInterrupt caught - gi.args: {gi.args}")
        logger.info(f"[CHAT] Extracted interrupt_value: {interrupt_value}")

        # SPECIAL HANDLING: If interrupt is just a string (e.g. "Duplicate detected"), 
        # return it as a final response to the user and Halt.
        if isinstance(interrupt_value, str):
            # Humanize the error message using LLM
            try:
                from app.services.llm_service import get_llm_service
                llm = get_llm_service()
                humanized_msg = llm.chat(
                    system_prompt="You are a helpful assistant. The user's request was stopped by the system with the following error. "
                                "Rewrite this error message to be polite, concise, and helpful to the user. "
                                "Explain clearly why the action was blocked. Do not mention 'system error' or 'tools'.",
                    prompt=f"System Error: {interrupt_value}"
                )
                response_content = f"🛑 {humanized_msg}"
            except Exception as e:
                logger.error(f"Failed to humanize interrupt message: {e}")
                response_content = f"🛑 {interrupt_value}"

            # Determine agent_id based on user role
            agent_id = "supervisor_v1" if current_user.role == UserRole.ADMIN else f"twg_{chat_in.twg_id}_agent"

            return {
                "response": response_content, 
                "conversation_id": conv_id,
                "citations": [],
                "agent_id": agent_id,
                # We do NOT set interrupted=True here because we don't need UI approval.
                # We just want to halt and show the message.
            }
        
        # Extract draft details for the response message
        draft_preview = ""
        if isinstance(interrupt_value, dict) and "draft" in interrupt_value:
            draft = interrupt_value["draft"]
            to_list = draft.get("to", [])
            subject = draft.get("subject", "No Subject")
            draft_preview = f"\n\n**To:** {', '.join(to_list)}\n**Subject:** {subject}"
            
            # Link this thread context to the approval request so we can resume later
            if "request_id" in interrupt_value:
                req_id = interrupt_value["request_id"]
                approval_service = get_email_approval_service()
                if approval_service.update_approval_request_thread(req_id, str(conv_id)):
                    logger.info(f"[CHAT] Linked thread {conv_id} to approval request {req_id}")
        
        # Determine agent_id based on user role
        agent_id = "supervisor_v1" if current_user.role == UserRole.ADMIN else f"twg_{chat_in.twg_id}_agent"
        
        response_dict = {
            "response": "",  # Empty - frontend will handle the message display
            "conversation_id": conv_id,
            "citations": [],
            "agent_id": agent_id,
            "interrupted": True,
            "interrupt_payload": interrupt_value,
            "thread_id": str(conv_id)  # Used to resume the graph
        }
        
        logger.info(f"[CHAT] Returning interrupt response: {response_dict}")
        return response_dict
    except Exception as e:
        # Log the error and return a helpful message
        import traceback
        traceback.print_exc()

        # Determine agent_id based on user role
        agent_id = "supervisor_v1" if current_user.role == UserRole.ADMIN else f"twg_{chat_in.twg_id}_agent"

        return {
            "response": f"I apologize, but I encountered an error processing your request: {str(e)}",
            "conversation_id": conv_id,
            "citations": [],
            "agent_id": agent_id
        }

@router.post("/chat/enhanced", response_model=EnhancedChatResponse)
async def enhanced_chat(
    chat_in: EnhancedChatRequest,
    current_user: User = Depends(get_current_active_user)
):
    """
    Enhanced chat with rich message support, suggestions, and tool visibility.

    This endpoint provides:
    - Rich message types (actions, requests, tool execution status)
    - Proactive suggestions
    - Tool execution visibility
    - File attachment support
    """
    from app.tools._rbac import set_user_context, set_user_for_thread
    set_user_context(str(current_user.id), current_user.role)

    conv_id = chat_in.conversation_id or uuid.uuid4()
    set_user_for_thread(str(conv_id), str(current_user.id), current_user.role)

    try:
        # Get the supervisor agent
        supervisor = get_supervisor()

        # Parse message for commands and mentions (Phase 2)
        parsed = command_parser.parse_message(chat_in.message)

        # SECURITY: Strict RBAC for Mentions
        if current_user.role != UserRole.ADMIN and parsed["type"] in [MessageParseType.MENTION, MessageParseType.MIXED]:
             if parsed["type"] == MessageParseType.MENTION:
                 parsed["type"] = MessageParseType.NATURAL

        # Handle based on parse type
        if parsed["type"] == MessageParseType.COMMAND:
            # Command execution
            response_text = await handle_command(supervisor, parsed, chat_in.message, twg_id=str(chat_in.twg_id) if chat_in.twg_id else None, thread_id=str(conv_id))
            message_type = ChatMessageType.COMMAND_RESULT
        elif parsed["type"] == MessageParseType.MENTION:
            # Route to specific agent(s)
            response_text = await handle_mention(supervisor, parsed, twg_id=str(chat_in.twg_id) if chat_in.twg_id else None, thread_id=str(conv_id))
            message_type = ChatMessageType.AGENT_TEXT
        elif parsed["type"] == MessageParseType.MIXED:
            # Both command and mention - prioritize command
            response_text = await handle_command(supervisor, parsed, chat_in.message, twg_id=str(chat_in.twg_id) if chat_in.twg_id else None, thread_id=str(conv_id))
            message_type = ChatMessageType.COMMAND_RESULT
        else:
            # Natural language - regular chat
            response_text = await supervisor.chat_with_tools(chat_in.message, thread_id=str(conv_id))
            message_type = ChatMessageType.AGENT_TEXT

        # Create the agent response message
        agent_message = ChatMessage(
            message_id=uuid.uuid4(),
            conversation_id=conv_id,
            message_type=message_type,
            content=response_text,
            sender="agent",
            timestamp=datetime.utcnow(),
            metadata={"parsed": parsed} if parsed["type"] != MessageParseType.NATURAL else None
        )

        # TODO: Implement suggestion generation in Phase 3
        suggestions = []

        # TODO: Implement tool execution tracking in Phase 6
        tool_executions = []

        return EnhancedChatResponse(
            message=agent_message,
            suggestions=suggestions,
            tool_executions=tool_executions,
            conversation_id=conv_id
        )

    except Exception as e:
        import traceback
        traceback.print_exc()

        # Return error as agent message
        error_message = ChatMessage(
            message_id=uuid.uuid4(),
            conversation_id=conv_id,
            message_type=ChatMessageType.AGENT_TEXT,
            content=f"I apologize, but I encountered an error processing your request: {str(e)}",
            sender="agent",
            timestamp=datetime.utcnow()
        )

        return EnhancedChatResponse(
            message=error_message,
            suggestions=[],
            tool_executions=[],
            conversation_id=conv_id
        )


@router.get("/chat/stream")
async def stream_chat_get(
    message: str,
    current_user: User = Depends(get_current_active_user),
    request: Request = None,
    conversation_id: str = None,
    twg_id: str = None,
):
    """
    GET-based SSE streaming chat endpoint for Claude Code-style UI.

    Accepts query params: message (required), conversation_id (optional), twg_id (optional).
    Auth: JWT Bearer (same as /chat).

    Emits SSE event types: routing, agent, tool_call, tool_result, token, done, error.
    """
    from app.models.models import UserRole

    user_timezone = request.headers.get("X-User-Timezone") if request else None

    async def event_generator() -> AsyncGenerator[str, None]:
        from app.tools._rbac import set_user_context, set_user_for_thread
        conv_id = conversation_id or str(uuid.uuid4())
        set_user_context(str(current_user.id), current_user.role)
        set_user_for_thread(conv_id, str(current_user.id), current_user.role)

        def _sse(data: dict) -> str:
            return f"data: {json.dumps(data)}\n\n"

        _agent_label_map = {
            "energy": "Energy Martin",
            "agriculture": "Agriculture Martin",
            "minerals": "Minerals Martin",
            "digital": "Digital Martin",
            "protocol": "Protocol Martin",
            "resource_mobilization": "Investment Martin",
            "supervisor_v1": "Supervisor",
            "supervisor": "Supervisor",
        }

        from app.services.stream_events import register_queue, unregister_queue
        event_queue: asyncio.Queue = asyncio.Queue()
        register_queue(conv_id, event_queue)

        try:
            yield _sse({"type": "routing", "content": "Analysing query..."})

            # RBAC — mirror the POST /chat logic
            force_agent_id = None
            if current_user.role == UserRole.ADMIN:
                twg_context = twg_id
            elif current_user.role in [UserRole.TWG_FACILITATOR, UserRole.TWG_MEMBER]:
                if not twg_id:
                    yield _sse({"type": "error", "message": "TWG ID required for TWG member access."})
                    return
                from app.models.models import UserRole as UR
                if not has_twg_access(current_user, uuid.UUID(twg_id)):
                    yield _sse({"type": "error", "message": "You do not have access to this TWG."})
                    return
                twg_context = twg_id
                # SAFETY LINE: TWG_MEMBER chats run under the member-scoped agent
                # (agent_id="member", gated to MEMBER_TOOLS) bound to the caller's twg_id.
                if current_user.role == UserRole.TWG_MEMBER:
                    force_agent_id = "member"
            else:
                yield _sse({"type": "error", "message": "Insufficient permissions to access AI agents."})
                return

            supervisor = get_supervisor()

            # Run the chat as a background task so we can drain the event queue
            # concurrently — showing tool calls and agent routing in real-time.
            chat_task = asyncio.create_task(
                supervisor.chat_with_tools(
                    message,
                    twg_id=twg_context,
                    thread_id=conv_id,
                    user_timezone=user_timezone,
                    force_agent_id=force_agent_id,
                )
            )

            agent_emitted = False
            agent_id = "supervisor"

            # Drain event queue while chat_task is running
            while not chat_task.done():
                try:
                    evt = await asyncio.wait_for(event_queue.get(), timeout=0.08)
                    if evt.get("type") == "agent" and not agent_emitted:
                        agent_emitted = True
                        agent_id = evt.get("content", "supervisor")
                    yield _sse(evt)
                except asyncio.TimeoutError:
                    continue

            # Drain any events that arrived in the last tick
            while not event_queue.empty():
                evt = event_queue.get_nowait()
                if evt.get("type") == "agent" and not agent_emitted:
                    agent_emitted = True
                    agent_id = evt.get("content", "supervisor")
                yield _sse(evt)

            # Get the final result (re-raises any exception from the task)
            raw_response = await chat_task

            # Extract response text and metadata
            if isinstance(raw_response, dict):
                response_text: str = raw_response.get("response", "")
                citations = raw_response.get("citations", [])
            else:
                response_text = str(raw_response)
                citations = []

            # Emit agent badge if the queue never produced one
            if not agent_emitted:
                twg_key = twg_context or "supervisor"
                for key in _agent_label_map:
                    if key in twg_key:
                        yield _sse({"type": "agent", "content": key, "label": _agent_label_map[key]})
                        agent_id = key
                        break
                else:
                    yield _sse({"type": "agent", "content": "supervisor", "label": "Supervisor"})

            # Emit action_required if intent detected (TWG context only)
            if twg_context and response_text:
                action_event = _detect_action_intent(response_text, twg_context)
                if action_event:
                    _store_action(
                        action_event["action_id"],
                        str(current_user.id),
                        action_event["action_type"],
                        action_event["payload"],
                    )
                    yield _sse(action_event)

            # Tokens were already streamed in real-time via the event queue.
            yield _sse({
                "type": "done",
                "response": response_text,
                "agent_id": agent_id,
                "conversation_id": conv_id,
                "citations": citations,
            })

        except Exception as e:
            import traceback
            traceback.print_exc()
            yield _sse({"type": "error", "message": str(e)})

        finally:
            unregister_queue(conv_id)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive",
        },
    )


@router.post("/chat/stream")
async def stream_chat(
    chat_in: EnhancedChatRequest,
    current_user: User = Depends(get_current_active_user),
    request: Request = None
):
    """
    Streaming chat endpoint that provides real-time updates on agent thinking and tool execution.

    Returns Server-Sent Events (SSE) stream with:
    - Agent thinking status
    - Tool execution progress
    - Intermediate results
    - Final response
    """

    async def event_generator() -> AsyncGenerator[str, None]:
        """Generate SSE events for streaming."""
        from app.tools._rbac import set_user_context, set_user_for_thread
        set_user_context(str(current_user.id), current_user.role)

        # Ensure conv_id is always a string for JSON serialization
        conv_id = str(chat_in.conversation_id) if chat_in.conversation_id else str(uuid.uuid4())
        set_user_for_thread(conv_id, str(current_user.id), current_user.role)

        # Extract user timezone from header
        user_timezone = request.headers.get("X-User-Timezone") if request else None
        
        # DEBUG: Log the request details
        logger.info(f"[STREAM] Request - Message: {chat_in.message[:50]}...")
        logger.info(f"[STREAM] Request - TWG ID: {chat_in.twg_id} (type: {type(chat_in.twg_id).__name__ if chat_in.twg_id else 'None'})")
        logger.info(f"[STREAM] Request - User Timezone: {user_timezone}")

        try:
            # Send initial event
            yield f"data: {json.dumps({'type': 'start', 'conversation_id': conv_id})}\n\n"

            # Track if we've sent a final_response event (to avoid duplicates)
            final_response_sent = False

            # Use singleton supervisor to ensure memory persistence (MemorySaver)
            supervisor = get_supervisor()

            # SAFETY LINE: TWG_MEMBER streaming chats run under the member-scoped
            # agent (agent_id="member", gated to MEMBER_TOOLS) bound to the caller's
            # twg_id — never the facilitator/pillar agent. Threaded into the
            # natural-language streaming path below via force_agent_id.
            force_agent_id = "member" if current_user.role == UserRole.TWG_MEMBER else None

            # Parse message for commands and mentions
            parsed = command_parser.parse_message(chat_in.message)

            # SECURITY: Strict RBAC for Mentions
            # Non-admins cannot use @mentions to switch agents. They are locked to their assigned TWG agent.
            if current_user.role != UserRole.ADMIN and parsed["type"] in [MessageParseType.MENTION, MessageParseType.MIXED]:
                logger.warning(f"Restricted user {current_user.id} attempted agent routing. Forcing NATURAL mode.")
                if parsed["type"] == MessageParseType.MENTION:
                    parsed["type"] = MessageParseType.NATURAL
                # For MIXED, we leave it as is if it prioritizes commands, but validat command handling
                # Logic below for MIXED uses handle_command, which is safe as it doesn't route based on mentions.

            # Send parsing event
            yield f"data: {json.dumps({'type': 'parsing', 'result': {'message_type': str(parsed['type']), 'command': parsed.get('command'), 'mentions': parsed.get('agent_mentions', [])}})}\n\n"

            # Determine what to execute
            if parsed["type"] == MessageParseType.COMMAND:
                # Send command execution event
                yield f"data: {json.dumps({'type': 'command_detected', 'command': parsed['command'], 'params': parsed['parameters']})}\n\n"

                # Stream tool execution
                command = parsed["command"]
                if command == "/search":
                    yield f"data: {json.dumps({'type': 'tool_start', 'tool': 'knowledge_search', 'status': 'Searching knowledge base...'})}\n\n"
                elif command == "/email":
                    if "to" in parsed["parameters"]:
                        yield f"data: {json.dumps({'type': 'tool_start', 'tool': 'email_send', 'status': 'Composing email...'})}\n\n"
                    else:
                        yield f"data: {json.dumps({'type': 'tool_start', 'tool': 'email_search', 'status': 'Searching inbox...'})}\n\n"
                elif command == "/schedule":
                    yield f"data: {json.dumps({'type': 'tool_start', 'tool': 'scheduler', 'status': 'Checking schedules...'})}\n\n"
                elif command == "/draft":
                    yield f"data: {json.dumps({'type': 'tool_start', 'tool': 'document_drafter', 'status': 'Drafting document...'})}\n\n"
                elif command == "/analyze":
                    yield f"data: {json.dumps({'type': 'tool_start', 'tool': 'analyzer', 'status': 'Analyzing data...'})}\n\n"

                # Execute command
                response_text = await handle_command(supervisor, parsed, chat_in.message, twg_id=str(chat_in.twg_id) if chat_in.twg_id else None, thread_id=conv_id)
                message_type = ChatMessageType.COMMAND_RESULT

            elif parsed["type"] == MessageParseType.MENTION:
                # Send agent routing event
                agent_ids = parsed["agent_mentions"]
                agents_joined = ", ".join(agent_ids)
                routing_status = f"Routing to {agents_joined} agent(s)..."
                yield f"data: {json.dumps({'type': 'agent_routing', 'agents': agent_ids, 'status': routing_status})}\n\n"

                # Execute with mentioned agent
                raw_response = await handle_mention(supervisor, parsed, twg_id=str(chat_in.twg_id) if chat_in.twg_id else None, thread_id=conv_id)
                # Handle dict response
                citations = []
                if isinstance(raw_response, dict):
                    citations = raw_response.get("citations", [])
                    response_text = raw_response.get("response", "")
                else:
                    response_text = str(raw_response)
                message_type = ChatMessageType.AGENT_TEXT

            elif parsed["type"] == MessageParseType.MIXED:
                yield f"data: {json.dumps({'type': 'mixed_execution', 'status': 'Processing command with agent mention...'})}\n\n"
                raw_response = await handle_command(supervisor, parsed, chat_in.message, twg_id=str(chat_in.twg_id) if chat_in.twg_id else None, thread_id=conv_id)
                # Handle dict response
                citations = []
                if isinstance(raw_response, dict):
                    citations = raw_response.get("citations", [])
                    response_text = raw_response.get("response", "")
                else:
                    response_text = str(raw_response)
                message_type = ChatMessageType.COMMAND_RESULT

            else:
                # Natural language - show thinking
                yield f"data: {json.dumps({'type': 'thinking', 'status': 'Processing your request...', 'step_id': str(uuid.uuid4())})}\n\n"

                # Natural language - stream real graph events
                yield f"data: {json.dumps({'type': 'thinking', 'status': 'Starting Supervisor...', 'icon': 'admin_panel_settings', 'step_id': str(uuid.uuid4())})}\n\n"

                response_text = ""
                citations = []
                
                # Stream events from LangGraph
                async for event in supervisor.stream_chat_events(chat_in.message, twg_id=str(chat_in.twg_id) if chat_in.twg_id else None, thread_id=conv_id, user_timezone=user_timezone, force_agent_id=force_agent_id):
                    if event["type"] == "node_update":
                        node = event["node"]
                        status_msg = f"Processing step: {node}"
                        icon = "smart_toy" # Default
                        
                        # Map nodes to friendly messages and icons
                        if node == "route_query":
                            status_msg = "Routing your query..."
                            icon = "alt_route"
                        elif node == "supervisor":
                            status_msg = "Supervisor Analyzing..."
                            icon = "admin_panel_settings"
                        elif node == "dispatch_multiple":
                            status_msg = "Dispatching to multiple agents..."
                            icon = "hub"
                        elif node == "synthesis":
                            status_msg = "Synthesizing insights..."
                            icon = "auto_awesome"
                        elif node in ["energy", "agriculture", "minerals", "digital", "protocol", "resource_mobilization"]:
                            status_msg = f"Consulting {node.title()} TWG Agent..."
                            icon = "group"
                        
                        yield f"data: {json.dumps({'type': 'thinking', 'status': status_msg, 'icon': icon, 'step_id': str(uuid.uuid4())})}\n\n"
                    
                    elif event["type"] == "final_response":
                        raw_content = event["content"]
                        # Handle dict response
                        if isinstance(raw_content, dict):
                            citations = raw_content.get("citations", [])
                            response_text = raw_content.get("response", "")
                        else:
                            response_text = str(raw_content)

                        # Send the final response immediately as a 'final_response' event
                        # The frontend will convert this to a proper message
                        yield f"data: {json.dumps({'type': 'final_response', 'content': response_text, 'conversation_id': conv_id})}\n\n"
                        final_response_sent = True

                    # Pass through new granular events for Generative UI
                    elif event["type"] in ["tool_start", "tool_result", "token"]:
                        yield f"data: {json.dumps(event)}\n\n"
                        
                message_type = ChatMessageType.AGENT_TEXT

            # Send completion event
            yield f"data: {json.dumps({'type': 'tool_complete', 'status': 'Completed', 'step_id': str(uuid.uuid4())})}\n\n"

            # Emit action_required if intent detected (TWG context only)
            twg_id_str = str(chat_in.twg_id) if chat_in.twg_id else None
            if twg_id_str and response_text:
                action_event = _detect_action_intent(response_text, twg_id_str)
                if action_event:
                    _store_action(
                        action_event["action_id"],
                        str(current_user.id),
                        action_event["action_type"],
                        action_event["payload"],
                    )
                    yield f"data: {json.dumps(action_event)}\n\n"

            # Only send fallback response if we haven't already sent a final_response event
            if not final_response_sent:
                # Create the final message
                agent_message = ChatMessage(
                    message_id=uuid.uuid4(),
                    conversation_id=conv_id,
                    message_type=message_type,
                    content=response_text,
                    sender="agent",
                    timestamp=datetime.utcnow(),
                    metadata={"parsed": parsed, "citations": citations} if citations else ({"parsed": parsed} if parsed["type"] != MessageParseType.NATURAL else None)
                )

                # Send final response - use model_dump with mode='json' to handle UUID serialization
                yield f"data: {json.dumps({'type': 'response', 'message': agent_message.model_dump(mode='json')})}\n\n"

            # Send done event
            yield f"data: {json.dumps({'type': 'done'})}\n\n"

        except GraphInterrupt as gi:
            logger.info(f"Graph interrupt caught in stream: {gi}")
            # Extract payload (assuming first arg is the payload dict)
            interrupt_payload = gi.args[0] if gi.args else {}
            
            # CRITICAL: Link thread_id to approval request for resumption
            if isinstance(interrupt_payload, dict):
                if interrupt_payload.get("type") == "email_approval_required" and "request_id" in interrupt_payload:
                    req_id = interrupt_payload["request_id"]
                    approval_service = get_email_approval_service()
                    if approval_service.update_approval_request_thread(req_id, conv_id):
                        logger.info(f"[STREAM] Linked thread {conv_id} to approval request {req_id}")
                    else:
                        logger.warning(f"[STREAM] Failed to link thread {conv_id} to approval request {req_id}")
            else:
                # Handle string interrupts (e.g. "Duplicate meeting detected")
                logger.info(f"[STREAM] Non-dict interrupt detected: {interrupt_payload}")
                if isinstance(interrupt_payload, str):
                    # Wrap string in a displayable payload format for frontend
                    interrupt_payload = {
                        "type": "info_interrupt",
                        "message": interrupt_payload
                    }
            
            # Use jsonable_encoder to handle UUIDs and other types
            from fastapi.encoders import jsonable_encoder
            safe_payload = jsonable_encoder(interrupt_payload)
            
            # Send interrupt event
            yield f"data: {json.dumps({'type': 'interrupt', 'payload': safe_payload})}\n\n"
            # End stream gracefully so client doesn't retry immediately or show error
            yield f"data: {json.dumps({'type': 'done'})}\n\n"

        except Exception as e:
            import traceback
            traceback.print_exc()

            # Send error event
            error_data = {
                'type': 'error',
                'error': str(e),
                'message': f'I apologize, but I encountered an error: {str(e)}'
            }
            yield f"data: {json.dumps(error_data)}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )


async def run_background_task(task_id: str, prompt: str, twg_id: str, user_timezone: str):
    try:
        logger.info(f"[{task_id}] Starting background task logic...")
        supervisor = get_supervisor()
        # Execute the heavy lifting using the supervisor
        await supervisor.chat_with_tools(
            prompt, 
            twg_id=twg_id, 
            thread_id=task_id, 
            user_timezone=user_timezone
        )
        logger.info(f"[{task_id}] Background task finished successfully.")
    except Exception as e:
        logger.error(f"[{task_id}] Background task failed: {str(e)}")

@router.post("/task", status_code=status.HTTP_202_ACCEPTED)
async def assign_agent_task(
    task_in: AgentTaskRequest,
    background_tasks: BackgroundTasks,
    request: Request,
    current_user: User = Depends(get_current_active_user)
):
    """
    Assign a high-level task to the agent swarm (e.g., draft Communiqué).
    
    Returns a task ID for polling and executes the request in the background.
    """
    task_id = str(uuid.uuid4())
    user_timezone = request.headers.get("X-User-Timezone", "UTC")
    
    # We pass the user's role/twg context so the background agent retains proper scoping.
    twg_context = str(task_in.twg_id) if hasattr(task_in, 'twg_id') and task_in.twg_id else "global"
    
    # Dispatch it to the background
    background_tasks.add_task(
        run_background_task,
        task_id=task_id,
        prompt=task_in.title,  # Basic mapping, in reality we'd have a full prompt field
        twg_id=twg_context,
        user_timezone=user_timezone
    )
    
    return {
        "task_id": task_id,
        "status": "queued",
        "message": f"Task '{task_in.title}' has been dispatched to the agent swarm and is processing in the background."
    }

@router.get("/status", response_model=AgentStatus)
async def get_agent_swarm_status(
    current_user: User = Depends(get_current_active_user)
):
    """
    Get the current operational status of the agent swarm.
    """
    return {
        "status": "operational",
        "swarm_ready": True,
        "active_agents": ["Supervisor", "Energy Martin", "Minerals Martin", "Agribusiness Martin"],
        "version": "0.1.0-alpha"
    }


# Phase 2: Command Autocomplete Endpoints

@router.get("/commands/autocomplete")
async def get_command_autocomplete(
    query: str,
    current_user: User = Depends(get_current_active_user)
):
    """
    Get command autocomplete suggestions for slash commands.

    Args:
        query: Partial command (e.g., "/em" or "/search")

    Returns:
        List of matching commands with descriptions and examples
    """
    suggestions = command_parser.get_command_suggestions(query)
    return {"suggestions": suggestions}


@router.get("/mentions/autocomplete")
async def get_mention_autocomplete(
    query: str,
    current_user: User = Depends(get_current_active_user)
):
    """
    Get @mention autocomplete suggestions for TWG agents.

    Args:
        query: Partial mention (e.g., "@En" or "@Agri")

    Returns:
        List of matching agent mentions with metadata
    """
    suggestions = command_parser.get_mention_suggestions(query)
    return {"suggestions": suggestions}


@router.get("/commands/list")
async def get_all_commands(
    current_user: User = Depends(get_current_active_user)
):
    """
    Get all available commands with metadata.

    Returns:
        Dictionary of all commands with descriptions, examples, and parameters
    """
    commands = command_parser.get_all_commands()
    return {"commands": commands}


@router.get("/agents/list")
async def get_all_agent_mentions(
    current_user: User = Depends(get_current_active_user)
):
    """
    Get all available agent mentions.

    Returns:
        Dictionary of all TWG agent mentions with metadata
    """
    agents = command_parser.get_all_agents()
    return {"agents": agents}


# Email Approval Endpoints (Human-in-the-Loop)

@router.get("/email/pending-approvals")
async def get_pending_email_approvals(
    current_user: User = Depends(get_current_active_user)
):
    """
    Get all pending email approvals for the current user.

    Returns:
        List of pending email approval requests
    """
    approval_service = get_email_approval_service()
    # Clean up old requests first
    approval_service.cleanup_old_requests()

    pending = list(approval_service.pending_approvals.values())
    return {"pending_approvals": pending}


@router.get("/email/approval/{request_id}")
async def get_email_approval(
    request_id: str,
    current_user: User = Depends(get_current_active_user)
):
    """
    Get a specific email approval request.

    Args:
        request_id: The approval request ID

    Returns:
        EmailApprovalRequest details
    """
    approval_service = get_email_approval_service()
    approval_request = approval_service.get_approval_request(request_id)

    if not approval_request:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Approval request {request_id} not found"
        )

    return approval_request


@router.post("/email/approval/{request_id}/approve", response_model=EmailApprovalResult)
async def approve_email(
    request_id: str,
    approval_response: EmailApprovalResponse,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Approve and send an email.

    Args:
        request_id: The approval request ID
        approval_response: User's approval decision with optional modifications

    Returns:
        Result of email sending operation
    """
    approval_service = get_email_approval_service()
    approval_request = approval_service.get_approval_request(request_id)
    
    # Initialize audit service
    from app.services.audit_service import audit_service


    if not approval_request:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Approval request {request_id} not found"
        )

    if not approval_response.approved:
        # User declined - remove the request
        approval_service.remove_approval_request(request_id)
        return EmailApprovalResult(
            success=True,
            message="Email sending cancelled by user",
            email_sent=False
        )

    # Use modified draft if provided, otherwise use original
    draft = approval_response.modifications or approval_request.draft

    try:
        # Send the email using Resend service
        resend_service = get_resend_service()
        result = resend_service.send_message(
            to=draft.to,
            subject=draft.subject,
            body=draft.body,
            html_body=draft.html_body,
            cc=draft.cc,
            bcc=draft.bcc,
            attachments=draft.attachments
        )

        # Remove the approval request
        approval_service.remove_approval_request(request_id)

        # RESUME AGENT EXECUTION
        thread_id = approval_request.thread_id
        if thread_id:
            logger.info(f"Resuming agent execution for thread {thread_id}")
            
            # Prepare resumption value for the agent
            resume_value = {
                "approved": True, 
                "message_id": result.get('message_id'), 
                "status": "sent"
            }
            try:
                supervisor = get_supervisor()
                agent_response = await supervisor.resume_chat(thread_id, resume_value)
                logger.info(f"Agent resumed successfully. Response: {agent_response}")
            except Exception as e:
                logger.error(f"Failed to resume agent: {e}")
        else:
             logger.warning(f"No thread_id linked to approval request {request_id} - cannot resume agent")

        # Audit Log
        if result.get("status") == "success" or True: # result usually dict from resend
             await audit_service.log_activity(
                db=db,
                user_id=current_user.id,
                action="send_email",
                resource_type="email",
                resource_id=None,
                details={
                    "to": draft.to,
                    "subject": draft.subject,
                    "message_id": result.get('message_id', 'unknown'),
                    "request_id": request_id,
                    "provider": "resend"
                },
                ip_address=None
            )
             await db.commit()

    except Exception as e:
        # Revert/Log
        logger.error(f"Failed to send email: {e}")
        return EmailApprovalResult(
            success=False,
            message=f"Failed to send email: {str(e)}",
            email_sent=False
        )
    
    return EmailApprovalResult(
        success=True,
        message="Email sent successfully via Resend" + (" (Agent resumed)" if thread_id else ""),
        email_sent=True
    )


from app.schemas.schemas import DocumentApprovalRequest, DocumentApprovalResult

@router.post("/document/approval/{request_id}/approve", response_model=DocumentApprovalResult)
async def approve_document(
    request_id: str,
    approval_data: DocumentApprovalRequest,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Approve and save a document.
    """
    from app.services.agent_service import AgentService
    agent_service = AgentService(db)
    
    try:
        result = await agent_service.approve_document_creation(
            approval_request_id=request_id,
            final_title=approval_data.title,
            final_content=approval_data.content,
            document_type=approval_data.document_type,
            file_name=approval_data.file_name,
            tags=approval_data.tags,
            user_id=current_user.id,
            twg_id=current_user.twg_ids[0] if current_user.twg_ids else None # Fallback
        )
        
        return DocumentApprovalResult(
            status="approved",
            document_id=result["document_id"],
            file_path=result["file_path"],
            message="Document saved successfully."
        )
        
    except Exception as e:
        logger.error(f"Failed to approve document: {e}")
        raise HTTPException(status_code=500, detail=str(e))




@router.post("/email/approval/{request_id}/decline", response_model=EmailApprovalResult)
async def decline_email(
    request_id: str,
    reason: str = None,
    current_user: User = Depends(get_current_active_user)
):
    """
    Decline an email approval request.

    Args:
        request_id: The approval request ID
        reason: Optional reason for declining

    Returns:
        Result of the decline operation
    """
    approval_service = get_email_approval_service()
    approval_request = approval_service.get_approval_request(request_id)

    if not approval_request:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Approval request {request_id} not found"
        )

    # Remove the approval request
    approval_service.remove_approval_request(request_id)

    return EmailApprovalResult(
        success=True,
        message=f"Email declined: {reason}" if reason else "Email sending cancelled",
        email_sent=False
    )


# ---------------------------------------------------------------------------
# Execute Action Endpoint
# ---------------------------------------------------------------------------

class ExecuteActionRequest(BaseModel):
    action_id: str
    confirmed: bool
    edits: dict = {}


@router.post("/execute")
async def execute_action(
    request: ExecuteActionRequest,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Execute a pending action (schedule meeting, create action item, draft document,
    or any of the new pipeline-write actions stored via _rbac.store_pending_action)."""
    from app.tools._rbac import get_pending_action, drop_pending_action

    # Look in both stores: the legacy in-route dict (schedule_meeting /
    # create_action_item) and the shared one used by the pipeline-write tools.
    entry = _get_action(request.action_id, str(current_user.id)) or \
            get_pending_action(request.action_id, str(current_user.id))
    if not entry:
        raise HTTPException(status_code=400, detail="Action expired or not found")

    if not request.confirmed:
        _pending_actions.pop(request.action_id, None)
        drop_pending_action(request.action_id)
        return {"success": True, "cancelled": True, "message": "Action cancelled."}

    payload = {**entry["payload"], **request.edits}
    action_type = entry["action_type"]

    try:
        if action_type == "schedule_meeting":
            return await _execute_schedule_meeting(payload, current_user, db, request.action_id)

        elif action_type == "create_action_item":
            return await _execute_create_action_item(payload, current_user, db, request.action_id)

        elif action_type == "advance_project_stage":
            return await _execute_advance_project_stage(payload, current_user, db, request.action_id)

        elif action_type == "decline_project":
            return await _execute_decline_project(payload, current_user, db, request.action_id)

        elif action_type == "mark_flagship":
            return await _execute_mark_flagship(payload, current_user, db, request.action_id)

        elif action_type == "rescore_project":
            return await _execute_rescore_project(payload, current_user, db, request.action_id)

        elif action_type == "graduate_from_incubation":
            return await _execute_graduate_from_incubation(payload, current_user, db, request.action_id)

        elif action_type == "bulk_create_action_items":
            return await _execute_bulk_create_action_items(payload, current_user, db, request.action_id)

        elif action_type in ("send_whatsapp_message", "send_whatsapp_to_group"):
            return await _execute_send_whatsapp(payload, current_user, db, request.action_id)

        elif action_type == "draft_document":
            _finalize_action(request.action_id)
            return {
                "success": True,
                "resource_id": None,
                "message": "Draft ready.",
                "draft_content": payload.get("content", ""),
            }

        else:
            raise HTTPException(status_code=400, detail=f"Unknown action type: {action_type}")

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to execute action: {str(e)}")


async def _execute_schedule_meeting(payload: dict, current_user: User, db: AsyncSession, action_id: str) -> dict:
    """Create a meeting directly via SQLAlchemy, matching the pattern used in the meetings route."""
    import datetime as _dt
    from app.models.models import Meeting as _Meeting

    twg_id_raw = payload.get("twg_id")
    if not twg_id_raw:
        raise HTTPException(status_code=400, detail="twg_id is required to schedule a meeting")

    twg_id = uuid.UUID(str(twg_id_raw))
    title = payload.get("title", "TWG Meeting")
    duration_minutes = int(payload.get("duration_minutes", 60))
    meeting_type = payload.get("meeting_type", "virtual")

    start_raw = payload.get("date") or payload.get("start_time") or payload.get("scheduled_at")
    if start_raw and isinstance(start_raw, str):
        scheduled_at = _dt.datetime.fromisoformat(start_raw.replace("Z", "+00:00")).replace(tzinfo=None)
    elif isinstance(start_raw, _dt.datetime):
        scheduled_at = start_raw.replace(tzinfo=None)
    else:
        scheduled_at = _dt.datetime.utcnow() + _dt.timedelta(days=7)

    meeting_id = uuid.uuid4()
    db_meeting = _Meeting(
        id=meeting_id,
        twg_id=twg_id,
        title=title,
        scheduled_at=scheduled_at,
        duration_minutes=duration_minutes,
        meeting_type=meeting_type,
    )
    db.add(db_meeting)
    await db.commit()

    _finalize_action(action_id)
    return {"success": True, "resource_id": str(meeting_id), "message": f"Meeting '{title}' scheduled successfully."}


async def _execute_send_whatsapp(payload: dict, current_user: User, db: AsyncSession, action_id: str) -> dict:
    """Deliver a confirmed WhatsApp message via the gateway."""
    from app.services.whatsapp_service import get_whatsapp_service

    chat_id = payload.get("chat_id") or payload.get("to") or payload.get("group")
    message = payload.get("message", "")
    if not chat_id or not message:
        raise HTTPException(status_code=400, detail="chat_id and message are required")

    result = await get_whatsapp_service().send_text(chat_id, message)
    _finalize_action(action_id)

    if result.get("status") == "error":
        return {"success": False, "message": f"WhatsApp send failed: {result.get('error')}", "data": result}
    if result.get("status") == "simulated":
        return {"success": True, "message": "WhatsApp is disabled — message simulated, not delivered.", "data": result}
    return {"success": True, "message": "WhatsApp message sent.", "data": result}


async def _execute_create_action_item(payload: dict, current_user: User, db: AsyncSession, action_id: str) -> dict:
    """Create an action item directly via SQLAlchemy, matching the pattern used in the meetings route."""
    import datetime as _dt
    from app.models.models import ActionItem as _ActionItem, ActionItemStatus as _ActionItemStatus, ActionItemPriority as _ActionItemPriority

    twg_id_raw = payload.get("twg_id")
    # If no twg_id but a project_id was supplied (the new pipeline tool), derive
    # twg_id from the project so action items can be attached to a project.
    if not twg_id_raw:
        project_id_raw = payload.get("project_id")
        if project_id_raw:
            from app.models.models import Project as _Project
            from sqlalchemy import select as __select
            proj = (await db.execute(__select(_Project).where(_Project.id == uuid.UUID(str(project_id_raw))))).scalar_one_or_none()
            if not proj:
                raise HTTPException(status_code=404, detail="Project not found")
            twg_id_raw = str(proj.twg_id)
    if not twg_id_raw:
        raise HTTPException(status_code=400, detail="twg_id or project_id is required to create an action item")

    twg_id = uuid.UUID(str(twg_id_raw))
    description = payload.get("title") or payload.get("description") or "Action Item"

    due_raw = payload.get("due_date")
    if due_raw and isinstance(due_raw, str):
        due_date = _dt.datetime.fromisoformat(due_raw.replace("Z", "+00:00")).replace(tzinfo=None)
    elif isinstance(due_raw, _dt.datetime):
        due_date = due_raw.replace(tzinfo=None)
    else:
        due_date = None

    priority_raw = str(payload.get("priority", "medium")).lower()
    try:
        priority = _ActionItemPriority(priority_raw)
    except ValueError:
        priority = _ActionItemPriority.MEDIUM

    owner_id_raw = payload.get("assignee_id") or payload.get("owner_id")
    owner_id = uuid.UUID(str(owner_id_raw)) if owner_id_raw else None

    item_id = uuid.uuid4()
    db_item = _ActionItem(
        id=item_id,
        twg_id=twg_id,
        description=description,
        owner_id=owner_id,
        due_date=due_date,
        priority=priority,
        status=_ActionItemStatus.PENDING,
    )
    db.add(db_item)
    await db.commit()

    _finalize_action(action_id)
    return {"success": True, "resource_id": str(item_id), "message": f"Action item '{description}' created."}


# Project Memo Email Endpoint

from pydantic import BaseModel, EmailStr

class SendMemoEmailRequest(BaseModel):
    to_email: EmailStr
    subject: str
    body: str
    memo_content: str
    project_id: str
    project_name: str


@router.post("/supervisor/send-email")
async def send_project_memo_email(
    request: SendMemoEmailRequest,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Send a project investment memo via email using the supervisor agent's email tool.

    Args:
        request: Email request with memo content
        current_user: Current authenticated user

    Returns:
        Success status and message
    """
    try:
        logger.info(f"Using supervisor agent to send project memo email to {request.to_email}")

        # Import the send_email tool function
        from app.tools.email_tools import send_email

        # Format the email body with the memo content
        full_body = f"{request.body}\n\n{'='*80}\n\n{request.memo_content}"

        # Create HTML version
        html_body = f"""
        <html>
            <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
                <p>{request.body}</p>
                <hr style="border: 1px solid #ccc; margin: 20px 0;">
                <pre style="background-color: #f5f5f5; padding: 20px; border-radius: 5px; overflow-x: auto; white-space: pre-wrap;">
{request.memo_content}
                </pre>
                <hr style="border: 1px solid #ccc; margin: 20px 0;">
                <p style="font-size: 12px; color: #666;">
                    <em>This email was generated and sent by the ECOWAS TWG AI Agent System</em>
                </p>
            </body>
        </html>
        """

        # Use the supervisor agent's email tool to send the email
        result = await send_email(
            to=request.to_email,
            subject=request.subject,
            message=full_body,
            html_body=html_body,
            context=f"Sending investment memo for project {request.project_name} ({request.project_id})"
        )

        logger.info(f"Email tool result: {result}")

        # Check if it created an approval request or sent directly
        if result.get('status') == 'approval_required':
            approval_id = result.get('approval_request_id')
            logger.info(f"Email approval request created: {approval_id}")

            # Auto-approve for this endpoint since user already initiated the send
            approval_service = get_email_approval_service()
            approval_request = approval_service.get_approval_request(approval_id)

            if approval_request:
                # Send the email directly
                resend_service = get_resend_service()
                send_result = resend_service.send_message(
                    to=approval_request.draft.to,
                    subject=approval_request.draft.subject,
                    body=approval_request.draft.body,
                    html_body=approval_request.draft.html_body
                )

                # Remove the approval request
                approval_service.remove_approval_request(approval_id)

                logger.info(f"Project memo email sent successfully to {request.to_email}")

                # Audit Log
                await audit_service.log_activity(
                    db=db,
                    user_id=current_user.id,
                    action="send_project_memo_email",
                    resource_type="email",
                    resource_id=None,
                    details={
                        "to": [request.to_email],
                        "subject": request.subject,
                        "project_id": request.project_id,
                        "project_name": request.project_name
                    }
                )
                await db.commit()

                return {
                    "success": True,
                    "message": f"Investment memo sent successfully to {request.to_email}",
                    "email_sent": True,
                    "message_id": send_result.get('message_id'),
                    "thread_id": None
                }

        # Fallback response
        return {
            "success": True,
            "message": f"Email sent successfully to {request.to_email}",
            "email_sent": True,
            "result": result
        }

    except Exception as e:
        logger.error(f"Failed to send project memo email: {str(e)}")
        import traceback
        traceback.print_exc()

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to send email: {str(e)}"
        )


# ---------------------------------------------------------------------------
# Pipeline-write execution helpers (confirm-then-execute via /agents/execute)
# ---------------------------------------------------------------------------

from sqlalchemy import select as _select
from app.models.models import (
    AgentAuditLog as _AgentAuditLog,
    ActionItem as _ActionItemModel,
    ActionItemStatus as _ActionItemStatusModel,
    ActionItemPriority as _ActionItemPriorityModel,
    Project as _Project,
    ProjectStatus as _ProjectStatus,
    ProjectStatusHistory as _ProjectStatusHistory,
)


async def _audit(
    db: AsyncSession,
    *,
    user: User,
    action_id: str,
    tool_name: str,
    target_id,
    before,
    after,
    summary: str,
) -> None:
    """Append a single AgentAuditLog row in the caller's transaction."""
    role_value = user.role.value if hasattr(user.role, "value") else str(user.role)
    db.add(_AgentAuditLog(
        user_id=user.id,
        user_role=role_value,
        action_id=action_id,
        tool_name=tool_name,
        target_type="project",
        target_id=str(target_id) if target_id else None,
        before_json=before,
        after_json=after,
        summary=summary,
    ))


async def _execute_advance_project_stage(
    payload: dict, current_user: User, db: AsyncSession, action_id: str
) -> dict:
    pid = uuid.UUID(str(payload["project_id"]))
    target = _ProjectStatus(payload["target_stage"])
    row = (await db.execute(_select(_Project).where(_Project.id == pid))).scalar_one_or_none()
    if not row:
        raise HTTPException(status_code=404, detail="Project not found")
    before_stage = row.status if row.status else None
    before_value = before_stage.value if before_stage else None
    row.status = target
    db.add(_ProjectStatusHistory(
        project_id=pid,
        previous_status=before_stage,
        new_status=target,
        changed_by_id=current_user.id,
        notes=payload.get("notes") or "",
    ))
    await _audit(
        db, user=current_user, action_id=action_id, tool_name="advance_project_stage",
        target_id=pid, before={"status": before_value}, after={"status": target.value},
        summary=f"advance {before_value} -> {target.value}",
    )
    await db.commit()
    _finalize_action(action_id)
    return {"success": True, "resource_id": str(pid), "stage": target.value,
            "message": f"Project advanced to {target.value}."}


async def _execute_decline_project(
    payload: dict, current_user: User, db: AsyncSession, action_id: str
) -> dict:
    pid = uuid.UUID(str(payload["project_id"]))
    reason = (payload.get("reason") or "").strip()
    row = (await db.execute(_select(_Project).where(_Project.id == pid))).scalar_one_or_none()
    if not row:
        raise HTTPException(status_code=404, detail="Project not found")
    before_stage = row.status if row.status else None
    before_value = before_stage.value if before_stage else None
    row.status = _ProjectStatus.DECLINED
    db.add(_ProjectStatusHistory(
        project_id=pid,
        previous_status=before_stage,
        new_status=_ProjectStatus.DECLINED,
        changed_by_id=current_user.id,
        reason=reason,
        notes=reason,
    ))
    await _audit(
        db, user=current_user, action_id=action_id, tool_name="decline_project",
        target_id=pid, before={"status": before_value}, after={"status": "DECLINED"},
        summary=f"declined: {reason[:140]}",
    )
    await db.commit()
    _finalize_action(action_id)
    return {"success": True, "resource_id": str(pid), "message": "Project declined."}


async def _execute_mark_flagship(
    payload: dict, current_user: User, db: AsyncSession, action_id: str
) -> dict:
    pid = uuid.UUID(str(payload["project_id"]))
    row = (await db.execute(_select(_Project).where(_Project.id == pid))).scalar_one_or_none()
    if not row:
        raise HTTPException(status_code=404, detail="Project not found")
    before = bool(getattr(row, "is_flagship", False))
    row.is_flagship = bool(payload["is_flagship"])
    await _audit(
        db, user=current_user, action_id=action_id, tool_name="mark_flagship",
        target_id=pid, before={"is_flagship": before}, after={"is_flagship": row.is_flagship},
        summary=f"flagship {before} -> {row.is_flagship}",
    )
    await db.commit()
    _finalize_action(action_id)
    return {"success": True, "resource_id": str(pid), "is_flagship": row.is_flagship,
            "message": f"Project {'marked' if row.is_flagship else 'unmarked'} as flagship."}


async def _execute_rescore_project(
    payload: dict, current_user: User, db: AsyncSession, action_id: str
) -> dict:
    from app.services.project_pipeline_service import ProjectPipelineService
    pid = uuid.UUID(str(payload["project_id"]))
    service = ProjectPipelineService(db)
    # assess_project_readiness is the in-process WAIIS scoring path; it persists
    # afcen_score / readiness_score / strategic_alignment_score onto the Project row.
    afcen = await service.assess_project_readiness(pid)
    afcen_float = float(afcen) if afcen is not None else None
    await _audit(
        db, user=current_user, action_id=action_id, tool_name="rescore_project",
        target_id=pid, before=None, after={"afcen_score": afcen_float},
        summary=f"rescored -> {afcen_float}",
    )
    await db.commit()
    _finalize_action(action_id)
    return {"success": True, "resource_id": str(pid), "afcen_score": afcen_float,
            "message": f"Project rescored: AfCEN {afcen_float}."}


async def _execute_graduate_from_incubation(
    payload: dict, current_user: User, db: AsyncSession, action_id: str
) -> dict:
    pid = uuid.UUID(str(payload["project_id"]))
    row = (await db.execute(_select(_Project).where(_Project.id == pid))).scalar_one_or_none()
    if not row or row.status != _ProjectStatus.INCUBATION:
        raise HTTPException(status_code=409, detail="Project is not in Incubation")
    row.status = _ProjectStatus.DRAFT
    db.add(_ProjectStatusHistory(
        project_id=pid,
        previous_status=_ProjectStatus.INCUBATION,
        new_status=_ProjectStatus.DRAFT,
        changed_by_id=current_user.id,
        notes="Graduated from Incubation via Martin.",
    ))
    await _audit(
        db, user=current_user, action_id=action_id, tool_name="graduate_from_incubation",
        target_id=pid, before={"status": "INCUBATION"}, after={"status": "DRAFT"},
        summary="incubation -> draft",
    )
    await db.commit()
    _finalize_action(action_id)
    return {"success": True, "resource_id": str(pid),
            "message": "Project graduated from Incubation."}


async def _execute_bulk_create_action_items(
    payload: dict, current_user: User, db: AsyncSession, action_id: str
) -> dict:
    import datetime as _dt
    meeting_id_raw = payload.get("meeting_id")
    if not meeting_id_raw:
        raise HTTPException(status_code=400, detail="meeting_id is required")
    meeting_id = uuid.UUID(str(meeting_id_raw))

    # Look up the meeting's twg_id since ActionItem.twg_id is NOT NULL.
    from app.models.models import Meeting as _Meeting
    meeting_row = (await db.execute(
        _select(_Meeting).where(_Meeting.id == meeting_id)
    )).scalar_one_or_none()
    if not meeting_row:
        raise HTTPException(status_code=404, detail="Meeting not found")
    twg_id = meeting_row.twg_id

    created_ids: list[str] = []
    for it in payload.get("items", []):
        description = (it.get("description") or "").strip()
        if not description:
            continue

        due_raw = it.get("due_date")
        if due_raw and isinstance(due_raw, str):
            try:
                due_date = _dt.datetime.fromisoformat(due_raw.replace("Z", "+00:00")).replace(tzinfo=None)
            except ValueError:
                due_date = None
        elif isinstance(due_raw, _dt.datetime):
            due_date = due_raw.replace(tzinfo=None)
        else:
            due_date = None

        priority_raw = str(it.get("priority", "medium")).lower()
        try:
            priority = _ActionItemPriorityModel(priority_raw)
        except ValueError:
            priority = _ActionItemPriorityModel.MEDIUM

        owner_id_raw = it.get("owner_user_id") or it.get("owner_id") or it.get("assignee_id")
        owner_id = uuid.UUID(str(owner_id_raw)) if owner_id_raw else None

        item_id = uuid.uuid4()
        db.add(_ActionItemModel(
            id=item_id,
            twg_id=twg_id,
            meeting_id=meeting_id,
            description=description,
            owner_id=owner_id,
            due_date=due_date,
            priority=priority,
            status=_ActionItemStatusModel.PENDING,
        ))
        created_ids.append(str(item_id))

    await db.flush()
    await _audit(
        db, user=current_user, action_id=action_id, tool_name="bulk_create_action_items",
        target_id=meeting_id, before=None, after={"count": len(created_ids)},
        summary=f"created {len(created_ids)} action items",
    )
    await db.commit()
    _finalize_action(action_id)
    return {"success": True, "count": len(created_ids), "ids": created_ids,
            "message": f"Created {len(created_ids)} action item(s)."}
