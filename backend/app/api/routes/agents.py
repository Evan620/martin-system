from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from typing import List, AsyncGenerator
import uuid
import asyncio
import json

from backend.app.api.deps import get_current_active_user
from backend.app.models.models import User
from backend.app.schemas.schemas import AgentChatRequest, AgentChatResponse, AgentTaskRequest, AgentStatus
from backend.app.schemas.chat_messages import (
    EnhancedChatRequest,
    EnhancedChatResponse,
    ChatMessage,
    ChatMessageType,
    AgentSuggestion,
    ToolExecution
)
from backend.app.agents.supervisor_with_tools import SupervisorWithTools
from backend.app.services.command_parser import CommandParser, MessageParseType
from backend.app.services.email_approval_service import get_email_approval_service
from backend.app.services.gmail_service import get_gmail_service
from backend.app.schemas.email_approval import (
    EmailApprovalRequest,
    EmailApprovalResponse,
    EmailApprovalResult
)
from datetime import datetime

router = APIRouter(prefix="/agents", tags=["Agents"])

# Initialize the supervisor agent (singleton)
supervisor_agent = None
command_parser = CommandParser()

def get_supervisor() -> SupervisorWithTools:
    """Get or create the supervisor agent instance."""
    global supervisor_agent
    if supervisor_agent is None:
        supervisor_agent = SupervisorWithTools()
    return supervisor_agent


# Command and Mention Handlers (Phase 2)

async def handle_command(supervisor: SupervisorWithTools, parsed: dict, original_message: str) -> str:
    """Handle slash command execution."""
    command = parsed["command"]
    params = parsed["parameters"]
    clean_query = parsed["clean_query"]

    # Map commands to supervisor methods
    if command == "/search":
        query = params.get("query", clean_query)
        return await supervisor.chat_with_tools(f"Search the knowledge base for: {query}")

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
                (f" and CC {cc}" if cc else "")
            )
        else:
            # Search emails
            search_term = params.get("search", clean_query)
            return await supervisor.chat_with_tools(f"Search my emails for: {search_term}")

    elif command == "/schedule":
        return await supervisor.chat_with_tools(f"Help me with scheduling: {clean_query}")

    elif command == "/draft":
        doc_type = params.get("type", "document")
        topic = params.get("topic", clean_query)
        return await supervisor.chat_with_tools(f"Draft a {doc_type} about: {topic}")

    elif command == "/analyze":
        target = params.get("target", clean_query)
        return await supervisor.chat_with_tools(f"Analyze: {target}")

    elif command == "/broadcast":
        message = params.get("message", clean_query)
        return await supervisor.chat_with_tools(f"Broadcast this message to all TWGs: {message}")

    elif command == "/summarize":
        target = params.get("target", clean_query)
        return await supervisor.chat_with_tools(f"Summarize: {target}")

    else:
        return f"Command {command} recognized but handler not implemented yet. Query: {clean_query}"


async def handle_mention(supervisor: SupervisorWithTools, parsed: dict) -> str:
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
            f"[ROUTING TO {agent_id.upper()} TWG AGENT] {clean_query}"
        )
    else:
        return await supervisor.chat_with_tools(
            f"[ROUTING TO MULTIPLE AGENTS: {', '.join(agent_ids)}] {clean_query}"
        )


