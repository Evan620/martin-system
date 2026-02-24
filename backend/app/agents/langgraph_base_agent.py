"""
LangGraph Base Agent - PROPER IMPLEMENTATION

All agents (TWG agents and Supervisor) should inherit from this.
Uses LangGraph StateGraph for proper agent orchestration.
"""

from typing import Annotated, TypedDict, List, Dict, Optional, Sequence, cast, Any
from loguru import logger
from operator import add
import json

from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver
from langgraph.types import interrupt, Command
from langgraph.errors import GraphInterrupt, GraphRecursionError
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage

from app.services.llm_service import get_llm_service
from app.agents.prompts import get_prompt
from app.core.knowledge_base import get_knowledge_base
from app.agents.utils import get_twg_id_by_agent_id


# Helper function for message accumulation
def add_messages(left: Sequence[BaseMessage], right: Sequence[BaseMessage]) -> Sequence[BaseMessage]:
    """Add messages together for state accumulation."""
    return list(left) + list(right)


# =========================================================================
# STATE SCHEMA FOR INDIVIDUAL AGENTS
# =========================================================================

class AgentConversationState(TypedDict):
    """
    State schema for individual agent conversations.

    Each agent maintains its own conversation state using LangGraph.
    """
    # Messages using custom message handling
    messages: Annotated[Sequence[BaseMessage], add_messages]

    # Current query
    query: str

    # Response
    response: str

    # Agent metadata
    agent_id: str
    session_id: str

    # Context (optional)
    context: Optional[Dict]
    
    # State tracking for Tiered Memory summarization
    summarized_index: int
    
    # Store structured citations for frontend
    citations: Annotated[List[Dict], add]
    
    # Flag to indicate an approval is pending (stops agent loop)
    approval_pending: Optional[bool]
    
    # User's Timezone (e.g., "Africa/Lagos")
    user_timezone: Optional[str]
    
    # Tool-round counter to prevent infinite tool-calling loops
    tool_rounds: int


# =========================================================================
# LANGGRAPH BASE AGENT CLASS
# =========================================================================

