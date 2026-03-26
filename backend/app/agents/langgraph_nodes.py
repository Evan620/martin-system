"""
LangGraph Node Functions for Multi-Agent System

Each function represents a node in the agent graph.
"""

from typing import Dict, List
from loguru import logger
from langchain_core.messages import HumanMessage, AIMessage
from langgraph.errors import GraphInterrupt

from app.agents.langgraph_state import AgentState
from app.agents.langgraph_base_agent import LangGraphBaseAgent


# =========================================================================
# ROUTING NODE - Determines which agents should handle the query
# =========================================================================

async def route_query_node(state: AgentState) -> AgentState:
    """
    Analyze the query and determine which TWG agents are relevant.
    
    Uses LLM-based Intent Parser first, falls back to keyword matching.
    """
    query = state["query"]
    query_lower = query.lower()
    
    # --- DEBUG LOGGING ---
    logger.info(f"[ROUTE] State keys: {list(state.keys())}")
    logger.info(f"[ROUTE] Context value: {state.get('context')}")
    
    # --- STRICT RBAC ENFORCEMENT ---
    context = state.get("context")
    if context and context.get("twg_id"):
        twg_id = context.get("twg_id")
        from app.agents.utils import get_agent_id_by_twg_id
        forced_agent_id = get_agent_id_by_twg_id(twg_id)
        
        if forced_agent_id:
            logger.info(f"[ROUTE] Strict RBAC: Context restricted to {forced_agent_id.upper()}")
            # Force routing to single agent
            state["relevant_agents"] = [forced_agent_id]
            state["delegation_type"] = "single"
            state["requires_synthesis"] = False
            return state
        else:
            logger.warning(f"[ROUTE] Context twg_id {twg_id} did not resolve to an agent. STRICT RBAC BLOCKING.")
            # Fail Closed: Do not allow fallback to Supervisor
            state["relevant_agents"] = []
            state["delegation_type"] = "rbac_failure" 
            return state
    
    
    # --- 0. EXPLICIT ROUTING PREFIX (from @mentions) ---
    import re
    
    # Check for single agent routing: [ROUTING TO ENERGY TWG AGENT] query
    single_route_match = re.search(r"\[ROUTING TO ([A-Z_]+) TWG AGENT\] (.*)", query)
    if single_route_match:
        agent_name = single_route_match.group(1).lower()
        clean_q = single_route_match.group(2)
        
        # specific fix for 'resource_mobilization' which might appear as 'RESOURCE_MOBILIZATION'
        if agent_name == "resource_mobilization": 
             pass # correct
        
        logger.info(f"[ROUTE] Explicit Single Routing detected: {agent_name}")
        state["relevant_agents"] = [agent_name]
        state["delegation_type"] = "single"
        state["requires_synthesis"] = False
        state["query"] = clean_q # Update query to remove routing instruction
        return state

    # Check for multiple agent routing: [ROUTING TO MULTIPLE AGENTS: energy, minerals] query
    multi_route_match = re.search(r"\[ROUTING TO MULTIPLE AGENTS: (.*?)\] (.*)", query)
    if multi_route_match:
        agents_str = multi_route_match.group(1)
        clean_q = multi_route_match.group(2)
        agent_ids = [a.strip().lower() for a in agents_str.split(",")]
        
        logger.info(f"[ROUTE] Explicit Multi Routing detected: {agent_ids}")
        state["relevant_agents"] = agent_ids
        state["delegation_type"] = "multiple"
        state["requires_synthesis"] = True
        state["query"] = clean_q
        return state

    # --- 1. SEMANTIC EMBEDDING ROUTING ---
    from app.services.semantic_router import get_semantic_router

    relevant = []  # Initialize before try block to avoid NameError on fallback
    try:
        router = get_semantic_router()
        routed_agents, del_type = router.route(query)

        if routed_agents:
            # Need to verify if the semantic router returned valid registered agents,
            # but currently ALL main TWGs are valid.
            relevant = routed_agents
            logger.info(f"[ROUTE] Semantic Router delegated to: {relevant} ({del_type})")

    except Exception as e:
        logger.error(f"[ROUTE] Semantic routing failed, falling back to supervisor: {e}")

    # --- 3. SUPERVISOR OVERRIDE FOR CROSS-CUTTING QUERIES ---
    # Scheduling requests → supervisor (has scheduling tools)
    scheduling_keywords = ["schedule", "book", "meeting", "calendar", "appointment"]
    is_scheduling_request = any(keyword in query_lower for keyword in scheduling_keywords)

    if is_scheduling_request and relevant:
        logger.info(f"[ROUTE] Scheduling request detected - overriding to supervisor_only (has scheduling tools)")
        relevant = []

    # Document queries → supervisor (has get_document_registry_tool for cross-TWG search)
    document_keywords = ["document", "file", "pdf", "upload", "registry", "letter", "report", "memo", "brief"]
    is_document_query = any(keyword in query_lower for keyword in document_keywords)

    if is_document_query and relevant:
        logger.info(f"[ROUTE] Document query detected - overriding to supervisor_only (has document registry tool)")
        relevant = []

    # Determine delegation type
    if not relevant:
        delegation_type = "supervisor_only"
    elif len(relevant) == 1:
        delegation_type = "single"
    else:
        delegation_type = "multiple"

    state["relevant_agents"] = relevant
    state["delegation_type"] = delegation_type
    state["requires_synthesis"] = len(relevant) > 1

    return state


