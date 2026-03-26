"""
LangGraph-Based Supervisor Agent

This is the PROPER implementation using LangGraph's StateGraph.
Replaces the manual delegation logic with LangGraph's orchestration.
"""

from typing import Dict, List, Optional, Any, Literal
from loguru import logger

from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver
from langgraph.errors import GraphInterrupt, GraphRecursionError
from langchain_core.messages import HumanMessage, AIMessage

from app.agents.langgraph_base_agent import LangGraphBaseAgent
from app.agents.langgraph_state import AgentState
from app.agents.langgraph_nodes import (
    route_query_node,
    supervisor_node,
    create_twg_agent_node,
    synthesis_node,
    single_agent_response_node,
    negotiation_node
)
from app.services.supervisor_state_service import get_supervisor_state, SupervisorGlobalState


class LangGraphSupervisor:
    """
    LangGraph-based Supervisor for multi-agent orchestration.

    Uses StateGraph to properly manage agent workflows with:
    - Conditional routing
    - State management
    - Checkpointing
    - Parallel execution where appropriate
    """

    def __init__(
        self,
        keep_history: bool = True,
        session_id: Optional[str] = None,
        use_redis: bool = False,
        memory_ttl: Optional[int] = None
    ):
        """
        Initialize the LangGraph Supervisor.

        Args:
            keep_history: Whether to maintain conversation history
            session_id: Session identifier for checkpointing
            use_redis: If True, use Redis for persistent memory (future)
            memory_ttl: TTL for Redis keys in seconds (optional)
        """
        self.session_id = session_id or "default"
        self.keep_history = keep_history
        self.use_redis = use_redis
        self.memory_ttl = memory_ttl

        # Create supervisor agent (for general knowledge and synthesis)
        # CRITICAL: Supervisor has MANY tools (20+ tools) which consume ~8-10K tokens
        # With a 16K context window, we can only afford 3-5 messages of history
        # Otherwise we hit: "This model's maximum context length is 16384 tokens"
        self.supervisor_agent = LangGraphBaseAgent(
            agent_id="supervisor",
            keep_history=keep_history,
            max_history=6,  # INCREASED from 3 to 6 to prevent context loss on follow-ups (e.g. "proceed")
            session_id=session_id,
            use_redis=use_redis,
            memory_ttl=memory_ttl
        )

        # Initialize access to Global State
        self.state_service = get_supervisor_state()

        # Supervisor tools are now registered in the ToolRegistry.
        # Set the module-level context so consult_twg_agents_tool can reach agents.
        from app.tools.supervisor_tools import set_supervisor_context
        set_supervisor_context(twg_agents={}, session_id=session_id)

        # Registry of TWG agents
        self._twg_agents: Dict[str, LangGraphBaseAgent] = {}

        # The LangGraph StateGraph
        self.graph = None
        self.compiled_graph = None

        # Memory saver for checkpointing
        self.memory = MemorySaver()

        logger.info(f"LangGraphSupervisor initialized for session '{self.session_id}'")

    def _update_supervisor_context(self):
        """Update the supervisor tool context with current agent references."""
        from app.tools.supervisor_tools import set_supervisor_context
        set_supervisor_context(twg_agents=self._twg_agents, session_id=self.session_id)


    def register_agent(self, agent_id: str, agent: LangGraphBaseAgent) -> None:
        """Register a TWG agent."""
        self._twg_agents[agent_id] = agent
        self._update_supervisor_context()
        logger.info(f"[SUPERVISOR] Registered {agent_id} agent")

    def register_all_agents(self) -> None:
        """Automatically register all LangGraph-based TWG agents."""
        # Import LangGraph-based agents
        from app.agents.langgraph_energy_agent import create_langgraph_energy_agent
        from app.agents.langgraph_agriculture_agent import create_langgraph_agriculture_agent
        from app.agents.langgraph_minerals_agent import create_langgraph_minerals_agent
        from app.agents.langgraph_digital_agent import create_langgraph_digital_agent
        from app.agents.langgraph_protocol_agent import create_langgraph_protocol_agent
        from app.agents.langgraph_resource_mobilization_agent import create_langgraph_resource_mobilization_agent

        agents = {
            "energy": create_langgraph_energy_agent(keep_history=True),
            "agriculture": create_langgraph_agriculture_agent(keep_history=True),
            "minerals": create_langgraph_minerals_agent(keep_history=True),
            "digital": create_langgraph_digital_agent(keep_history=True),
            "protocol": create_langgraph_protocol_agent(keep_history=True),
            "resource_mobilization": create_langgraph_resource_mobilization_agent(keep_history=True),
        }

        for agent_id, agent in agents.items():
            self.register_agent(agent_id, agent)

        logger.info(f"[SUPERVISOR] All {len(agents)} LangGraph TWG agents registered")

    def build_graph(self) -> None:
        """
        Build the LangGraph StateGraph.

        This is the core orchestration logic using LangGraph's proper patterns.
        """
        if not self._twg_agents:
            raise ValueError("No TWG agents registered. Call register_all_agents() first.")

        logger.info("[SUPERVISOR] Building LangGraph StateGraph...")

        # Create the graph
        workflow = StateGraph(AgentState)

        # =====================================================================
        # ADD NODES
        # =====================================================================

        # 1. Route query node - determines which agents to consult
        workflow.add_node("route_query", route_query_node)

        # 2. Supervisor node - handles general queries
        async def call_supervisor_node(state: AgentState) -> AgentState:
            return await supervisor_node(state, self.supervisor_agent)
            
        workflow.add_node("supervisor", call_supervisor_node)

        # 3. TWG agent nodes - one for each registered agent
        for agent_id, agent in self._twg_agents.items():
            workflow.add_node(
                agent_id,
                create_twg_agent_node(agent_id, agent)
            )

        # 4. Synthesis node - combines multiple agent responses
        async def call_synthesis_node(state: AgentState) -> AgentState:
            return await synthesis_node(state, self.supervisor_agent)
            
        workflow.add_node("synthesis", call_synthesis_node)

        # 5. Single agent response node - formats single agent response
        workflow.add_node("single_agent_response", single_agent_response_node)

        # 6. Negotiation node
        workflow.add_node("negotiation", negotiation_node)

        # =====================================================================
        # ADD EDGES AND CONDITIONAL ROUTING
        # =====================================================================

        # Set entry point
        workflow.set_entry_point("route_query")

        # Add dispatch_multiple node for handling multiple agents
        async def dispatch_multiple_node(state: AgentState) -> AgentState:
            """
            Dispatch query to multiple TWG agents in PARALLEL (Async Fan-Out).
            """
            import asyncio
            relevant_agents = state["relevant_agents"]
            query = state["query"]

            state["agent_responses"] = {}
            
            # Helper function for parallel execution
            async def query_agent(agent_id: str, agent: LangGraphBaseAgent, dispatch_thread_id: Optional[str], user_timezone: Optional[str]) -> tuple[str, str]:
                try:
                    logger.info(f"[DISPATCH] Querying {agent_id} in parallel...")
                    response = await agent.chat(query, thread_id=dispatch_thread_id, user_timezone=user_timezone)
                    return (agent_id, response)
                except GraphInterrupt:
                    logger.info(f"[DISPATCH] Interrupt from {agent_id} detected in supervisor")
                    raise
                except Exception as e:
                    if type(e).__name__ == "GraphInterrupt":
                        logger.info(f"[DISPATCH] GraphInterrupt caught as Exception from {agent_id}")
                        raise e
                    logger.error(f"[DISPATCH] Error with {agent_id}: {e}")
                    return (agent_id, f"Error: {str(e)}")

            dispatch_thread_id = state.get("session_id")
            user_timezone = state.get("user_timezone")
            
            # Prepare tasks
            tasks = []
            for agent_id in relevant_agents:
                if agent_id in self._twg_agents:
                    tasks.append(query_agent(agent_id, self._twg_agents[agent_id], dispatch_thread_id, user_timezone))
            
            if not tasks:
                 return state

            # Execute in parallel
            try:
                results = await asyncio.gather(*tasks)
                for agent_id, response in results:
                    state["agent_responses"][agent_id] = response
            except GraphInterrupt:
                # Re-raise interruption immediately
                raise

            return state

        workflow.add_node("dispatch_multiple", dispatch_multiple_node)

        # Conditional routing after route_query
        def route_to_agents(state: AgentState) -> str:
            """
            Determine next step based on routing decision.

            Returns:
                - "supervisor" if no specific TWG needed
                - agent_id if single agent
                - "parallel_agents" if multiple agents (future enhancement)
                - "negotiation" if negotiation is explicitly requested
            """
            delegation_type = state.get("delegation_type")
            relevant_agents = state["relevant_agents"]

            if delegation_type == "negotiation":
                return "negotiation"
            
            if delegation_type == "supervisor_only":
                logger.info("[ROUTE] -> supervisor (general knowledge)")
                return "supervisor"

            elif delegation_type == "single":
                agent_id = relevant_agents[0]
                logger.info(f"[ROUTE] -> {agent_id} (single agent)")
                return agent_id

            else:  # multiple agents
                logger.info(f"[ROUTE] -> multiple agents: {relevant_agents}")
                return "dispatch_multiple"

        workflow.add_conditional_edges(
            "route_query",
            route_to_agents,
            {
                "supervisor": "supervisor",
                "negotiation": "negotiation",
                **{agent_id: agent_id for agent_id in self._twg_agents.keys()},
                "dispatch_multiple": "dispatch_multiple"
            }
        )

        
        # Function to check if the supervisor or synthesis output triggers a negotiation
        def check_for_negotiation_trigger(state: AgentState) -> str:
            """
            Check if the final response contains the negotiation trigger flag.
            """
            response = state.get("final_response") or ""
            # Check for the tool output in the response content (it might be raw tool output)
            # Or if the LLM output describes starting one (less reliable)
            
            # The tool output is "NEGOTIATION_STARTED::{desc}::{a}::{b}"
            if "NEGOTIATION_STARTED::" in response:
                logger.info("[COND] NEGOTIATION_STARTED trigger detected!")
                
                parts = response.split("::")
                if len(parts) >= 4:
                    desc, a, b = parts[1], parts[2], parts[3]
                    state["negotiation_context"] = {
                        "conflict_description": desc,
                        "agent_ids": [a, b]
                    }
                    return "negotiation"
            
            # Also check for synthesis conflict detection
            if "CONFLICT ALERT:" in response:
                 # TODO: Parse conflict alert to auto-trigger? 
                 # For now, let's Stick to manual tool trigger which is safer
                 pass

            return END

        # From supervisor -> check trigger -> negotiation OR end
        workflow.add_conditional_edges(
            "supervisor",
            check_for_negotiation_trigger,
            {
                "negotiation": "negotiation",
                END: END
            }
        )

        # From single agents -> single_agent_response -> END
        for agent_id in self._twg_agents.keys():
            workflow.add_edge(agent_id, "single_agent_response")

        workflow.add_edge("single_agent_response", END)

        # From dispatch_multiple -> synthesis -> check trigger -> negotiation OR end
        workflow.add_edge("dispatch_multiple", "synthesis")
        workflow.add_conditional_edges(
            "synthesis",
            check_for_negotiation_trigger,
            {
                "negotiation": "negotiation",
                END: END
            }
        )
        
        # From negotiation -> END
        workflow.add_edge("negotiation", END)

        # =====================================================================
        # COMPILE GRAPH
        # =====================================================================

        # Compile with checkpointing
        self.graph = workflow
        self.compiled_graph = workflow.compile(checkpointer=self.memory)

        logger.info("[SUPERVISOR] ✓ LangGraph StateGraph compiled successfully")
        logger.info(f"[SUPERVISOR] Nodes: route_query, supervisor, {', '.join(self._twg_agents.keys())}, synthesis, single_agent_response, dispatch_multiple")

    async def chat(self, message: str, thread_id: Optional[str] = None, twg_id: Optional[str] = None, user_timezone: Optional[str] = None) -> dict:
        """
        Chat interface using LangGraph execution.

        Args:
            message: User query
            thread_id: Optional thread ID for conversation threading
            twg_id: Optional TWG ID to restrict context (Strict RBAC)

        Returns:
            Agent response
        """
        if not self.compiled_graph:
            raise ValueError("Graph not built. Call build_graph() first.")

        thread_id = thread_id or self.session_id

        logger.info(f"[SUPERVISOR:{thread_id}] Received: {message[:100]}... (Context: {twg_id or 'General'})")

        # Initialize state
        initial_state: AgentState = {
            "messages": [HumanMessage(content=message)],
            "query": message,
            "relevant_agents": [],
            "agent_responses": {},
            "synthesized_response": None,
            "final_response": "",
            "requires_synthesis": False,
            "delegation_type": "supervisor_only",
            "session_id": thread_id,
            "user_id": None,
            "context": {"twg_id": twg_id} if twg_id else None,
            "user_timezone": user_timezone,
            "citations": []
        }

        # Run the graph
        # Enforce recursion limit for supervisor workflow
        config = {"configurable": {"thread_id": thread_id}, "recursion_limit": 30}

        try:
            # Use ainvoke for async execution (required since route_query_node is async)
            result = await self.compiled_graph.ainvoke(initial_state, config)

            # CHECK FOR INTERRUPTS (same logic as LangGraphBaseAgent)
            # The Main Graph's invoke() might not re-raise exceptions from nodes
            snapshot = await self.compiled_graph.aget_state(config)
            if snapshot.tasks:
                for task in snapshot.tasks:
                    if hasattr(task, 'interrupts') and task.interrupts:
                        for inter in task.interrupts:
                            # inter.value contains the actual payload
                            interrupt_value = inter.value if hasattr(inter, 'value') else inter
                            logger.info(f"[SUPERVISOR] Detected interrupt in state: {interrupt_value}")
                            # Import here to avoid scope issues
                            from langgraph.errors import GraphInterrupt as GI
                            raise GI(interrupt_value)

            final_response = result.get("final_response", "")
            citations = result.get("citations", [])

            logger.info(f"[SUPERVISOR:{thread_id}] Response generated")

            return {
                "response": final_response,
                "citations": citations
            }

        except GraphRecursionError:
            logger.warning(f"[SUPERVISOR:{thread_id}] GraphRecursionError: Max iterations reached")
            return {
                "response": "I apologize, but the supervisor reached the maximum number of steps. This usually indicates a complex loop or conflict. Please refine your request.",
                "citations": []
            }

        except Exception as e:
            # Check for GraphInterrupt by name to avoid import/scope issues
            if type(e).__name__ == "GraphInterrupt":
                raise e

            logger.error(f"[SUPERVISOR:{thread_id}] Error: {e}")
            return {
                "response": f"I apologize, but I encountered an error: {str(e)}",
                "citations": []
            }

    async def stream_chat(self, message: str, thread_id: Optional[str] = None, twg_id: Optional[str] = None, user_timezone: Optional[str] = None):
        """
        Stream chat events from LangGraph execution.
        Yields events for each step in the graph.
        """
        if not self.compiled_graph:
            raise ValueError("Graph not built. Call build_graph() first.")

        thread_id = thread_id or self.session_id
        logger.info(f"[SUPERVISOR:{thread_id}] Streaming: {message[:100]}...")
        logger.info(f"[SUPERVISOR:{thread_id}] TWG ID parameter: {twg_id} (type: {type(twg_id).__name__})")

        initial_state: AgentState = {
            "messages": [HumanMessage(content=message)],
            "query": message,
            "relevant_agents": [],
            "agent_responses": {},
            "synthesized_response": None,
            "final_response": "",
            "requires_synthesis": False,
            "delegation_type": "supervisor_only",
            "session_id": thread_id,
            "user_id": None,
            "context": {"twg_id": twg_id, "user_timezone": user_timezone} if twg_id or user_timezone else None,
            "user_timezone": user_timezone
        }

        config = {"configurable": {"thread_id": thread_id}, "recursion_limit": 30}

        try:
            # Track whether we already yielded a final response to prevent duplicates
            _final_response_yielded = False

            # Use astream_events(version="v2") for granular token and tool streaming
            async for event in self.compiled_graph.astream_events(initial_state, config, version="v2"):
                event_type = event["event"]
                name = event.get("name", "")

                # Yield Node starts (chain starts that match our graph nodes)
                if event_type == "on_chain_start" and name in ["route_query", "supervisor", "dispatch_multiple", "synthesis", "single_agent_response", "energy", "agriculture", "minerals", "digital", "protocol", "resource_mobilization"]:
                    yield {
                        "type": "node_update",
                        "node": name
                    }

                # Granular Streaming: Tool Starts
                elif event_type == "on_tool_start":
                    yield {
                        "type": "tool_start",
                        "tool": name,
                        "args": event.get("data", {}).get("input", {})
                    }

                # Granular Streaming: Tool Ends
                elif event_type == "on_tool_end":
                    yield {
                        "type": "tool_result",
                        "tool": name,
                        "result": str(event.get("data", {}).get("output", ""))[:200] + "..." # Truncate long results for UI
                    }

                # Granular Streaming: LLM Tokens
                elif event_type == "on_chat_model_stream":
                    chunk = event.get("data", {}).get("chunk")
                    if chunk and hasattr(chunk, "content") and chunk.content:
                        yield {
                            "type": "token",
                            "content": chunk.content
                        }

                # End of specific graph nodes producing final response
                elif event_type == "on_chain_end" and name in ["supervisor", "synthesis", "single_agent_response", "energy", "agriculture", "minerals", "digital", "protocol", "resource_mobilization"]:
                    state_update = event.get("data", {}).get("output", {})
                    if isinstance(state_update, dict) and "final_response" in state_update and state_update["final_response"]:
                        if not _final_response_yielded:
                            _final_response_yielded = True
                            yield {
                                 "type": "final_response",
                                 "content": state_update["final_response"]
                            }

            # CHECK FOR INTERRUPTS (After stream ends, check if it was paused)
            snapshot = await self.compiled_graph.aget_state(config)
            if snapshot.tasks:
                for task in snapshot.tasks:
                    interrupts = getattr(task, 'interrupts', None)
                    if interrupts:
                        for inter in interrupts:
                            interrupt_value = getattr(inter, 'value', inter)
                            logger.info(f"[SUPERVISOR] Detected interrupt in state after stream: {interrupt_value}")
                            from langgraph.errors import GraphInterrupt as GI
                            raise GI(interrupt_value)
            # Also check snapshot.next — if graph is paused (not at END), it may be interrupted
            if snapshot.next and not _final_response_yielded:
                logger.info(f"[SUPERVISOR] Graph paused at node(s): {snapshot.next} — possible interrupt")

            # AFTER STREAM: Fallback — only yield if nothing was yielded during stream
            if not _final_response_yielded:
                final_state = snapshot.values if snapshot else None
                if final_state and isinstance(final_state, dict):
                    final_response = final_state.get("final_response")
                    if final_response:
                        logger.info(f"[SUPERVISOR] Yielding final_response from final state (fallback)")
                        _final_response_yielded = True
                        yield {
                            "type": "final_response",
                            "content": final_response
                        }
                    # Also check agent_responses for single agent case
                    elif "agent_responses" in final_state and final_state["agent_responses"]:
                        for agent_id, response_raw in final_state["agent_responses"].items():
                            response_text = ""
                            if isinstance(response_raw, dict):
                                response_text = response_raw.get("response", "")
                            else:
                                response_text = str(response_raw)
                            if response_text:
                                logger.info(f"[SUPERVISOR] Yielding response from agent_responses[{agent_id}] (fallback)")
                                _final_response_yielded = True
                                yield {
                                    "type": "final_response",
                                    "content": f"[Consulted {agent_id.upper()} TWG]\n\n{response_text}"
                                }
                                break

            # 3d. Empty response fallback — if nothing was yielded at all
            if not _final_response_yielded:
                logger.warning(f"[SUPERVISOR:{thread_id}] Stream completed with no final response — yielding fallback")
                yield {
                    "type": "final_response",
                    "content": "I encountered an issue processing your request. Please try rephrasing or ask about a specific topic."
                }

        except Exception as e:
            # Check for GraphInterrupt by name to avoid import/scope issues or re-raise if caught
            if type(e).__name__ == "GraphInterrupt":
                raise e
                
            yield {"type": "error", "error": str(e)}

    async def resume_chat(self, thread_id: str, resume_value: Dict) -> str:
        """
        Resume a paused conversation by checking which agent is interrupted.
        
        Args:
            thread_id: The thread ID
            resume_value: The value to provide to the interrupted node
        """
        logger.info(f"[SUPERVISOR:{thread_id}] Attempting to resume chat...")
        
        # 1. Check child agents
        for agent_id, agent in self._twg_agents.items():
            if not agent.compiled_graph:
                continue
                
            config = {"configurable": {"thread_id": thread_id}}
            snapshot = agent.compiled_graph.get_state(config)
            
                
            # Check if this agent is interrupted
            if snapshot.tasks:
                for task in snapshot.tasks:
                    if hasattr(task, 'interrupts') and task.interrupts:
                        logger.info(f"[SUPERVISOR] Found interrupt in agent '{agent_id}'. Resuming...")
                        # Resume this agent (Async)
                        return await agent.resume_chat(thread_id, resume_value)
        
        # 2. Check supervisor agent (the general one)
        config = {"configurable": {"thread_id": thread_id}}
        snapshot = await self.supervisor_agent.compiled_graph.aget_state(config)
        if snapshot.tasks:
             for task in snapshot.tasks:
                    if hasattr(task, 'interrupts') and task.interrupts:
                        logger.info(f"[SUPERVISOR] Found interrupt in supervisor agent. Resuming...")
                        return await self.supervisor_agent.resume_chat(thread_id, resume_value)

        logger.warning(f"[SUPERVISOR:{thread_id}] No interrupted agent found to resume.")
        return "No active interruption found to resume."

    def get_graph_visualization(self) -> str:
        """
        Get ASCII visualization of the graph structure.

        Returns:
            Graph visualization as string
        """
        if not self.compiled_graph:
            return "Graph not built yet. Call build_graph() first."

        try:
            # LangGraph provides visualization capabilities
            return str(self.compiled_graph.get_graph().draw_ascii())
        except Exception as e:
            logger.warning(f"Could not generate visualization: {e}")
            return "Visualization not available"

    def get_registered_agents(self) -> List[str]:
        """Get list of registered agent IDs."""
        return list(self._twg_agents.keys())

    def get_supervisor_status(self) -> Dict[str, Any]:
        """Get supervisor status information."""
        return {
            "supervisor_type": "LangGraph StateGraph",
            "langgraph_version": "1.0.5+",
            "session_id": self.session_id,
            "registered_agents": self.get_registered_agents(),
            "agent_count": len(self._twg_agents),
            "graph_built": self.compiled_graph is not None,
            "history_enabled": self.keep_history,
            "checkpointing_enabled": True,
            "memory_type": "MemorySaver"
        }

    def reset_history(self, thread_id: Optional[str] = None):
        """
        Clear conversation history for a thread.

        Note: With LangGraph checkpointing, history is managed per thread.
        """
        thread_id = thread_id or self.session_id
        # In LangGraph, you can clear by not using previous thread_id
        logger.info(f"[SUPERVISOR:{thread_id}] History cleared (use new thread_id)")


# =========================================================================
# CONVENIENCE FUNCTIONS
# =========================================================================

def create_langgraph_supervisor(
    keep_history: bool = True,
    auto_register: bool = True,
    session_id: Optional[str] = None,
    use_redis: bool = False,
    memory_ttl: Optional[int] = None
) -> LangGraphSupervisor:
    """
    Create and return a LangGraph Supervisor instance.

    Args:
        keep_history: Whether to maintain conversation history
        auto_register: If True, automatically register all TWG agents
        session_id: Session identifier
        use_redis: If True, use Redis for persistent memory (future)
        memory_ttl: TTL for Redis keys in seconds (optional)

    Returns:
        Configured LangGraphSupervisor instance
    """
    supervisor = LangGraphSupervisor(
        keep_history=keep_history,
        session_id=session_id,
        use_redis=use_redis,
        memory_ttl=memory_ttl
    )

    if auto_register:
        supervisor.register_all_agents()
        supervisor.build_graph()

    return supervisor