class LangGraphBaseAgent:
    """
    Base class for ALL agents using LangGraph StateGraph.

    This replaces the old BaseAgent with proper LangGraph orchestration.
    Every TWG agent and the Supervisor should use this.
    """

    def __init__(
        self,
        agent_id: str,
        keep_history: bool = True,
        max_history: int = 10,
        session_id: Optional[str] = None,
        use_redis: bool = False,
        memory_ttl: Optional[int] = None
    ):
        """
        Initialize a LangGraph-based agent.

        Args:
            agent_id: Unique identifier
            keep_history: Whether to maintain conversation history
            max_history: Maximum messages to keep
            session_id: Session identifier for checkpointing
            use_redis: If True, use Redis checkpointer (future)
            memory_ttl: TTL for memory (optional)
        """
        self.agent_id = agent_id
        self.keep_history = keep_history
        self.max_history = max_history
        self.session_id = session_id or "default"
        self.use_redis = use_redis
        self.memory_ttl = memory_ttl

        # Load system prompt
        try:
            base_prompt = get_prompt(agent_id)
            logger.info(f"[{agent_id}] Loaded system prompt")
        except ValueError as e:
            logger.error(f"[{agent_id}] Failed to load prompt: {e}")
            raise

        # Get LLM service
        self.llm = get_llm_service()
        
        # Tools Configuration — Zero-Trust Tool Registry
        from app.tools.tool_registry import get_tool_registry
        import json
        
        self._tool_registry = get_tool_registry()
        self.tools_def, self.tool_map = self._tool_registry.get_tools_for_agent(
            agent_id=agent_id,
            twg_id=get_twg_id_by_agent_id(agent_id),
        )
        
        # Initialize Tiered Memory Manager
        from app.services.memory_manager import get_memory_manager
        self.memory_manager = get_memory_manager()
        
        # Get Knowledge Base (RAG)
        try:
            self.kb = get_knowledge_base()
        except Exception as e:
            logger.warning(f"[{agent_id}] Knowledge Base not available: {e}")
            self.kb = None
            
        # Resolve TWG ID for RAG context scoping
        self.twg_id = get_twg_id_by_agent_id(agent_id)
        if self.twg_id:
            logger.info(f"[{agent_id}] RAG Enabled. Scoped to TWG: {self.twg_id}")
            
            # Inject TWG ID into system prompt for explicit context awareness
            self.system_prompt = base_prompt + """

---
YOUR TWG CONTEXT:
- You have access ONLY to your TWG's data (meetings, documents, projects)
- You represent a specific Technical Working Group within the ECOWAS Summit

CRITICAL TOOL USAGE RULES:
1. When calling get_schedule or get_past_meetings, you do NOT need to pass twg_id - it will be automatically injected
2. When users ask about "upcoming meetings" or "my meetings", they mean YOUR TWG's meetings
3. You cannot see other TWGs' meetings - only the Supervisor can see cross-TWG data
4. If asked about another TWG's schedule, politely explain you only have access to your own TWG's data
5. NEVER expose raw TWG IDs (UUIDs) to users - always use human-readable TWG names
"""
        else:
            # Supervisor or non-TWG agent
            self.system_prompt = base_prompt


        # LangGraph components
        self.graph = None
        self.compiled_graph = None
        self.memory = MemorySaver()  # In-memory checkpointer

        # Build the agent's graph
        self._build_graph()

        logger.info(f"[{agent_id}] LangGraph agent initialized")

    def add_tool(self, tool_func):
        """
        Add a python function as a tool to the agent.
        Autogenerates the schema from the function signature and docstring.
        """
        import inspect
        
        func_name = tool_func.__name__
        doc = tool_func.__doc__ or "No description provided."
        
        # Simple schema generation
        sig = inspect.signature(tool_func)
        parameters = {}
        required = []
        
        for name, param in sig.parameters.items():
            param_type = "string"
            if param.annotation == int:
                param_type = "integer"
            elif param.annotation == bool:
                param_type = "boolean"
                
            parameters[name] = {
                "type": param_type,
                "description": f"Parameter {name}" 
            }
            if param.default == inspect.Parameter.empty:
                required.append(name)
        
        tool_def = {
            "type": "function",
            "function": {
                "name": func_name,
                "description": doc.strip(),
                "parameters": {
                    "type": "object",
                    "properties": parameters,
                    "required": required
                }
            }
        }
        
        self.tools_def.append(tool_def)
        self.tool_map[func_name] = tool_func
        logger.info(f"[{self.agent_id}] Added tool: {func_name}")

    def _build_graph(self) -> None:
        """
        Build the LangGraph StateGraph for this agent.
        Includes tool execution loop.
        """
        workflow = StateGraph(AgentConversationState)

        # Add nodes
        workflow.add_node("process_query", self._process_query_node)
        workflow.add_node("generate_response", self._generate_response_node)
        workflow.add_node("execute_tools", self._execute_tools_node)
        
        # Add Critic node
        from app.agents.critic_node import critic_retry_node
        workflow.add_node("critic_retry", critic_retry_node)

        # Set entry point
        workflow.set_entry_point("process_query")

        # Add edges
        workflow.add_edge("process_query", "generate_response")
        
        # Conditional edge: check if tokens were generated or tool calls
        workflow.add_conditional_edges(
            "generate_response",
            self._should_continue,
            {
                "continue": "execute_tools",
                "end": END
            }
        )
        
        # Conditional edge from execute_tools
        workflow.add_conditional_edges(
            "execute_tools",
            self._check_for_errors,
            {
                "critic": "critic_retry",
                "generate": "generate_response"
            }
        )
        
        # Always return directly to generation after critic feedback
        workflow.add_edge("critic_retry", "generate_response")

        # Compile with checkpointing
        self.graph = workflow
        self.compiled_graph = workflow.compile(checkpointer=self.memory)

        logger.info(f"[{self.agent_id}] StateGraph compiled with Tools loop and Critic recovery")

    def _check_for_errors(self, state: AgentConversationState) -> str:
        """
        Check if the last tool execution resulted in an error requiring critic intervention.
        """
        # If tool rounds maxed out, give up and force generation to finish
        if int(state.get("tool_rounds", 0) or 0) >= 5: # pyre-ignore[6]
            return "generate"
            
        from app.agents.critic_node import extract_latest_tool_error
        if extract_latest_tool_error(state["messages"]):
            logger.info(f"[{self.agent_id}] Tool error detected. Routing to Critic for analysis.")
            return "critic"
            
        return "generate"

    def _should_continue(self, state: AgentConversationState) -> str:
        """
        Determine if we should continue to tool execution or end.
        """
        # CRITICAL: If an approval is pending, STOP the loop immediately
        if state.get("approval_pending"):
            logger.info(f"[{self.agent_id}] Approval pending - ending loop")
            return "end"
        
        # SAFETY: Limit tool rounds to prevent infinite loops burning LLM tokens
        MAX_TOOL_ROUNDS = 5
        tool_rounds = int(state.get("tool_rounds", 0) or 0) # pyre-ignore[6]
        if tool_rounds >= MAX_TOOL_ROUNDS:
            logger.warning(f"[{self.agent_id}] Max tool rounds ({MAX_TOOL_ROUNDS}) reached. Forcing text response.")
            return "end"
        
        messages = state["messages"]
        last_message = messages[-1]
        
        if hasattr(last_message, "tool_calls") and last_message.tool_calls:
            return "continue"
            
        return "end"

    async def _process_query_node(self, state: AgentConversationState) -> AgentConversationState:
        """Process incoming query."""
        query = state["query"]
        
        # Initialize context and citations if needed
        if state.get("context") is None:
            state["context"] = {}
        if state.get("citations") is None:
            state["citations"] = []

        # RAG Retrieval
        if self.twg_id and self.kb:
            try:
                # Search KB restricted to TWG namespace
                namespace = f"twg-{self.twg_id}"
                # Use asyncio.to_thread if kb.search is blocking and slow
                # Assuming kb.search is synchronous for now
                import asyncio
                twg_results = await asyncio.to_thread(self.kb.search, 
                    query=query,
                    namespace=namespace,
                    top_k=3
                )
                
                # Search Global Broadcast namespace
                global_results = await asyncio.to_thread(self.kb.search,
                    query=query,
                    namespace="global",
                    top_k=2
                )
                
                # Merge and Sort by Score
                results = twg_results + global_results
                results.sort(key=lambda x: x['score'], reverse=True)
                results = results[:3] # Keep top 3 most relevant context pieces
                
                # Format context
                if results:
                    # Format context with EXTREME truncation to prevent token errors
                    # Limit to 500 chars per doc (~125 tokens) × 2 = 250 tokens total
                    context_parts = []
                    for r in results:
                        file_name = r['metadata'].get('file_name', 'Unknown')
                        text = r['metadata'].get('text', '') or ''
                        # Truncate text to 2000 chars (approx 500 tokens) to allow for more context while staying within limits
                        truncated_text = text[:2000] + "..." if len(text) > 2000 else text
                        context_parts.append(f"[{file_name}]\n{truncated_text}")

                    context_text = "\n".join(context_parts)

                    # Store in state
                    state['context'] = {"retrieved_docs": context_text, "source": namespace} # pyre-ignore[16]
                    
                    # Also populate structured citations
                    citations = []
                    for r in results:
                         citations.append({
                             "source": r['metadata'].get('file_name', 'Unknown'),
                             "page": r['metadata'].get('page', 1),
                             "relevance": r['score']
                         })
                    state['citations'] = citations # pyre-ignore[16]
                    
                    logger.info(f"[{self.agent_id}] Retrieved {len(results)} docs from {namespace}")
                else:
                    logger.info(f"[{self.agent_id}] No relevant docs found in {namespace}")
                    
            except Exception as e:
                logger.error(f"[{self.agent_id}] RAG Error: {e}")
                
        return state

    async def _generate_response_node(self, state: AgentConversationState) -> AgentConversationState:
        """
        Generate response using LLM, supporting Tool Calls.
        """
        query = state["query"]
        messages = cast(List[BaseMessage], state.get("messages", []))
        
        # 1. Tiered Memory: Track and trigger background summarization of old messages
        summarized_index = int(state.get("summarized_index", 0) or 0) # pyre-ignore[6]
        
        # If we have at least 5 messages that have fallen out of the sliding window, archive them
        if len(messages) - summarized_index > self.max_history + 5:
            messages_to_summarize = messages[summarized_index : len(messages) - self.max_history]
            
            # Fire and forget background summarization
            import asyncio
            asyncio.create_task(
                self.memory_manager.summarize_and_archive(
                    session_id=self.session_id,
                    agent_id=self.agent_id,
                    messages_to_summarize=messages_to_summarize
                )
            )
            # Advance the pointer
            state["summarized_index"] = len(messages) - self.max_history # pyre-ignore[16]

        # 2. Tiered Memory: Get sliding window + long term semantic context
        current_query = state.get("query", "")
        if not current_query and messages:
            current_query = str(messages[-1].content)
            
        history, long_term_summary = self.memory_manager.get_context(
            session_id=self.session_id,
            agent_id=self.agent_id,
            messages=messages,
            current_query=current_query,
            max_history=self.max_history
        )
        
        logger.info(f"[{self.agent_id}] Generating response using dynamic tiered memory window of {len(history)} messages...")

        try:
            # Prepare messages for LLM service (dict format)
            history: List[Dict[str, Any]] = []
            for msg in messages:
                if isinstance(msg, HumanMessage):
                    history.append({"role": "user", "content": msg.content})
                elif isinstance(msg, AIMessage):
                    msg_dict = {"role": "assistant", "content": msg.content}
                    if hasattr(msg, "tool_calls") and msg.tool_calls:
                         api_tool_calls = []
                         for tc in msg.tool_calls:
                             api_tool_calls.append({
                                 "id": tc["id"],
                                 "type": "function",
                                 "function": {
                                     "name": tc["name"],
                                     "arguments": json.dumps(tc["args"]) if isinstance(tc["args"], dict) else tc["args"]
                                 }
                             })
                         msg_dict["tool_calls"] = api_tool_calls
                    history.append(msg_dict)
                elif msg.type == "tool":
                    history.append({
                        "role": "tool",
                        "tool_call_id": msg.tool_call_id,
                        "content": msg.content
                    })

            # SANITIZATION: Ensure strict OpenAI compliance
            # Rule 1: Assistant with tool_calls MUST be followed by Tool messages
            # Rule 2: Tool messages MUST be preceded by an assistant message with matching tool_calls
            sanitized_history = []
            skip_indices = set()
            
            for i in range(len(history)):
                msg = history[i]
                
                # Check for dangling tool calls (assistant with tool_calls but no tool responses)
                if msg.get("role") == "assistant" and "tool_calls" in msg:
                    # Look ahead for matching tool outputs
                    tool_call_ids = {tc.get("id") for tc in msg.get("tool_calls", []) if isinstance(tc, dict)} # pyre-ignore[16, 29]
                    found_responses = set()
                    
                    # Scan subsequent messages for tool responses
                    j = i + 1
                    while j < len(history) and history[j].get("role") == "tool":
                        if history[j].get("tool_call_id") in tool_call_ids:
                             found_responses.add(history[j].get("tool_call_id"))
                        j += 1
                        
                    # If any tool call is missing a response, strip the tool_calls
                    if len(found_responses) < len(tool_call_ids):
                         logger.warning(f"[{self.agent_id}] Sanitizing history: Msg {i} has dangling tool calls. Stripping tools.")
                         msg.pop("tool_calls", None)
                         if not msg.get("content"):
                             msg["content"] = "[System: Previous tool call interrupted]"
                
                sanitized_history.append(msg)
            
            # PASS 2: Remove orphaned tool messages (tool messages without preceding assistant with tool_calls)
            # This happens after history truncation cuts off the assistant message but leaves tool responses
            final_history: List[Dict[str, Any]] = []
            active_tool_call_ids = set()
            
            for msg in sanitized_history:
                if msg.get("role") == "assistant" and "tool_calls" in msg:
                    # Track which tool_call_ids are active
                    active_tool_call_ids = {tc.get("id") for tc in msg.get("tool_calls", []) if isinstance(tc, dict)} # pyre-ignore[16, 29]
                    final_history.append(msg)
                elif msg.get("role") == "tool":
                    # Only include tool messages that have a matching preceding assistant tool_call
                    if msg.get("tool_call_id") in active_tool_call_ids:
                        final_history.append(msg)
                    else:
                        logger.warning(f"[{self.agent_id}] Sanitizing history: Removing orphaned tool message (tool_call_id: {msg.get('tool_call_id')})")
                else:
                    active_tool_call_ids = set()  # Reset on non-tool messages
                    final_history.append(msg)
            
            history = final_history

            # RAG Context injection (simplified)
            # RAG Context injection (simplified)
            from datetime import datetime, timezone as tz
            from zoneinfo import ZoneInfo
            from typing import Any
            
            # Use user's timezone if provided, otherwise default to Nairobi
            tz_var = state.get("user_timezone")
            tz_name = str(tz_var) if tz_var else "Africa/Nairobi"
            try:
                user_tz = ZoneInfo(tz_name)
            except Exception:
                logger.warning(f"Invalid timezone {tz_name}, falling back to Africa/Nairobi")
                user_tz = ZoneInfo("Africa/Nairobi")
                
            now = datetime.now(user_tz)
            current_time_str = now.strftime("%A, %B %d, %Y at %I:%M %p")
            today_date = now.strftime("%Y-%m-%d")
            
            sys_prompt = f"{self.system_prompt}\n\nCurrent Date & Time: {current_time_str} ({tz_name})\nToday's date is: {today_date}"
            
            if long_term_summary:
                sys_prompt = f"{sys_prompt}\n\n{long_term_summary}"
                
            context = state.get("context")
            if isinstance(context, dict) and "retrieved_docs" in context:
                sys_prompt = f"{sys_prompt}\n\nRelevant Context:\n{context['retrieved_docs']}"

            # Call LLM with tools
            # If self.llm.chat_with_history is SYNC, we wrap it.
            # Usually LLM calls are IO bound, so we use to_thread.
            import asyncio
            response_obj = await asyncio.to_thread(
                self.llm.chat_with_history,
                messages=history,
                system_prompt=sys_prompt,
                tools=self.tools_def
            )
            
            # DEBUG: Log the full system prompt to verify Timezone injection
            logger.info(f"[{self.agent_id}] System Prompt Context:\n{sys_prompt[-500:]}") # Log last 500 chars containing time context

            # Handle Response
            if hasattr(response_obj, "tool_calls") and response_obj.tool_calls:
                # LLM wants to call a tool
                logger.info(f"[{self.agent_id}] Tool Call detected: {len(response_obj.tool_calls)}")
                
                tool_calls_data = []
                for tc in response_obj.tool_calls:
                    # Trusting structured output guarantees from the LLM service
                    args_parsed = json.loads(tc.function.arguments)
                    
                    if not isinstance(args_parsed, dict):
                        args_parsed = {}
                        
                    tool_calls_data.append({
                        "name": tc.function.name,
                        "args": args_parsed,
                        "id": tc.id
                    })
                
                ai_msg = AIMessage(
                    content=str(response_obj.content or ""), 
                    tool_calls=tool_calls_data
                )
                state["response"] = "[Calling Tool...]" # pyre-ignore[16]
                cast(List[BaseMessage], state["messages"]).append(ai_msg) # pyre-ignore[16]
                
            else:
                # Standard text response
                content = response_obj if isinstance(response_obj, str) else response_obj.content
                
                # FALLBACK parsing removed for brevity/stability - relying on standard tool usage
                logger.info(f"[{self.agent_id}] Text Response generated")
                state["response"] = content # pyre-ignore[16]
                cast(List[BaseMessage], state["messages"]).append(AIMessage(content=content)) # pyre-ignore[16]

        except Exception as e:
            logger.error(f"[{self.agent_id}] Error in generation: {e}")
            state["response"] = f"Error: {str(e)}" # pyre-ignore[16]
            cast(List[BaseMessage], state["messages"]).append(AIMessage(content=state["response"])) # pyre-ignore[16]

        return state

    async def _execute_tools_node(self, state: AgentConversationState) -> AgentConversationState:
        """
        Execute tool calls requested by the LLM.
        
        Uses the Zero-Trust ToolRegistry for validated execution with
        automatic twg_id and user_timezone injection.
        """
        messages = cast(List[BaseMessage], state.get("messages", []))
        if not messages:
            return state
            
        last_message = messages[-1]
        
        if not hasattr(last_message, "tool_calls") or not last_message.tool_calls:
            return state
            
        from langchain_core.messages import ToolMessage
        from langgraph.errors import GraphInterrupt
        from app.tools.tool_registry import ToolAccessDenied
        import json
        
        new_messages = []
        user_timezone = state.get("user_timezone")
        
        for tool_call in last_message.tool_calls:
            tool_name = tool_call["name"]
            tool_args = tool_call["args"]
            tool_id = tool_call["id"]
            
            logger.info(f"[{self.agent_id}] Executing tool: {tool_name}")
            
            try:
                # Try Zero-Trust ToolRegistry first, fall back to local tool_map
                # (Supervisor state tools added via add_tool() live in tool_map only)
                if self._tool_registry and tool_name in self._tool_registry._tools:
                    output_str = await self._tool_registry.execute_tool(
                        tool_name=tool_name,
                        tool_args=tool_args,
                        agent_id=self.agent_id,
                        twg_id=self.twg_id,
                        user_timezone=user_timezone,
                    )
                elif tool_name in self.tool_map:
                    import asyncio, inspect
                    func = self.tool_map[tool_name]
                    # Auto-inject twg_id/user_timezone if the function accepts them
                    sig = inspect.signature(func)
                    if "twg_id" in sig.parameters and self.twg_id and "twg_id" not in tool_args:
                        tool_args["twg_id"] = self.twg_id
                    if "user_timezone" in sig.parameters and user_timezone and "user_timezone" not in tool_args:
                        tool_args["user_timezone"] = user_timezone
                    if asyncio.iscoroutinefunction(func):
                        raw_result = await func(**tool_args)
                    else:
                        raw_result = await asyncio.to_thread(func, **tool_args)
                    # Use json.dumps for dict/list so downstream json.loads() works
                    if isinstance(raw_result, (dict, list)):
                        output_str = json.dumps(raw_result, default=str)
                    else:
                        output_str = str(raw_result)
                else:
                    output_str = json.dumps({"error": f"Tool '{tool_name}' not found"})
                
                # SPECIAL HANDLING FOR APPROVAL REQUESTS
                if isinstance(output_str, str) and "approval_request_id" in output_str:
                    try:
                        res_json = json.loads(output_str) if isinstance(output_str, str) else output_str
                        if isinstance(res_json, dict) and "approval_request_id" in res_json:
                            logger.info(f"[{self.agent_id}] INTERRUPT: Approval required for {res_json['approval_request_id']}")
                            
                            approval_payload = {
                                "type": "email_approval_required",
                                "request_id": res_json.get("approval_request_id"),
                                "draft": res_json.get("draft", {}),
                                "message": res_json.get("message", "Email requires approval before sending.")
                            }
                            
                            # INTERRUPT the graph
                            human_response = interrupt(approval_payload)
                            
                            if human_response and human_response.get("approved"):
                                logger.info(f"[{self.agent_id}] Approval GRANTED - proceeding with send")
                                output_str = json.dumps({"status": "approved", "message": "Email approved and will be sent."})
                            else:
                                logger.info(f"[{self.agent_id}] Approval DENIED - cancelling send")
                        
                        elif isinstance(res_json, dict) and res_json.get("type") == "document_approval_required":
                             logger.info(f"[{self.agent_id}] INTERRUPT: Document Approval required for {res_json['approval_request_id']}")
                             
                             approval_payload = {
                                 "type": "document_approval_required",
                                 "request_id": res_json.get("approval_request_id"),
                                 "draft": res_json.get("document_draft", {}),
                                 "message": res_json.get("message", "Document requires approval before saving.")
                             }
                             
                             # INTERRUPT the graph
                             human_response = interrupt(approval_payload)
                             
                             if human_response and human_response.get("approved"):
                                 logger.info(f"[{self.agent_id}] Document Approval GRANTED - Saved.")
                                 saved_doc_id = human_response.get("result", {}).get("document_id", "unknown")
                                 output_str = json.dumps({"status": "approved", "message": f"Document approved and saved. ID: {saved_doc_id}"})
                             else:
                                 logger.info(f"[{self.agent_id}] Document Approval DENIED")
                                 output_str = json.dumps({"status": "denied", "message": "User declined to save the document."})
                    except GraphInterrupt:
                        logger.info(f"[{self.agent_id}] GraphInterrupt raised - pausing graph for approval")
                        raise
                    except json.JSONDecodeError:
                        pass
                    except Exception as e:
                        logger.error(f"[{self.agent_id}] Interrupt error: {e}")

                new_messages.append(ToolMessage(tool_call_id=tool_id, content=output_str))
            
            except ToolAccessDenied as tad:
                logger.warning(f"[{self.agent_id}] Access denied for tool '{tool_name}': {tad}")
                new_messages.append(ToolMessage(
                    tool_call_id=tool_id,
                    content=json.dumps({"error": f"Access denied: {str(tad)}"})
                ))
            except GraphInterrupt:
                raise
            except Exception as e:
                logger.error(f"[{self.agent_id}] Tool execution failed: {e}")
                new_messages.append(ToolMessage(tool_call_id=tool_id, content=f"Error: {str(e)}"))

        # Update state with all tool results
        cast(List[BaseMessage], state["messages"]).extend(new_messages) # pyre-ignore[16]
        
        # Increment tool-round counter
        state["tool_rounds"] = int(state.get("tool_rounds", 0) or 0) + 1 # pyre-ignore[6, 16]
        
        return state

    async def chat(self, message: str, thread_id: Optional[str] = None, user_timezone: Optional[str] = None) -> Dict[str, Any]:
        """
        Chat interface using LangGraph execution (Async).
        """
        graph = self.compiled_graph
        if not graph:
            raise ValueError(f"[{self.agent_id}] Graph not compiled")
            
        # ------------------------------------------------------------------
        # CONTEXT INJECTION (Supervisor Feedback Loop)
        # ------------------------------------------------------------------
        # Check for pending notifications for this TWG's Lead
        try:
            from app.core.database import get_db_session_context
            from app.models.models import TWG, Notification, NotificationType
            from sqlalchemy import select, and_
            
            twg_id_str = self.twg_id
            if twg_id_str:
                async with get_db_session_context() as db:
                     # Get Lead ID
                     stmt = select(TWG).where(TWG.id == twg_id_str)
                     res = await db.execute(stmt)
                     twg = res.scalar_one_or_none()
                     
                     if twg and twg.technical_lead_id:
                         # Fetch unread ALERT/TASK notifications
                         n_stmt = select(Notification).where(
                             and_(
                                 Notification.user_id == twg.technical_lead_id,
                                 Notification.is_read == False,
                                 Notification.type.in_([NotificationType.ALERT, NotificationType.TASK])
                             )
                         ).order_by(Notification.created_at.desc())
                         
                         n_res = await db.execute(n_stmt)
                         notifs = n_res.scalars().all()
                         
                         if notifs:
                             logger.info(f"[{self.agent_id}] Injecting {len(notifs)} pending notifications into context")
                             context_msg = "\n\n[SYSTEM ALERT: Supervisor Notifications Pending]"
                             for n in notifs:
                                 context_msg += f"\n- {n.title}: {n.content}"
                             context_msg += "\nPlease address these items if relevant to the current task."
                             
                             message += context_msg
                             
        except Exception as e:
            logger.warning(f"[{self.agent_id}] Failed to inject context: {e}")
        # ------------------------------------------------------------------

        thread_id = thread_id or self.session_id
        logger.info(f"[{self.agent_id}:{thread_id}] Received: {message[:100]}...")
        # Run the graph
        config = {"configurable": {"thread_id": thread_id}}
        
        # Initial state: user query
        initial_state: AgentConversationState = {
            "query": message,
            "messages": [HumanMessage(content=message)],  # pyre-ignore[16]
            "response": "",
            "agent_id": self.agent_id,
            "session_id": thread_id,
            "context": None,
            "summarized_index": 0,
            "citations": [],
            "approval_pending": False,
            "user_timezone": user_timezone,
            "tool_rounds": 0
        }
        
        try:
            # Run the graph asynchronously
            # Use ainvoke for compatibility with async nodes
            result = await graph.ainvoke(initial_state, config)

            # CHECK FOR INTERRUPTS (async state retrieval)
            snapshot = await graph.aget_state(config)
            if snapshot.tasks:
                for task in snapshot.tasks:
                    interrupts = getattr(task, 'interrupts', [])
                    if interrupts:
                        interrupt_val = getattr(interrupts[0], 'value', {})
                        return {
                            "status": "approval_required",
                            "approval_request_id": interrupt_val.get("approval_request_id", ""),
                            "tool_id": interrupt_val.get("tool_id", ""),
                            "description": interrupt_val.get("description", "A tool requires approval")
                        }

            response_text = result.get("response", "No response generated.")
            citations = result.get("citations", [])
            
            logger.info(f"[{self.agent_id}:{thread_id}] Response: {response_text[:100]}...")
            
            return {
                "response": response_text,
                "citations": citations
            }

        except GraphInterrupt:
            raise
        except GraphRecursionError:
            logger.warning(f"[{self.agent_id}:{thread_id}] GraphRecursionError: Max iterations reached")
            return {
                "response": "I apologize, but I reached the maximum number of steps trying to solve this request.",
                "citations": []
            }
        except Exception as e:
            logger.error(f"[{self.agent_id}:{thread_id}] Error: {e}")
            return {
                "response": f"I apologize, but I encountered an error: {str(e)}",
                "citations": []
            }

    async def resume_chat(self, thread_id: str, resume_value: Dict) -> str:
        """
        Resume a paused agent conversation (Async).
        """
        graph = self.compiled_graph
        if not graph:
            raise ValueError(f"[{self.agent_id}] Graph not compiled")
            
        logger.info(f"[{self.agent_id}:{thread_id}] Resuming with value: {resume_value}")
        
        config = {"configurable": {"thread_id": thread_id}, "recursion_limit": 20}
        
        try:
            # Resume asynchronously
            result = await graph.ainvoke(
                Command(resume=resume_value),  # pyre-ignore[16]
                config
            )
            
            snapshot = await graph.aget_state(config)
            if snapshot.tasks:
                for task in snapshot.tasks:
                    if hasattr(task, 'interrupts') and task.interrupts:
                        for inter in task.interrupts:
                            logger.info(f"[{self.agent_id}] Detected interrupt in state: {inter.value}")
                            raise GraphInterrupt(inter.value)
                            
            response = result.get("response", "")
            logger.info(f"[{self.agent_id}:{thread_id}] Response (Resumed): {response[:100]}...")
            return response
            
        except GraphInterrupt:
            raise
        except Exception as e:
            logger.error(f"[{self.agent_id}:{thread_id}] Resume Error: {e}")
            return f"I apologize, but I entered an error resuming the conversation: {str(e)}"

    def reset_history(self, thread_id: Optional[str] = None):
        """
        Clear conversation history for a thread.

        With LangGraph, you can clear by using a new thread_id.
        """
        thread_id = thread_id or self.session_id
        logger.info(f"[{self.agent_id}:{thread_id}] History cleared (use new thread_id for fresh conversation)")

    def clear_history(self, thread_id: Optional[str] = None):
        """Alias for reset_history for backward compatibility."""
        self.reset_history(thread_id)

    def get_agent_info(self) -> Dict:
        """Get agent information."""
        return {
            "agent_id": self.agent_id,
            "agent_type": "LangGraph StateGraph",
            "langgraph_version": "1.0.5+",
            "system_prompt": self.system_prompt[:200] + "...",
            "keep_history": self.keep_history,
            "max_history": self.max_history,
            "session_id": self.session_id,
            "graph_compiled": self.compiled_graph is not None,
            "checkpointing_enabled": True
        }

    def get_graph_visualization(self) -> str:
        """
        Get ASCII visualization of the agent's graph.
        """
        if not self.compiled_graph:
            return "Graph not built"

        try:
            return str(self.compiled_graph.get_graph().draw_ascii())
        except Exception as e:
            logger.warning(f"Could not generate visualization: {e}")
            return "Visualization not available"

    def __repr__(self) -> str:
        return f"<LangGraphAgent: {self.agent_id}>"


# =========================================================================
# FACTORY FUNCTION
# =========================================================================

def create_langgraph_agent(
    agent_id: str,
    keep_history: bool = True,
    session_id: Optional[str] = None
) -> LangGraphBaseAgent:
    """
    Factory function to create a LangGraph-based agent.

    Args:
        agent_id: Agent identifier
        keep_history: Whether to maintain conversation history
        session_id: Session identifier

    Returns:
        Configured LangGraphBaseAgent instance
    """
    return LangGraphBaseAgent(
        agent_id=agent_id,
        keep_history=keep_history,
        session_id=session_id
    )
