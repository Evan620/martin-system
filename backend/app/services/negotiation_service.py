"""
Negotiation Service

Facilitates automated negotiation between TWG agents to resolve conflicts.
Refactored to support:
- Database integration (Conflict model)
- Counter-proposal logic
- Multi-round debate
- Context-aware resource trading
"""

from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timezone
UTC = timezone.utc
from loguru import logger
from uuid import UUID
import json

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.models.models import Conflict, ConflictStatus, Meeting, User, TWG, MeetingParticipant
from app.services.llm_service import get_llm_service

class NegotiationService:
    """
    Orchestrates "True AI Multi-Agent Negotiation" (Debate Pattern).
    
    Instead of just voting on pre-defined options, this service facilitates 
    a counter-proposal loop where agents can:
    1. Reject proposals with specific reasons (constraints).
    2. Offer conditional compromises ("I'll move if you give me the Main Hall").
    """

    def __init__(self, db: AsyncSession):
        self.db = db
        self.llm_service = get_llm_service()

    async def initiate_negotiation(
        self,
        trigger_user_id: Optional[UUID],
        topic: str,
        participating_twg_ids: List[UUID],
        context_data: Dict[str, Any]
    ) -> Conflict:
        """
        Start a new negotiation. Creates or updates a Conflict record.
        """
        # 1. Resolve TWG names
        # We need names for the agents_involved list
        stmt = select(TWG).where(TWG.id.in_(participating_twg_ids))
        twgs = (await self.db.execute(stmt)).scalars().all()
        agent_names = [twg.pillar.value for twg in twgs] # e.g. "energy_infrastructure"
        
        # 2. Check if active conflict exists for this topic?
        # For now, always create a new one or use the one passed in context if available
        conflict_id = context_data.get("conflict_id")
        
        if conflict_id:
            stmt = select(Conflict).where(Conflict.id == UUID(conflict_id))
            conflict = (await self.db.execute(stmt)).scalar_one_or_none()
            if conflict:
                # Reset status if needed
                if conflict.status in [ConflictStatus.RESOLVED, ConflictStatus.DISMISSED]:
                    conflict.status = ConflictStatus.NEGOTIATING
                    conflict.resolution_log = (conflict.resolution_log or []) + [{
                        "action": "reopened",
                        "timestamp": datetime.utcnow().isoformat()
                    }]
                return conflict
        
        # Create new Conflict record if not found
        import uuid
        new_conflict = Conflict(
            id=uuid.uuid4(),
            conflict_type="schedule_clash", # default, can be updated
            severity="medium",
            description=topic,
            agents_involved=agent_names,
            conflicting_positions=context_data.get("positions", {}),
            status=ConflictStatus.NEGOTIATING,
            metadata_json={"twg_ids": [str(t.id) for t in twgs], **context_data}
        )
        self.db.add(new_conflict)
        await self.db.flush()
        return new_conflict

    async def run_negotiation(self, conflict_id: UUID, max_rounds: int = 4, user_feedback: str = None, apply_immediately: bool = True) -> Dict[str, Any]:
        """
        Run the multi-round negotiation loop.
        Args:
            user_feedback: Optional instructions from the user to guide the agents (e.g. "Don't move the Keynote").
            apply_immediately: If True, executes the resolution on consensus. If False, marks as PENDING_APPROVAL.
        """
        stmt = select(Conflict).where(Conflict.id == conflict_id)
        conflict = (await self.db.execute(stmt)).scalar_one_or_none()
        
        if not conflict:
            raise ValueError(f"Conflict {conflict_id} not found")
        
        # Resolve agent UUIDs to TWG names for human-readable output
        agent_names = {}
        for agent_id in conflict.agents_involved:
            try:
                twg_stmt = select(TWG).where(TWG.id == UUID(agent_id))
                twg = (await self.db.execute(twg_stmt)).scalar_one_or_none()
                if twg:
                    agent_names[agent_id] = twg.name
                else:
                    agent_names[agent_id] = agent_id  # Fallback to ID if not found
            except:
                agent_names[agent_id] = agent_id  # Fallback for non-UUID strings
        
        # Load Context (Meetings, VIPs, etc.)
        context_str = await self._build_deep_context(conflict)
        
        # Inject User Feedback if provided (The "HITL" prompt)
        if user_feedback:
            context_str += f"\n\n[USER INSTRUCTION]: {user_feedback}\nMake sure your proposals respect this instruction."
        
        # Negotiation State
        round_num = 1
        history = []
        
        # Start the Loop
        while round_num <= max_rounds:
            logger.info(f"🔄 Negotiation Round {round_num} for {conflict_id}")
            
            # 1. Generate Proposals / Counter-Proposals (using UUIDs internally)
            proposals_raw = await self._generate_agent_proposals(conflict, context_str, history)
            
            # Map to human-readable names for history
            proposals = {agent_names.get(agent_id, agent_id): text for agent_id, text in proposals_raw.items()}
            
            # Log this round
            round_entry = {
                "round": round_num,
                "timestamp": datetime.utcnow().isoformat(),
                "proposals": proposals
            }
            history.append(round_entry)
            
            # 2. Supervisor Analysis
            analysis = await self._supervisor_analyze(conflict, context_str, history)
            
            if analysis.get("has_consensus"):
                logger.info(f"✅ Consensus Reached in Round {round_num}")
                await self._finalize_resolution(conflict, analysis, history, apply=apply_immediately)
                return {
                    "status": "CONSENSUS_REACHED",
                    "rounds": round_num,
                    "overview": {
                        "history": history,
                        "agreement_text": analysis.get("agreement_text"),
                        "summary": f"Resolved in {round_num} rounds.",
                        "status": "auto_resolved" if apply_immediately else "pending_approval"
                    }
                }         # 3. Guidance for next round (updated into context)
            guidance = analysis.get("guidance", "Please try to find a middle ground.")
            context_str += f"\n\n[SUPERVISOR GUIDANCE]: {guidance}"
            
            round_num += 1
            
        # If loop finishes without consensus
        proposals_considered = await self._escalate_conflict(conflict, history)
        return {
            "status": "ESCALATED",
            "rounds": max_rounds,
            "proposals_considered": proposals_considered,
            "overview": {
                "history": history,
                "agreement_text": None,
                "summary": "Max rounds reached without consensus.",
                "status": "escalated"
            }
        }

    async def _build_deep_context(self, conflict: Conflict) -> str:
        """
        Fetch DB Objects (Meetings, Profiles) to give the LLM 'Reasoning Power'.
        """
        context = f"CONFLICT: {conflict.description}\n"
        
        # Extract meeting IDs from metadata/positions
        # Assuming positions format: {'agent_name': {'meeting_id': 'uuid'}}
        # or metadata: {'meeting_ids': ['uuid', 'uuid']}
        meeting_ids = []
        
        # Look in metadata first (more reliable if we populate it)
        if conflict.metadata_json and "meeting_ids" in conflict.metadata_json:
             meeting_ids = conflict.metadata_json["meeting_ids"]
        
        # Use positions as fallback
        elif conflict.conflicting_positions:
             for pos in conflict.conflicting_positions.values():
                 if isinstance(pos, dict) and "meeting_id" in pos:
                     meeting_ids.append(pos["meeting_id"])
                 elif isinstance(pos, str) and len(pos) == 36: # simple uuid check
                     meeting_ids.append(pos)

        if meeting_ids:
            # Query DB
            stmt = select(Meeting).where(
                Meeting.id.in_([UUID(mid) for mid in meeting_ids])
            ).options(
                selectinload(Meeting.participants).selectinload(MeetingParticipant.user).selectinload(User.vip_profile),
                selectinload(Meeting.twg)
            )
            res = (await self.db.execute(stmt)).scalars().all()
            
            context += "\nINVOLVED EVENTS:\n"
            for m in res:
                vip_names = [
                    f"{p.user.full_name} ({p.user.vip_profile.title})" 
                    for p in m.participants 
                    if p.user and p.user.vip_profile
                ]
                context += f"- '{m.title}' (ID: {m.id})\n  Owner: {m.twg.name} TWG\n"
                context += f"  Time: {m.scheduled_at}\n"
                context += f"  Location: {m.location}\n"
                context += f"  VIPs: {', '.join(vip_names) if vip_names else 'None'}\n"
                context += f"  Duration: {m.duration_minutes} mins\n\n"
                
        return context

    async def _generate_agent_proposals(self, conflict: Conflict, context: str, history: List[Dict]) -> Dict[str, str]:
        """
        Ask each agent for their move.
        """
        proposals = {}
        
        history_text = ""
        if history:
            history_text = "\nNEGOTIATION HISTORY:\n"
            for h in history:
                history_text += f"\nRound {h['round']}:\n"
                for agent, prop in h['proposals'].items():
                    history_text += f"  {agent}: {prop}\n"
        
        # Deduplicate agents (handle internal conflicts where Agent A = Agent B)
        # Use set to unique, then sort to ensure deterministic order
        unique_agents = sorted(list(set(conflict.agents_involved)))
        
        for agent_name in unique_agents:
            # Persona Prompt
            system_prompt = f"""You are the {agent_name} TWG Agent for the ECOWAS Summit.
You are in a high-stakes negotiation to resolve a conflict.

Your Goal:
1. Protect your key constraints (VIPs, deadlines).
2. BE CREATIVE. Propose specific trades (e.g. "I move to 4pm if I get the big room").
3. Seeking solution. Do not just say "No". Offer "Yes, if...".

IMPORTANT: When referring to meetings, use their TITLES (e.g. "Food Systems Workshop"), NOT their IDs.

CONTEXT:
{context}

{history_text}
"""
            user_prompt = "What is your proposal for this round? (Be concise, 1-2 sentences. Use meeting titles, not IDs.)"
            
            try:
                response = self.llm_service.chat(
                    prompt=user_prompt,
                    system_prompt=system_prompt
                )
                proposals[agent_name] = response
            except Exception as e:
                logger.error(f"Agent {agent_name} failed to propose: {e}")
                proposals[agent_name] = "Abstain due to error."
                
        return proposals

    async def _supervisor_analyze(self, conflict: Conflict, context: str, history: List[Dict]) -> Dict[str, Any]:
        """
        The Supervisor judges if the latest proposals converge.
        """
        last_round = history[-1]
        
        system_prompt = """You are the Secretariat Martin (Supervisor).
Review the latest negotiation proposals.
Determine if CONSENSUS has been reached.

Consensus Rules:
- All parties successfully agreed to a specific plan.
- Or one party conceded and the other accepted.
- No "open questions" remain.
- SINGLE AGENT CASE: If there is only one agent involved (internal conflict) and they propose a concrete, valid resolution (e.g. "I will move my meeting"), that IS CONSENSUS.

Output JSON:
{
    "has_consensus": boolean,
    "agreement_text": "text summary of the deal" or null,
    "structured_resolution": {
        "type": "shift_time" | "change_venue" | "cancel" | "no_action",
        "meeting_id": "UUID of the meeting to change",
        "new_value": "YYYY-MM-DDTHH:MM:SS" (for time) OR "Venue Name" (for venue)
    } (or null if no consensus),
    "guidance": "advice for next round if not resolved"
}
"""
        user_prompt = f"""CONTEXT:
{context}

LATEST ROUND PROPOSALS:
{json.dumps(last_round['proposals'], indent=2)}
"""
        response = self.llm_service.chat(
            prompt=user_prompt,
            system_prompt=system_prompt
        )
        
        # Parse JSON
        try:
            # Clean markdown code blocks if any
            clean_res = response.replace("```json", "").replace("```", "").strip()
            # Find JSON braces
            start = clean_res.find('{')
            end = clean_res.rfind('}') + 1
            if start >= 0 and end > start:
                 return json.loads(clean_res[start:end])
            return json.loads(clean_res)
        except Exception:
            logger.warning(f"Failed to parse Supervisor JSON: {response}")
            return {"has_consensus": False, "guidance": "Keep talking."}

    async def _finalize_resolution(self, conflict: Conflict, analysis: Dict[str, Any], history: List[Dict], apply: bool = True):
        """
        Save the win and APPLY the changes (or mark for approval).
        """
        action_log = {}
        structured_action = analysis.get("structured_resolution")

        if apply:
            # 1. Apply the resolution IMMEDIATELY
            if structured_action:
                 try:
                     action_log = await self._apply_resolution_action(structured_action)
                 except Exception as e:
                     logger.error(f"Failed to apply resolution action: {e}")
                     action_log = {"error": str(e)}
            
            conflict.status = ConflictStatus.RESOLVED
            conflict.resolved_at = datetime.utcnow()
        else:
            # 2. Defer application (Pending Approval)
            conflict.status = ConflictStatus.PENDING_APPROVAL
            # Store pending action in metadata so we can execute it later
            if not conflict.metadata_json:
                conflict.metadata_json = {}
            conflict.metadata_json["pending_resolution"] = structured_action
            conflict.metadata_json["pending_agreement_text"] = analysis.get("agreement_text")
            action_log = {"status": "pending_approval", "reason": "human_in_loop"}

        # 3. Update Conflict Record
        conflict.resolution_log = (conflict.resolution_log or []) + [{
            "action": "resolved_via_debate" if apply else "negotiation_concluded_pending_approval",
            "agreement": analysis.get("agreement_text"),
            "structured_action": structured_action,
            "action_result": action_log,
            "history": history,
            "timestamp": datetime.utcnow().isoformat()
        }]
        await self.db.commit()

    async def _apply_resolution_action(self, action: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute the changes in the database and notify participants.
        """
        from app.services.resolution_notifier import ResolutionNotifier
        
        res_type = action.get("type")
        meeting_id = action.get("meeting_id")
        new_value = action.get("new_value")
        
        if not meeting_id or not res_type:
            return {"status": "skipped", "reason": "missing_params"}

        # Validate meeting_id is a valid UUID
        try:
            meeting_uuid = UUID(meeting_id)
        except (ValueError, AttributeError):
            return {"status": "failed", "reason": f"invalid_meeting_id: '{meeting_id}' is not a valid UUID"}

        stmt = select(Meeting).where(Meeting.id == meeting_uuid)
        meeting = (await self.db.execute(stmt)).scalar_one_or_none()
        
        if not meeting:
            return {"status": "failed", "reason": "meeting_not_found"}
            
        old_value = ""
        notification_result = {}
        notifier = ResolutionNotifier(self.db)
        
        if res_type == "shift_time":
            try:
                # Parse ISO format
                new_dt = datetime.fromisoformat(new_value.replace('Z', '+00:00'))
                # Remove timezone info to match DB (TIMESTAMP WITHOUT TIME ZONE)
                if new_dt.tzinfo is not None:
                    new_dt = new_dt.replace(tzinfo=None)
                
                old_dt = meeting.scheduled_at
                old_value = str(old_dt)
                meeting.scheduled_at = new_dt
                
                # Notify participants of the reschedule
                notification_result = await notifier.notify_meeting_rescheduled(
                    meeting=meeting,
                    old_time=old_dt,
                    new_time=new_dt
                )
            except ValueError as e:
                 return {"status": "failed", "reason": f"invalid_date_format: {e}"}
                 
        elif res_type == "change_venue":
            old_venue = meeting.location
            old_value = old_venue
            meeting.location = new_value
            
            # Notify participants of venue change
            notification_result = await notifier.notify_meeting_venue_changed(
                meeting=meeting,
                old_venue=old_venue,
                new_venue=new_value
            )
            
        elif res_type == "cancel":
            old_value = str(meeting.status)
            meeting.status = "cancelled"
            
            # Notify participants of cancellation
            notification_result = await notifier.notify_meeting_cancelled(
                meeting=meeting,
                reason="Resolved via AI conflict negotiation"
            )
            
        return {
            "status": "applied", 
            "type": res_type, 
            "old": old_value, 
            "new": new_value,
            "notifications": notification_result
        }

    async def _escalate_conflict(self, conflict: Conflict, history: List[Dict]) -> List[Dict[str, str]]:
        """
        Give up and call a human.
        Analyze history to suggest "Unresolved Options" for the human to consider.
        """
        conflict.status = ConflictStatus.ESCALATED
        conflict.human_action_required = True
        
        # Generative Step: Ask Supervisor to summarize valid options from the debate
        proposals_considered = []
        try:
            history_text = "\n".join([
                f"Round {h['round']}: {json.dumps(h['proposals'])}" 
                for h in history
            ])
            
            system_prompt = """You are the Secretariat Martin (Supervisor).
The negotiation between agents has FAILED (escalated).
Your job is to summarize the 2-3 most viable "Proposals Considered" that the human user could choose to manually enforce.

Analyze the negotiation history. Identify specific, concrete options that were discussed or would make sense.
            
Output JSON format:
[
    {
        "id": "option_1",
        "action": "Move [Meeting Name] to [Time]...",
        "rationale": "Agent A proposed this, but Agent B rejected it due to [Reason]. Human can override."
    },
    ...
]
"""
            user_prompt = f"Negotiation History:\n{history_text}\n\nList the best unresolved options for the human."
            
            response = self.llm_service.chat(prompt=user_prompt, system_prompt=system_prompt)
            
            # Clean and Parse
            clean_res = response.replace("```json", "").replace("```", "").strip()
            start = clean_res.find('[')
            end = clean_res.rfind(']') + 1
            if start >= 0 and end > start:
                 proposals_considered = json.loads(clean_res[start:end])
            else:
                 # Fallback if no array found
                 proposals_considered = json.loads(clean_res)
                 
        except Exception as e:
            logger.warning(f"Failed to generate escalation options: {e}")
            proposals_considered = []

        conflict.resolution_log = (conflict.resolution_log or []) + [{
            "action": "escalated_max_rounds",
            "history": history,
            "proposals_considered": proposals_considered,
            "timestamp": datetime.utcnow().isoformat()
        }]
        await self.db.commit()
        
        return proposals_considered

    async def apply_pending_resolution(self, conflict_id: UUID) -> Dict[str, Any]:
        """
        Apply a resolution that was negotiated but deferred for approval.
        """
        stmt = select(Conflict).where(Conflict.id == conflict_id)
        conflict = (await self.db.execute(stmt)).scalar_one_or_none()
        
        if not conflict:
             raise ValueError("Conflict not found")
        
        # Check metadata for pending resolution
        action = None
        if conflict.metadata_json:
            action = conflict.metadata_json.get("pending_resolution")
        
        if not action:
             return {"status": "failed", "reason": "no_pending_resolution"}
             
        # Apply
        log = await self._apply_resolution_action(action)
        
        conflict.status = ConflictStatus.RESOLVED
        conflict.resolved_at = datetime.utcnow()
        conflict.resolution_log = (conflict.resolution_log or []) + [{
             "action": "user_approved_pending_resolution",
             "result": log,
             "timestamp": datetime.utcnow().isoformat()
        }]
        
        # Clear pending flag
        if conflict.metadata_json:
            conflict.metadata_json.pop("pending_resolution", None)
            
        await self.db.commit()
        return log
