"""
Critic Node for Iterative Refinement

Implements the Critic Pattern to analyze tool execution failures and provide 
constructive feedback or corrected schemas back to the agent, rather than 
crashing out or returning opaque errors to the user.
"""

from typing import Dict, Any, Optional
from loguru import logger
from langchain_core.messages import HumanMessage, AIMessage, BaseMessage

from app.services.llm_service import get_llm_service
from app.agents.langgraph_state import AgentState

def critic_analyze_error(
    failed_tool_name: str,
    failed_args: Dict[str, Any],
    error_message: str,
    original_intent: str
) -> str:
    """
    Analyze a tool failure and suggest a correction.
    
    Args:
        failed_tool_name: Name of the tool that failed
        failed_args: Arguments passed to the tool
        error_message: The raw error message returned by the tool or system
        original_intent: What the user was trying to achieve
        
    Returns:
        str: Constructive feedback for the agent to try again or gracefully degrade.
    """
    llm = get_llm_service()
    
    system_prompt = """
    You are the Agent Critic. An autonomous agent attempted to use a tool to solve a user's request, but it failed.
    
    Your job is to:
    1. Analyze the original intent.
    2. Look at the tool they tried to use and the arguments they provided.
    3. Look at the exact error message.
    4. Provide CONSTRUCTive feedback to the agent on how to fix their tool call, or if the tool is the wrong choice entirely.
    
    Rules:
    - Keep your feedback extremely brief and actionable.
    - If the error is a completely invalid tool (e.g. they hallucinated a tool), tell them strictly to use standard conversational response.
    - If it's a JSON/Schema error, tell them exactly which field to fix.
    - If it's an access denied error, tell them to inform the user they lack permissions.
    """
    
    prompt = f"""
    Original User Intent: {original_intent}
    
    Tool Attempted: {failed_tool_name}
    Arguments Provided: {failed_args}
    
    Error Encountered: {error_message}
    
    Give precisely worded, actionable feedback to the agent so it can successfully retry.
    """
    
    try:
        response = llm.chat(
            prompt=prompt,
            system_prompt=system_prompt,
            temperature=0.1,  # Low temp for analytical feedback
            max_tokens=250
        )
        # Handle string or AIMessage return
        return response if isinstance(response, str) else response.content
    except Exception as e:
        logger.error(f"[Critic] LLM analysis failed: {e}")
        return f"System generic feedback: Tool '{failed_tool_name}' failed with {error_message}. Please review your arguments and try again."

def extract_latest_tool_error(messages: list[BaseMessage]) -> Optional[Dict[str, Any]]:
    """
    Scan the recent message history for a failed Tool message.
    Returns a dict with tool details if an error is found, otherwise None.
    """
    # Look at the most recent messages (usually the last 1 or 2 are tool results)
    for msg in reversed(messages):
        if msg.type == "tool":
            content_str = str(msg.content).lower()
            if "error" in content_str or "access denied" in content_str or "validation" in content_str:
                return {
                    "tool_call_id": msg.tool_call_id,
                    "error": msg.content
                }
        elif msg.type == "human" or msg.type == "user":
            # Don't look past the current user turn
            break
            
    return None

async def critic_retry_node(state: dict) -> dict:
    """
    LangGraph node to handle the Critic pattern.
    Reads the error out of the state, calls the LLM, and injects feedback.
    """
    messages = state.get("messages", [])
    if not messages:
        return state
        
    # 1. Identify what failed
    error_info = extract_latest_tool_error(messages)
    if not error_info:
        logger.debug("[CriticNode] Invoked but no explicit tool error found in recent messages.")
        return state
        
    tool_error = error_info["error"]
    failed_tool_id = error_info["tool_call_id"]
    
    # 2. Extract context
    query = state.get("query", "Unknown query")
    failed_tool_name = "Unknown Tool"
    failed_args = {}
    
    # Find the assistant message that spawned this tool call
    for msg in reversed(messages):
        if msg.type == "ai" and hasattr(msg, "tool_calls") and msg.tool_calls:
            for tc in msg.tool_calls:
                if tc.get("id") == failed_tool_id:
                    failed_tool_name = tc.get("name", "Unknown")
                    failed_args = tc.get("args", {})
                    break
            
    logger.info(f"[CriticNode] Analyzing failure for tool '{failed_tool_name}': {tool_error}")
    
    # 3. Analyze
    feedback = critic_analyze_error(
        failed_tool_name=failed_tool_name,
        failed_args=failed_args,
        error_message=tool_error,
        original_intent=query
    )
    
    logger.info(f"[CriticNode] Generated feedback: {feedback}")
    
    # 4. Inject feedback into state
    # We add a SystemMessage directing the agent to retry using the feedback
    from langchain_core.messages import SystemMessage
    
    retry_instruction = SystemMessage(
        content=f"[CRITIC FEEDBACK] Your previous tool call failed. Feedback: {feedback}\nPlease carefully incorporate this feedback and try your tool call again. Do not simply repeat the exact same call."
    )
    
    state["messages"].append(retry_instruction)
    
    return state
