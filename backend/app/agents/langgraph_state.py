"""
LangGraph State Schema for Multi-Agent System

Defines the shared state that flows through the agent graph.
"""

from typing import Annotated, TypedDict, List, Dict, Optional, Literal, Sequence
from operator import add
from langchain_core.messages import BaseMessage


# Helper function for message accumulation
def add_messages(left: Sequence[BaseMessage], right: Sequence[BaseMessage]) -> Sequence[BaseMessage]:
    """Add messages together for state accumulation."""
    return list(left) + list(right)


class AgentState(TypedDict):
    """
    Shared state for the multi-agent system.

    This state is passed between nodes in the graph and accumulates
    information as agents process queries.
    """
    # Messages - using LangGraph's built-in message handling
    messages: Annotated[List[BaseMessage], add_messages]

    # Query routing information
    query: str
    relevant_agents: List[str]  # Which TWG agents should handle this

    # Agent responses
    agent_responses: Dict[str, str]  # agent_id -> response

    # Synthesis and final output
    synthesized_response: Optional[str]
    final_response: str

    # Metadata
    requires_synthesis: bool  # True if multiple agents consulted
    delegation_type: Literal["single", "multiple", "supervisor_only"]

    # Session information
    session_id: Optional[str]
    user_id: Optional[str]

    # Context and history (optional)
    context: Optional[Dict[str, any]]
    
    # Structured Intent from LLM Parser
    directive_intent: Optional[Dict[str, any]]
    
    # User's timezone (e.g. "Africa/Lagos")
    user_timezone: Optional[str]

    # Structured Citations for frontend
    citations: Annotated[List[Dict], add]