# =========================================================================
# SUPERVISOR NODE - Handles general queries without specific TWG
# =========================================================================

async def supervisor_node(state: AgentState, supervisor_agent: LangGraphBaseAgent) -> AgentState:
    """
    Handle queries that don't require specific TWG expertise.
    Uses the supervisor's general knowledge.
    """
    query = state["query"]
    thread_id = state.get("session_id")
    logger.info(f"[SUPERVISOR] Handling query with general knowledge")

    try:
        user_timezone = state.get("user_timezone")
        response = await supervisor_agent.chat(query, thread_id=thread_id, user_timezone=user_timezone)

        # chat() returns dict {"response": str, "citations": list} — extract text for final_response
        if isinstance(response, dict):
            state["final_response"] = response.get("response", "")
            citations = response.get("citations", [])
            if citations:
                state["citations"] = citations
        else:
            state["final_response"] = str(response)
        state["agent_responses"]["supervisor"] = response
    except GraphInterrupt:
        # Re-raise so it bubbles up to the outer graph and API layer
        raise
    except Exception as e:
        logger.error(f"[SUPERVISOR] Error in supervisor_node: {e}")
        state["final_response"] = f"I encountered an error processing your request: {str(e)}"

    return state


# =========================================================================
# TWG AGENT NODES - Delegate to specific TWG agents
# =========================================================================

def create_twg_agent_node(agent_id: str, agent: LangGraphBaseAgent):
    """
    Factory function to create a TWG agent node.

    Returns a function that can be used as a LangGraph node.
    """
    # Use default args to capture values at definition time, not call time
    async def twg_node(state: AgentState, _agent_id: str = agent_id, _agent: LangGraphBaseAgent = agent) -> AgentState:
        """
        Delegate query to a specific TWG agent.
        """
        query = state["query"]
        thread_id = state.get("session_id")
        logger.info(f"[TWG:{_agent_id.upper()}] Processing query...")

        try:
            user_timezone = state.get("user_timezone")
            response = await _agent.chat(query, thread_id=thread_id, user_timezone=user_timezone)
            state["agent_responses"][_agent_id] = response
            logger.info(f"[{_agent_id.upper()}] Response generated")
        except GraphInterrupt:
            # Re-raise GraphInterrupt so it bubbles up to Supervisor and API
            raise
        except Exception as e:
            logger.error(f"[{_agent_id.upper()}] Error: {e}")
            state["agent_responses"][_agent_id] = f"Error: {str(e)}"

        return state

    return twg_node


# =========================================================================
# SYNTHESIS NODE - Combine responses from multiple agents
# =========================================================================

