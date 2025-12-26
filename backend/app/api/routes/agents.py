from fastapi import APIRouter, Depends, HTTPException, status
from typing import List
import uuid
import asyncio

from backend.app.api.deps import get_current_active_user
from backend.app.models.models import User
from backend.app.schemas.schemas import AgentChatRequest, AgentChatResponse, AgentTaskRequest, AgentStatus

router = APIRouter(prefix="/agents", tags=["Agents"])

@router.post("/chat", response_model=AgentChatResponse)
async def chat_with_martin(
    chat_in: AgentChatRequest,
    current_user: User = Depends(get_current_active_user)
):
    """
    Chat with the specialized 'Martin' agent for your TWG.
    
    (Currently Mocked - Will be replaced by Supervisor logic)
    """
    # Simulate AI processing time
    await asyncio.sleep(1.5)
    
    conv_id = chat_in.conversation_id or uuid.uuid4()
    
    # Placeholder response
    response_text = (
        f"Greetings {current_user.full_name}. I am analyzing your request regarding '{chat_in.message}'. "
        "As the Technical Advisor for this summit, I am cross-referencing this with the current knowledge base. "
        "How else can I assist with your TWG objectives today?"
    )
    
    return {
        "response": response_text,
        "conversation_id": conv_id,
        "citations": [
            {"source": "Abuja Declaration Draft.pdf", "page": 4, "relevance": 0.95},
            {"source": "ECOWAS Energy Policy 2024.docx", "page": 12, "relevance": 0.88}
        ],
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
