from fastapi import APIRouter, Depends, HTTPException, status
from typing import List
import uuid
import asyncio

from backend.app.api.deps import get_current_active_user
from backend.app.models.models import User
from backend.app.schemas.schemas import AgentChatRequest, AgentChatResponse, AgentTaskRequest, AgentStatus
from backend.app.agents.supervisor_with_tools import SupervisorWithTools

router = APIRouter(prefix="/agents", tags=["Agents"])

# Initialize the supervisor agent (singleton)
supervisor_agent = None

def get_supervisor() -> SupervisorWithTools:
    """Get or create the supervisor agent instance."""
    global supervisor_agent
    if supervisor_agent is None:
        supervisor_agent = SupervisorWithTools()
    return supervisor_agent

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