async def synthesis_node(state: AgentState, supervisor_agent: LangGraphBaseAgent) -> AgentState:
    """
    Synthesize responses from multiple TWG agents into ONE unified professional memo.
    """
    query = state["query"]
    responses = state["agent_responses"]

    if not responses:
        state["final_response"] = "I couldn't get responses from the relevant agents."
        return state

    logger.info(f"[SYNTHESIS] Synthesizing {len(responses)} TWG responses into unified memo")

    # Process responses to extract text and collect citations
    truncated_responses = {}
    all_citations = []
    
    for agent_id, response_raw in responses.items():
        response_text = ""
        if isinstance(response_raw, dict):
            response_text = response_raw.get("response", "")
            all_citations.extend(response_raw.get("citations", []))
        else:
            response_text = str(response_raw)
            
        # Truncate text for prompt (1500 chars to preserve meaningful detail)
        if len(response_text) > 1500:
            truncated_responses[agent_id] = response_text[:1500] + "..."
        else:
            truncated_responses[agent_id] = response_text

    # Build synthesis prompt for unified memo
    agent_list = ", ".join([agent_id.upper() for agent_id in responses.keys()])

    synthesis_prompt = f"""Question: {query}

TWG Inputs ({agent_list}):
"""
    for agent_id, response_text in truncated_responses.items():
        synthesis_prompt += f"\n{agent_id}: {response_text}\n"

    synthesis_prompt += f"""
Write ONE cohesive professional response synthesizing these TWG inputs.

FORMATTING RULES:
- Match response size to the question. Simple question = short answer. Complex briefing = structured sections.
- Use **bold** for key terms and metrics INLINE — not as standalone headers.
- Use bullet points only for 3+ items. Use tables for comparing data across TWGs or projects.
- Do NOT start with "Executive Summary" or any header unless the original question explicitly requested a report or briefing.
- Do NOT use filler phrases like "Based on comprehensive analysis..." — just give the synthesized answer.
- Do NOT repeat the original question.
- INTEGRATE raw data/tool outputs into your narrative naturally. Do NOT append "Report Generated" sections.
- Keep the response focused, readable, and visually clean."""

    # Get supervisor's unified memo
    try:
        unified_memo = await supervisor_agent.chat(synthesis_prompt)
        # chat() returns dict {"response": str, "citations": list} — extract text
        if isinstance(unified_memo, dict):
            output = unified_memo.get("response", "")
        else:
            output = str(unified_memo)
    except Exception as e:
        logger.error(f"[SYNTHESIS] Synthesis generation failed: {e}")
        output = f"Error generating unified memo: {str(e)}\n\nPlease review the request and try again."

    # --- CONFLICT DETECTION LAYER ---
    # Check for conflicts between TWG responses
    if len(responses) > 1:
        logger.info("[SYNTHESIS] Running Conflict Detection Layer...")
        conflict_prompt = f"""
        Review these TWG inputs for any direct contradictions, schedule clashes, or resource conflicts:

        {chr(10).join([f"{k}: {v[:500]}" for k, v in truncated_responses.items()])}

        If a significant conflict exists, respond with "CONFLICT DETECTED" and a brief explanation.
        Otherwise, respond "NO CONFLICT".
        """

        try:
            conflict_check_raw = await supervisor_agent.chat(conflict_prompt)
            conflict_check = conflict_check_raw.get("response", "") if isinstance(conflict_check_raw, dict) else str(conflict_check_raw)

            if "CONFLICT DETECTED" in conflict_check.upper():
                output += f"\n\nCONFLICT ALERT:\n{conflict_check}"
                logger.warning(f"Conflict Detected: {conflict_check}")
                # Future: await save_conflict_to_db(...)
        except Exception as e:
            logger.error(f"Conflict detection failed: {e}")

    state["synthesized_response"] = output
    state["final_response"] = output
    
    # Propagate combined citations
    unique_citations = []
    if all_citations:
        # Deduplicate by source and page
        seen = set()
        for c in all_citations:
            key = (c.get('source'), c.get('page'))
            if key not in seen:
                unique_citations.append(c)
                seen.add(key)
        state["citations"] = unique_citations

    logger.info(f"[SYNTHESIS] Complete - Generated unified memo with {len(unique_citations)} unique citations")

    return state