@router.post("/chat", response_model=AgentChatResponse)
async def chat_with_martin(
    chat_in: AgentChatRequest,
    current_user: User = Depends(get_current_active_user)
):
    """
    Chat with the Supervisor AI agent.

    Uses the actual LLM-powered supervisor with tool execution capabilities.
    """
    conv_id = chat_in.conversation_id or uuid.uuid4()

    try:
        # Get the supervisor agent
        supervisor = get_supervisor()

        # Chat with the supervisor using tools
        response_text = await supervisor.chat_with_tools(chat_in.message)

        return {
            "response": response_text,
            "conversation_id": conv_id,
            "citations": [],  # Citations will be extracted from the response in future
            "agent_id": "supervisor_v1"
        }
    except Exception as e:
        # Log the error and return a helpful message
        import traceback
        traceback.print_exc()

        return {
            "response": f"I apologize, but I encountered an error processing your request: {str(e)}",
            "conversation_id": conv_id,
            "citations": [],
            "agent_id": "supervisor_v1"
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
    conv_id = chat_in.conversation_id or uuid.uuid4()

    try:
        # Get the supervisor agent
        supervisor = get_supervisor()

        # Parse message for commands and mentions (Phase 2)
        parsed = command_parser.parse_message(chat_in.message)

        # Handle based on parse type
        if parsed["type"] == MessageParseType.COMMAND:
            # Command execution
            response_text = await handle_command(supervisor, parsed, chat_in.message)
            message_type = ChatMessageType.COMMAND_RESULT
        elif parsed["type"] == MessageParseType.MENTION:
            # Route to specific agent(s)
            response_text = await handle_mention(supervisor, parsed)
            message_type = ChatMessageType.AGENT_TEXT
        elif parsed["type"] == MessageParseType.MIXED:
            # Both command and mention - prioritize command
            response_text = await handle_command(supervisor, parsed, chat_in.message)
            message_type = ChatMessageType.COMMAND_RESULT
        else:
            # Natural language - regular chat
            response_text = await supervisor.chat_with_tools(chat_in.message)
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


@router.post("/chat/stream")
async def stream_chat(
    chat_in: EnhancedChatRequest,
    current_user: User = Depends(get_current_active_user)
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
        conv_id = chat_in.conversation_id or str(uuid.uuid4())

        try:
            # Send initial event
            yield f"data: {json.dumps({'type': 'start', 'conversation_id': conv_id})}\n\n"

            # Get the supervisor agent
            supervisor = get_supervisor()

            # Parse message for commands and mentions
            parsed = command_parser.parse_message(chat_in.message)

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
                response_text = await handle_command(supervisor, parsed, chat_in.message)
                message_type = ChatMessageType.COMMAND_RESULT

            elif parsed["type"] == MessageParseType.MENTION:
                # Send agent routing event
                agent_ids = parsed["agent_mentions"]
                status_msg = f"Routing to {', '.join(agent_ids)} agent(s)..."
                yield f"data: {json.dumps({'type': 'agent_routing', 'agents': agent_ids, 'status': status_msg})}\n\n"

                # Execute with mentioned agent
                response_text = await handle_mention(supervisor, parsed)
                message_type = ChatMessageType.AGENT_TEXT

            elif parsed["type"] == MessageParseType.MIXED:
                yield f"data: {json.dumps({'type': 'mixed_execution', 'status': 'Processing command with agent mention...'})}\n\n"
                response_text = await handle_command(supervisor, parsed, chat_in.message)
                message_type = ChatMessageType.COMMAND_RESULT

            else:
                # Natural language - show thinking
                yield f"data: {json.dumps({'type': 'thinking', 'status': 'Processing your request...'})}\n\n"

                # Simulate LLM thinking
                await asyncio.sleep(0.5)
                yield f"data: {json.dumps({'type': 'thinking', 'status': 'Analyzing context...'})}\n\n"

                # Execute
                response_text = await supervisor.chat_with_tools(chat_in.message)
                message_type = ChatMessageType.AGENT_TEXT

            # Send completion event
            yield f"data: {json.dumps({'type': 'tool_complete', 'status': 'Completed'})}\n\n"

            # Create the final message
            agent_message = ChatMessage(
                message_id=uuid.uuid4(),
                conversation_id=conv_id,
                message_type=message_type,
                content=response_text,
                sender="agent",
                timestamp=datetime.utcnow(),
                metadata={"parsed": parsed} if parsed["type"] != MessageParseType.NATURAL else None
            )

            # Send final response
            yield f"data: {json.dumps({'type': 'response', 'message': agent_message.dict()})}\n\n"

            # Send done event
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


@router.post("/task", status_code=status.HTTP_202_ACCEPTED)
async def assign_agent_task(
    task_in: AgentTaskRequest,
    current_user: User = Depends(get_current_active_user)
):
    """
    Assign a high-level task to the agent swarm (e.g., draft Communiqué).
    
    Returns a task ID for polling. (Currently Mocked)
    """
    task_id = uuid.uuid4()
    # In production, this would trigger a Celery task or a background agent flow
    return {
        "task_id": str(task_id),
        "status": "queued",
        "message": f"Task '{task_in.title}' has been dispatched to the agent swarm."
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
    current_user: User = Depends(get_current_active_user)
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
        # Send the email using Gmail service
        gmail_service = get_gmail_service()
        result = gmail_service.send_message(
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

        return EmailApprovalResult(
            success=True,
            message="Email sent successfully",
            email_sent=True,
            message_id=result.get('message_id'),
            thread_id=result.get('thread_id')
        )

    except Exception as e:
        import traceback
        traceback.print_exc()

        return EmailApprovalResult(
            success=False,
            message=f"Failed to send email: {str(e)}",
            email_sent=False
        )


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
    current_user: User = Depends(get_current_active_user)
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
        from backend.app.tools.email_tools import send_email

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
                gmail_service = get_gmail_service()
                send_result = gmail_service.send_message(
                    to=approval_request.draft.to,
                    subject=approval_request.draft.subject,
                    body=approval_request.draft.body,
                    html_body=approval_request.draft.html_body
                )

                # Remove the approval request
                approval_service.remove_approval_request(approval_id)

                logger.info(f"Project memo email sent successfully to {request.to_email}")

                return {
                    "success": True,
                    "message": f"Investment memo sent successfully to {request.to_email}",
                    "email_sent": True,
                    "message_id": send_result.get('message_id'),
                    "thread_id": send_result.get('thread_id')
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
