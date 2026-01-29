"""
LangGraph Base Agent - PROPER IMPLEMENTATION

All agents (TWG agents and Supervisor) should inherit from this.
Uses LangGraph StateGraph for proper agent orchestration.
"""

from typing import Annotated, TypedDict, List, Dict, Optional, Sequence
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
    
    # Store structured citations for frontend
    citations: Annotated[List[Dict], add]
    
    # Flag to indicate an approval is pending (stops agent loop)
    approval_pending: Optional[bool]
    
    # User's Timezone (e.g., "Africa/Lagos")
    user_timezone: Optional[str]


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
        
        # Tools Configuration
        from app.tools.calendar_tools import (
            GET_SCHEDULE_TOOL_DEF, get_schedule, 
            GET_PAST_MEETINGS_TOOL_DEF, get_past_meetings,
            UPDATE_MEETING_TOOL_DEF, update_meeting
        )
        from app.tools.email_tools import EMAIL_TOOLS, send_email, create_email_draft
        from app.tools.document_tools import REQUEST_DOCUMENT_APPROVAL_TOOL_DEF, request_document_approval_tool
        import json
        
        # Register default tools available to all agents (or specific ones)
        
        # 1. Start with standard tools (including update_meeting so agents can actually persist changes)
        self.tools_def = [
            GET_SCHEDULE_TOOL_DEF, 
            GET_PAST_MEETINGS_TOOL_DEF,
            UPDATE_MEETING_TOOL_DEF, 
            REQUEST_DOCUMENT_APPROVAL_TOOL_DEF
        ]
        
        # 2. Convert and add EMAIL_TOOLS
        for tool in EMAIL_TOOLS:
            # Create standard OpenAI tool definition
            tool_def = {
                "type": "function",
                "function": {
                    "name": tool["name"],
                    "description": tool["description"],
                    "parameters": {
                        "type": "object",
                        "properties": tool["parameters"],
                        # Assuming all params optional for now or need strict parsing
                        # Simple schema adjustment:
                        "required": [] 
                    }
                }
            }
            # Adjust properties format if needed. 
            # EMAIL_TOOLS params are simple key-value descriptions. 
            # We need to construct a valid JSON schema for parameters.
            
            new_props = {}
            for param_name, param_desc in tool["parameters"].items():
                # Default generic schema
                prop_schema = {
                    "type": "string",
                    "description": param_desc
                }
                
                # Specific Type Overrides
                if param_name in ["max_results", "days"]:
                    prop_schema["type"] = "integer"
                elif param_name in ["include_body"]:
                    prop_schema["type"] = "boolean"
                elif param_name in ["variables", "exclude_files"]:
                    prop_schema["type"] = "object"
                
                # Handle 'to': String or List of strings
                elif param_name == "to":
                    prop_schema = {
                        "anyOf": [
                            {"type": "string"},
                            {"type": "array", "items": {"type": "string"}}
                        ],
                        "description": param_desc
                    }
                
                # Handle 'attachments': List of strings (or null/string fallback)
                elif param_name == "attachments":
                     prop_schema = {
                        "anyOf": [
                            {"type": "array", "items": {"type": "string"}},
                            {"type": "string"},
                            {"type": "null"}
                        ],
                        "description": param_desc
                    }

                # Handle Nullable Strings (cc, bcc, html_body, pillar_name, context)
                elif param_name in ["cc", "bcc", "html_body", "pillar_name", "context"]:
                    prop_schema = {
                        "anyOf": [
                            {"type": "string"},
                            {"type": "null"}
                        ],
                        "description": param_desc
                    }

                new_props[param_name] = prop_schema
            
            tool_def["function"]["parameters"]["properties"] = new_props
            self.tools_def.append(tool_def)

        # 3. Build Tool Map (only include available tools)
        self.tool_map = {
            "get_schedule": get_schedule,
            "get_past_meetings": get_past_meetings,
            "update_meeting": update_meeting,
            "send_email": send_email,
            "create_email_draft": create_email_draft,
            "request_document_approval_tool": request_document_approval_tool
        }
        
        # Get Knowledge Base (RAG)
        try:
            self.kb = get_knowledge_base()
        except Exception as e:
            logger.warning(f"[{agent_id}] Knowledge Base not available: {e}")
            self.kb = None
            
        # Resolve TWG ID for RAG context scoping
        from app.agents.utils import get_twg_id_by_agent_id 
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
        
        workflow.add_edge("execute_tools", "generate_response")

        # Compile with checkpointing
        self.graph = workflow
        self.compiled_graph = workflow.compile(checkpointer=self.memory)

        logger.info(f"[{self.agent_id}] StateGraph compiled with Tools loop")

    def _should_continue(self, state: AgentConversationState) -> str:
        """
        Determine if we should continue to tool execution or end.
        """
        # CRITICAL: If an approval is pending, STOP the loop immediately
        if state.get("approval_pending"):
            logger.info(f"[{self.agent_id}] Approval pending - ending loop")
            return "end"
        
        messages = state["messages"]
        last_message = messages[-1]
        
        # Check if AIMessage has tool_calls
        # Note: GroqLLMService now returns object with tool_calls if present
        # In our state, we store AIMessage. 
        # We need to ensure we stored it correctly in _generate_response_node
        
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
                    state['context'] = {"retrieved_docs": context_text, "source": namespace}
                    
                    # Also populate structured citations
                    citations = []
                    for r in results:
                         citations.append({
                             "source": r['metadata'].get('file_name', 'Unknown'),
                             "page": r['metadata'].get('page', 1),
                             "relevance": r['score']
                         })
                    state['citations'] = citations
                    
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
        messages = state.get("messages", [])
        
        # Enforce History Limit to prevent 413 errors & Infinite Loops
        if len(messages) > 20:
             logger.warning(f"[{self.agent_id}] Loop detected (20+ messages). Truncating and forcing text response.")
             messages = messages[-self.max_history:]
             
        if len(messages) > self.max_history:
             messages = messages[-self.max_history:]
        
        logger.info(f"[{self.agent_id}] Generating response...")

        try:
            # Prepare messages for LLM service (dict format)
            history = []
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
            # Rule: Assistant with tool_calls MUST be followed by Tool messages
            sanitized_history = []
            skip_indices = set()
            
            for i in range(len(history)):
                msg = history[i]
                
                # Check for dangling tool calls
                if msg.get("role") == "assistant" and "tool_calls" in msg:
                    # Look ahead for matching tool outputs
                    tool_call_ids = {tc["id"] for tc in msg["tool_calls"]}
                    found_responses = set()
                    
                    # Scan subsequent messages for tool responses
                    # In a valid conversation, immediate next messages should be tools
                    j = i + 1
                    while j < len(history) and history[j].get("role") == "tool":
                        if history[j].get("tool_call_id") in tool_call_ids:
                             found_responses.add(history[j].get("tool_call_id"))
                        j += 1
                        
                    # If any tool call is missing a response, we consider this turn 'broken'/interrupted
                    # To satisfy OpenAI, we must either:
                    # 1. Provide fake responses (hard to guess)
                    # 2. Strip the tool_calls from the assistant message
                    if len(found_responses) < len(tool_call_ids):
                         logger.warning(f"[{self.agent_id}] Sanitizing history: Msg {i} has dangling tool calls. Stripping tools.")
                         del msg["tool_calls"]
                         if not msg.get("content"):
                             msg["content"] = "[System: Previous tool call interrupted]"
                
                sanitized_history.append(msg)
            
            history = sanitized_history

            # RAG Context injection (simplified)
            # RAG Context injection (simplified)
            from datetime import datetime, timezone as tz
            from zoneinfo import ZoneInfo
            
            # Use user's timezone if provided, otherwise default to Nairobi
            tz_name = state.get("user_timezone") or "Africa/Nairobi"
            try:
                user_tz = ZoneInfo(tz_name)
            except Exception:
                logger.warning(f"Invalid timezone {tz_name}, falling back to Africa/Nairobi")
                user_tz = ZoneInfo("Africa/Nairobi")
                
            now = datetime.now(user_tz)
            current_time_str = now.strftime("%A, %B %d, %Y at %I:%M %p")
            today_date = now.strftime("%Y-%m-%d")
            
            sys_prompt = f"{self.system_prompt}\n\nCurrent Date & Time: {current_time_str} ({tz_name})\nToday's date is: {today_date}"
            
            context = state.get("context")
            if context and "retrieved_docs" in context:
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
                    try:
                        args_parsed = json.loads(tc.function.arguments)
                    except (json.JSONDecodeError, TypeError):
                        args_parsed = {}
                    
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
                state["response"] = "[Calling Tool...]" # Intermediate state
                state["messages"].append(ai_msg)
                
            else:
                # Standard text response
                content = response_obj if isinstance(response_obj, str) else response_obj.content
                
                # FALLBACK parsing removed for brevity/stability - relying on standard tool usage
                logger.info(f"[{self.agent_id}] Text Response generated")
                state["response"] = content
                state["messages"].append(AIMessage(content=content))

        except Exception as e:
            logger.error(f"[{self.agent_id}] Error in generation: {e}")
            state["response"] = f"Error: {str(e)}"
            state["messages"].append(AIMessage(content=state["response"]))

        return state

    async def _execute_tools_node(self, state: AgentConversationState) -> AgentConversationState:
        """
        Execute tool calls request by the LLM (Async).
        """
        messages = state["messages"]
        last_message = messages[-1]
        
        if not hasattr(last_message, "tool_calls") or not last_message.tool_calls:
            return state
            
        from langchain_core.messages import ToolMessage
        from langgraph.errors import GraphInterrupt
        import json
        
        new_messages = []
        
        for tool_call in last_message.tool_calls:
            tool_name = tool_call["name"]
            tool_args = tool_call["args"]
            tool_id = tool_call["id"]
            
            logger.info(f"[{self.agent_id}] Executing tool: {tool_name}")
            
            try:
                if tool_name in self.tool_map:
                    # Execute function
                    func = self.tool_map[tool_name]
                    
                    import inspect
                    import asyncio
                    
                    # AUTO-INJECTION: Inject twg_id if tool accepts it and agent is scoped
                    sig = inspect.signature(func)
                    if "twg_id" in sig.parameters:
                        if self.twg_id and "twg_id" not in tool_args:
                            logger.info(f"[{self.agent_id}] Auto-injecting twg_id={self.twg_id} into {tool_name}")
                            tool_args["twg_id"] = self.twg_id
                            
                    # AUTO-INJECTION: Inject user_timezone for calendar tools if available
                    if "user_timezone" in sig.parameters:
                        tz_context = state.get("user_timezone")
                        if tz_context and "user_timezone" not in tool_args:
                             tool_args["user_timezone"] = tz_context
                    
                    if inspect.iscoroutinefunction(func):
                        # Async function - await directly
                        result = await func(**tool_args)
                    else:
                        # Sync function - run in thread to avoid blocking loop
                        result = await asyncio.to_thread(func, **tool_args)
                        
                else:
                    result = json.dumps({"error": f"Tool {tool_name} not found"})
                
                output_str = str(result)
                
                # SPECIAL HANDLING FOR APPROVAL REQUESTS
                if "approval_request_id" in output_str:
                    try:
                        res_json = json.loads(result) if isinstance(result, str) else result
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
                                 # Ideally we return the Doc ID here if the Approval Action saved it.
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
                
            except GraphInterrupt:
                raise
            except Exception as e:
                logger.error(f"[{self.agent_id}] Tool execution failed: {e}")
                new_messages.append(ToolMessage(tool_call_id=tool_id, content=f"Error: {str(e)}"))

        # Update state with all tool results
        state["messages"].extend(new_messages)
        return state

    async def chat(self, message: str, thread_id: Optional[str] = None, user_timezone: Optional[str] = None) -> Dict[str, any]:
        """
        Chat interface using LangGraph execution (Async).
        """
        if not self.compiled_graph:
            raise ValueError(f"[{self.agent_id}] Graph not compiled")
            
        # ------------------------------------------------------------------
        # CONTEXT INJECTION (Supervisor Feedback Loop)
        # ------------------------------------------------------------------
        # Check for pending notifications for this TWG's Lead
        try:
            from app.core.database import get_db_session_context
            from app.models.models import TWG, Notification, NotificationType
            from sqlalchemy import select, and_
            
            twg_id_str = get_twg_id_by_agent_id(self.agent_id)
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
            "messages": [HumanMessage(content=message)],
            "agent_id": self.agent_id,
            "messages": [HumanMessage(content=message)],
            "agent_id": self.agent_id,
            "session_id": thread_id,
            "citations": [],
            "user_timezone": user_timezone
        }
        
        try:
            # Run the graph asynchronously
            # Use ainvoke for compatibility with async nodes
            result = await self.compiled_graph.ainvoke(initial_state, config)

            # CHECK FOR INTERRUPTS (async state retrieval)
            snapshot = await self.compiled_graph.aget_state(config)
            if snapshot.tasks:
                for task in snapshot.tasks:
                    if hasattr(task, 'interrupts') and task.interrupts:
                        for inter in task.interrupts:
                            interrupt_value = inter.value if hasattr(inter, 'value') else inter
                            logger.info(f"[{self.agent_id}] Detected interrupt in state: {interrupt_value}")
                            raise GraphInterrupt(interrupt_value)

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
        if not self.compiled_graph:
            raise ValueError(f"[{self.agent_id}] Graph not compiled")
            
        logger.info(f"[{self.agent_id}:{thread_id}] Resuming with value: {resume_value}")
        
        config = {"configurable": {"thread_id": thread_id}, "recursion_limit": 20}
        
        try:
            # Resume asynchronously
            result = await self.compiled_graph.ainvoke(
                Command(resume=resume_value),
                config
            )
            
            snapshot = await self.compiled_graph.aget_state(config)
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