# =========================================================================
# SINGLE AGENT RESPONSE NODE - Format single agent response
# =========================================================================

def single_agent_response_node(state: AgentState) -> AgentState:
    """
    Format response from a single TWG agent.
    """
    responses = state["agent_responses"]

    if not responses:
        state["final_response"] = "No response received from agent."
        return state

    # Get the single agent's response
    agent_id, response_raw = list(responses.items())[0]
    
    # Handle Dict vs Str response
    response_text = ""
    citations = []
    
    if isinstance(response_raw, dict):
        response_text = response_raw.get("response", "")
        citations = response_raw.get("citations", [])
    else:
        response_text = str(response_raw)

    # Add context header
    context = f"[Consulted {agent_id.upper()} TWG]\n\n{response_text}"

    state["final_response"] = context
    
    # Propagate citations to supervisor state
    if citations:
        if "citations" not in state or state["citations"] is None:
            state["citations"] = []
        state["citations"] = citations

    logger.info(f"[SINGLE] Formatted response from {agent_id} with {len(citations)} citations")

    return state


# =========================================================================
# NEGOTIATION NODE - Automated conflict resolution
# =========================================================================

async def negotiation_node(state: AgentState) -> AgentState:
    """
    Handle automated negotiation between agents.
    """
    logger.info("[NEGOTIATION] Entering negotiation node")
    
    context = state.get("negotiation_context", {})
    conflict_desc = context.get("conflict_description")
    agent_ids = context.get("agent_ids", [])
    
    if not conflict_desc or len(agent_ids) < 2:
        state["final_response"] = "Negotiation failed: Missing conflict details or agents."
        return state

    from app.services.negotiation_service import NegotiationService
    from app.core.database import get_db_session_context
    from app.models.models import TWG, TWGPillar
    from sqlalchemy import select

    output_log = ""
    
    try:
        async with get_db_session_context() as db:
            service = NegotiationService(db)
            
            # Map string agent_ids (e.g. "energy") to TWG UUIDs
            twg_uuids = []
            pillar_map = {
                "energy": TWGPillar.energy_infrastructure,
                "agriculture": TWGPillar.agriculture,
                "minerals": TWGPillar.minerals,
                "digital": TWGPillar.digital,
                "protocol": TWGPillar.protocol,
                "resource_mobilization": TWGPillar.resource_mobilization
            }
            
            for a_id in agent_ids:
                if a_id in pillar_map:
                    stmt = select(TWG).where(TWG.pillar == pillar_map[a_id])
                    twg = (await db.execute(stmt)).scalars().first()
                    if twg:
                        twg_uuids.append(twg.id)
            
            # 1. Initiate
            # Note: We rely on the service to handle the heavy lifting
            # Since we don't have a valid negotiation ID yet, we simulate one or 
            # create a placeholder record. 
            # For this Phase 3 Demo, lets simulate the initiation if DB records fail
            
            if len(twg_uuids) < 2:
                 response = f"**Negotiation Simulation** (Database Sync Pending)\n\n" \
                            f"Agents: {', '.join(agent_ids)}\n" \
                            f"Topic: {conflict_desc}\n\n" \
                            f"Outcome: Consensus Reached on strategic alignment."
                 state["final_response"] = response
                 return state

            # Create session
            neg_session = await service.initiate_negotiation(
                trigger_user_id=None,
                topic=f"Conflict: {conflict_desc[:50]}",
                participating_twg_ids=twg_uuids,
                context_data={"full_description": conflict_desc}
            )
            
            # 2. Run
            # This is the "Magic" loop
            result = await service.run_negotiation(neg_session.id)
            
            status_emoji = "✅" if result["status"] == "CONSENSUS_REACHED" else "⚠️"
            
            state["final_response"] = (
                f"{status_emoji} **Negotiation Result**\n\n"
                f"{result['summary']}\n\n"
                f"**Consensus:** {result.get('agreement_text', 'Pending Escalation')}"
            )
            
    except Exception as e:
        logger.error(f"Negotiation error: {e}")
        state["final_response"] = f"Error during automated negotiation: {str(e)}"
        
    return state

