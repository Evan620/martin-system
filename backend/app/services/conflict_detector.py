"""
Conflict Detection Service

Analyzes TWG outputs to detect conflicts, overlaps, and contradictions.
Triggers automated negotiation or escalation as needed.
"""

from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timezone
UTC = timezone.utc
from loguru import logger
import re
import json

from app.schemas.broadcast_messages import (
    ConflictAlert,
    NegotiationRequest,
    create_conflict_alert,
    create_negotiation_request
)
from app.models.models import Document
from app.core.database import get_db_session_context
from sqlalchemy import select, and_, or_
from datetime import timedelta
import math

from app.models.models import Project, Conflict, ConflictType, ConflictSeverity, ConflictStatus, Conflict
from app.core.knowledge_base import get_knowledge_base
from app.services.llm_service import get_llm_service


class ConflictDetector:
    """Service for detecting conflicts between TWG outputs"""

    def __init__(self, llm_client: Optional[Any] = None):
        """
        Initialize conflict detector.

        Args:
            llm_client: Optional LLM client for semantic analysis
        """
        self.llm = llm_client
        self._conflict_history: List[ConflictAlert] = []
        self._negotiation_history: List[NegotiationRequest] = []

        # Conflict detection rules
        self._conflict_patterns = self._initialize_conflict_patterns()

    def _initialize_conflict_patterns(self) -> Dict[str, Any]:
        """Initialize conflict detection patterns"""
        return {
            ConflictType.POLICY_MISALIGNMENT.value: {
                "description": "Contradictory policy targets or goals",
                "keywords": [
                    "target", "goal", "%", "by 2026", "by 2030",
                    "achieve", "reach", "increase", "reduce"
                ],
                "severity": "HIGH"
            },
            ConflictType.RESOURCE_CONSTRAINT.value: {
                "description": "Competing resource allocation needs",
                "keywords": [
                    "budget", "funding", "investment", "allocation",
                    "priority", "million", "billion"
                ],
                "severity": "MEDIUM"
            },
            ConflictType.SCHEDULE_CLASH.value: {
                "description": "Overlapping or conflicting session proposals",
                "keywords": [
                    "session", "panel", "presentation", "workshop",
                    "same time", "concurrent", "parallel"
                ],
                "severity": "LOW"
            },
            # Merging policy direction into MISALIGNMENT but keeping unique keywords could be tricky if keys must be unique.
            # I will assume we can reuse the type OR I should have reduced the patterns.
            # But wait, keys need to be unique for the iteration.
            # So I will keep unique keys and map them to Enum *Types* separately.
            "policy_direction": {
                "type": ConflictType.POLICY_MISALIGNMENT.value,
                "description": "Contradictory policy directions",
                "keywords": [
                    "must", "should", "require", "mandate",
                    "prohibit", "ban", "allow", "permit"
                ],
                "severity": "HIGH"
            },
            "technology_choice": {
                "type": ConflictType.POLICY_MISALIGNMENT.value,
                "description": "Incompatible technology recommendations",
                "keywords": [
                    "technology", "platform", "standard", "protocol",
                    "system", "infrastructure"
                ],
                "severity": "MEDIUM"
            }
        }

    def detect_conflicts(
        self,
        twg_outputs: Dict[str, str]
    ) -> List[ConflictAlert]:
        """
        Detect conflicts across TWG outputs.

        Args:
            twg_outputs: Dictionary mapping agent_id to their output text

        Returns:
            List of detected conflicts
        """
        conflicts = []

        # 1. Pattern-based conflict detection
        pattern_conflicts = self._detect_pattern_conflicts(twg_outputs)
        conflicts.extend(pattern_conflicts)

        # 2. Target number conflicts (e.g., "100% renewables" vs "coal for smelting")
        target_conflicts = self._detect_target_conflicts(twg_outputs)
        conflicts.extend(target_conflicts)

        # 3. Semantic conflicts (using LLM if available)
        if self.llm:
            semantic_conflicts = self._detect_semantic_conflicts(twg_outputs)
            conflicts.extend(semantic_conflicts)

        # Store in history
        self._conflict_history.extend(conflicts)

        return conflicts

    def _detect_pattern_conflicts(
        self,
        twg_outputs: Dict[str, str]
    ) -> List[ConflictAlert]:
        """Detect conflicts using keyword patterns"""
        conflicts = []

        # Compare each pair of TWG outputs
        agent_ids = list(twg_outputs.keys())
        for i in range(len(agent_ids)):
            for j in range(i + 1, len(agent_ids)):
                agent_a = agent_ids[i]
                agent_b = agent_ids[j]

                output_a = twg_outputs[agent_a].lower()
                output_b = twg_outputs[agent_b].lower()

                # Check each conflict pattern
                for pattern_type, pattern_config in self._conflict_patterns.items():
                    keywords = pattern_config["keywords"]

                    # Both outputs mention keywords from this pattern
                    matches_a = [kw for kw in keywords if kw in output_a]
                    matches_b = [kw for kw in keywords if kw in output_b]

                    if matches_a and matches_b:
                        # Potential conflict - verify with deeper analysis
                        conflict = self._analyze_potential_conflict(
                            agent_a, agent_b,
                            output_a, output_b,
                            pattern_type, pattern_config,
                            matches_a, matches_b
                        )

                        if conflict:
                            conflicts.append(conflict)

        return conflicts

    def _detect_target_conflicts(
        self,
        twg_outputs: Dict[str, str]
    ) -> List[ConflictAlert]:
        """Detect conflicts in numerical targets"""
        conflicts = []

        # Extract targets from each output
        targets_by_agent = {}
        for agent_id, output in twg_outputs.items():
            targets = self._extract_targets(output)
            targets_by_agent[agent_id] = targets

        # Compare targets for conflicts
        # Example: Energy says "100% renewable by 2030"
        #          Minerals says "coal-fired smelting plants"
        agent_ids = list(targets_by_agent.keys())
        for i in range(len(agent_ids)):
            for j in range(i + 1, len(agent_ids)):
                agent_a = agent_ids[i]
                agent_b = agent_ids[j]

                # Check for contradictory targets
                conflict = self._check_target_contradiction(
                    agent_a, targets_by_agent[agent_a],
                    agent_b, targets_by_agent[agent_b]
                )

                if conflict:
                    conflicts.append(conflict)

        return conflicts

    def _extract_targets(self, text: str) -> List[Dict[str, Any]]:
        """Extract numerical targets and goals from text"""
        targets = []

        # Pattern: "X% renewable by YEAR"
        percent_pattern = r'(\d+)%\s+(\w+)(?:\s+by\s+(\d{4}))?'
        for match in re.finditer(percent_pattern, text, re.IGNORECASE):
            targets.append({
                "value": match.group(1),
                "unit": "%",
                "subject": match.group(2),
                "year": match.group(3),
                "full_text": match.group(0)
            })

        # Pattern: "X MW/GW of power"
        power_pattern = r'(\d+(?:\.\d+)?)\s*(MW|GW|kW)(?:\s+of\s+(\w+))?'
        for match in re.finditer(power_pattern, text, re.IGNORECASE):
            targets.append({
                "value": match.group(1),
                "unit": match.group(2),
                "subject": match.group(3) or "power",
                "full_text": match.group(0)
            })

        # Pattern: "$X million/billion investment"
        money_pattern = r'\$(\d+(?:\.\d+)?)\s*(million|billion)(?:\s+(\w+))?'
        for match in re.finditer(money_pattern, text, re.IGNORECASE):
            targets.append({
                "value": match.group(1),
                "unit": match.group(2),
                "subject": match.group(3) or "investment",
                "full_text": match.group(0)
            })

        return targets

    def _check_target_contradiction(
        self,
        agent_a: str,
        targets_a: List[Dict[str, Any]],
        agent_b: str,
        targets_b: List[Dict[str, Any]]
    ) -> Optional[ConflictAlert]:
        """Check if targets from two agents contradict"""
        # Example logic for renewable energy vs coal
        # This is a simplified check - real implementation would be more sophisticated

        renewable_keywords = ["renewable", "solar", "wind", "green"]
        fossil_keywords = ["coal", "gas", "fossil", "petroleum"]

        has_renewable_a = any(
            any(kw in str(t.get("subject", "")).lower() for kw in renewable_keywords)
            for t in targets_a
        )
        has_fossil_b = any(
            any(kw in str(t.get("subject", "")).lower() for kw in fossil_keywords)
            for t in targets_b
        )

        if has_renewable_a and has_fossil_b:
            # Potential conflict detected
            return create_conflict_alert(
                conflict_type=ConflictType.POLICY_MISALIGNMENT.value,
                severity="HIGH",
                agents_involved=[agent_a, agent_b],
                description=f"{agent_a.upper()} promotes renewable energy targets while {agent_b.upper()} includes fossil fuel infrastructure",
                conflicting_positions={
                    agent_a: "Renewable energy focus",
                    agent_b: "Includes fossil fuel infrastructure"
                },
                impact="Policy inconsistency may confuse investors and member states",
                urgency="HIGH",
                suggested_resolution="Clarify energy mix strategy or phase-out timeline for fossil fuels",
                requires_negotiation=True,
                requires_human_intervention=False
            )

        return None

    def _analyze_potential_conflict(
        self,
        agent_a: str,
        agent_b: str,
        output_a: str,
        output_b: str,
        pattern_type: str,
        pattern_config: Dict[str, Any],
        matches_a: List[str],
        matches_b: List[str]
    ) -> Optional[ConflictAlert]:
        """Analyze a potential conflict in detail"""
        # Extract relevant sentences
        sentences_a = self._extract_relevant_sentences(output_a, matches_a)
        sentences_b = self._extract_relevant_sentences(output_b, matches_b)

        # Simple heuristic: if both mention contradictory terms, flag as conflict
        # In real implementation, this would use LLM for deeper analysis

        if sentences_a and sentences_b:
            # Determine correct enum type
            c_type = pattern_config.get("type", pattern_type)
            # If pattern_type (the key) is already a valid enum value, usage is fine.
            # But if we used a custom key like "policy_direction", we must use the mapped type.
            
            return create_conflict_alert(
                conflict_type=c_type,
                severity=pattern_config["severity"],
                agents_involved=[agent_a, agent_b],
                description=f"Potential {pattern_config['description']} between {agent_a} and {agent_b}",
                conflicting_positions={
                    agent_a: " ".join(sentences_a[:2]),
                    agent_b: " ".join(sentences_b[:2])
                },
                impact=f"May cause confusion in {pattern_type} coordination",
                urgency="MEDIUM",
                requires_negotiation=True
            )

        return None

    def _extract_relevant_sentences(
        self,
        text: str,
        keywords: List[str]
    ) -> List[str]:
        """Extract sentences containing keywords"""
        sentences = text.split('.')
        relevant = []

        for sentence in sentences:
            if any(kw in sentence.lower() for kw in keywords):
                relevant.append(sentence.strip())

        return relevant

    def _detect_semantic_conflicts(
        self,
        twg_outputs: Dict[str, str]
    ) -> List[ConflictAlert]:
        """
        Detect semantic conflicts using LLM analysis.

        This is the most powerful conflict detection method.
        """
        if not self.llm:
            return []

        conflicts = []

        # Compare each pair of outputs
        agent_ids = list(twg_outputs.keys())
        for i in range(len(agent_ids)):
            for j in range(i + 1, len(agent_ids)):
                agent_a = agent_ids[i]
                agent_b = agent_ids[j]

                # Ask LLM to analyze for conflicts
                prompt = f"""Analyze these two TWG outputs for conflicts or contradictions:

TWG A ({agent_a.upper()}):
{twg_outputs[agent_a][:500]}

TWG B ({agent_b.upper()}):
{twg_outputs[agent_b][:500]}

Identify any:
1. Contradictory policy positions
2. Conflicting targets or goals
3. Incompatible recommendations
4. Resource allocation conflicts
5. Duplicate or redundant sessions/workshops
6. Implicit dependencies where one TWG relies on another (e.g., "requires input from Energy") without a clear link.

If conflicts or issues exist, respond with:
CONFLICT: [type] (types: policy_clash, target_mismatch, duplicate_session, missing_dependency, resource_conflict)
SEVERITY: [critical/high/medium/low]
DESCRIPTION: [clear description]
IMPACT: [what this affects]

If no conflicts, respond with: NO CONFLICT
"""

                try:
                    response = self.llm.chat(prompt)

                    if "CONFLICT:" in response:
                        # Parse LLM response and create conflict alert
                        conflict = self._parse_llm_conflict_response(
                            response, agent_a, agent_b,
                            twg_outputs[agent_a], twg_outputs[agent_b]
                        )
                        if conflict:
                            conflicts.append(conflict)

                except Exception as e:
                    logger.error(f"LLM conflict detection failed: {e}")

        return conflicts

    def _parse_llm_conflict_response(
        self,
        response: str,
        agent_a: str,
        agent_b: str,
        output_a: str,
        output_b: str
    ) -> Optional[ConflictAlert]:
        """Parse LLM's conflict detection response"""
        try:
            # Extract conflict details from response
            conflict_type = "unknown"
            severity = "MEDIUM"
            description = "Conflict detected by LLM"
            impact = "Needs review"

            for line in response.split('\n'):
                if line.startswith("CONFLICT:"):
                    raw_type = line.split(":", 1)[1].strip().upper()
                    # Map LLM output to valid ENUM
                    type_map = {
                        "POLICY_CLASH": ConflictType.POLICY_MISALIGNMENT.value,
                        "TARGET_MISMATCH": ConflictType.POLICY_MISALIGNMENT.value,
                        "DUPLICATE_SESSION": ConflictType.SCHEDULE_CLASH.value, 
                        "MISSING_DEPENDENCY": ConflictType.DEPENDENCY_BLOCKER.value,
                        "RESOURCE_CONFLICT": ConflictType.RESOURCE_CONSTRAINT.value,
                        # Fallback for direct match
                        "SCHEDULE_CLASH": ConflictType.SCHEDULE_CLASH.value,
                        "POLICY_MISALIGNMENT": ConflictType.POLICY_MISALIGNMENT.value,
                        "RESOURCE_CONSTRAINT": ConflictType.RESOURCE_CONSTRAINT.value
                    }
                    conflict_type = type_map.get(raw_type, ConflictType.POLICY_MISALIGNMENT.value) # Default safe
                elif line.startswith("SEVERITY:"):
                    severity = line.split(":", 1)[1].strip().upper()
                elif line.startswith("DESCRIPTION:"):
                    description = line.split(":", 1)[1].strip()
                elif line.startswith("IMPACT:"):
                    impact = line.split(":", 1)[1].strip()

            return create_conflict_alert(
                conflict_type=conflict_type,
                severity=severity,
                agents_involved=[agent_a, agent_b],
                description=description,
                conflicting_positions={
                    agent_a: output_a[:200],
                    agent_b: output_b[:200]
                },
                impact=impact,
                urgency="MEDIUM",
                requires_negotiation=True
            )

        except Exception as e:
            logger.error(f"Failed to parse LLM conflict response: {e}")
            return None

    def get_conflict_summary(self) -> Dict[str, Any]:
        """Get summary of all detected conflicts"""
        total = len(self._conflict_history)
        by_severity = {}
        by_type = {}
        by_status = {}

        for conflict in self._conflict_history:
            # Count by severity
            severity = conflict.severity
            by_severity[severity] = by_severity.get(severity, 0) + 1

            # Count by type
            ctype = conflict.conflict_type
            by_type[ctype] = by_type.get(ctype, 0) + 1

            # Count by status
            status = conflict.status
            by_status[status] = by_status.get(status, 0) + 1

        return {
            "total_conflicts": total,
            "by_severity": by_severity,
            "by_type": by_type,
            "by_status": by_status,
            "unresolved": by_status.get("pending", 0) + by_status.get("in_negotiation", 0)
        }

    def get_conflicts(
        self,
        status: Optional[str] = None,
        severity: Optional[str] = None,
        agents: Optional[List[str]] = None
    ) -> List[ConflictAlert]:
        """
        Get conflicts with optional filtering.

        Args:
            status: Filter by status (pending, resolved, etc.)
            severity: Filter by severity (critical, high, medium, low)
            agents: Filter by involved agents

        Returns:
            List of matching conflicts
        """
        conflicts = self._conflict_history

        if status:
            conflicts = [c for c in conflicts if c.status == status]

        if severity:
            conflicts = [c for c in conflicts if c.severity == severity]

        if agents:
            conflicts = [
                c for c in conflicts
                if any(a in c.agents_involved for a in agents)
            ]

        return conflicts

    async def check_new_document(self, new_doc: Document) -> List[ConflictAlert]:
        """
        Real-time semantic check when document is created/updated.
        Compares against ALL other TWGs' recent policy documents.
        """
        logger.info(f"Checking for conflicts with new document: {new_doc.file_name} ({new_doc.twg_id})")
        conflicts = []
        
        async with get_db_session_context() as db:
            try:
                # Get other TWGs' recent policy docs (last 30 days)
                # We need to filter by document type if available, but for now we look at all
                # excluding the current TWG
                stmt = select(Document).where(
                    and_(
                        Document.twg_id != new_doc.twg_id,
                        Document.created_at >= datetime.now(UTC) - timedelta(days=30)
                    )
                ).order_by(Document.created_at.desc())
                
                result = await db.execute(stmt)
                other_docs = result.scalars().all()
                
                logger.debug(f"Comparing against {len(other_docs)} other documents")
                
                for other_doc in other_docs:
                    # Construct text content proxy
                    # Ideally we fetch content from file storage or vector DB
                    # Here we use file_name + metadata as available
                    new_content = new_doc.file_name
                    if new_doc.metadata_json:
                        new_content += f" {str(new_doc.metadata_json)}"
                        
                    other_content = other_doc.file_name
                    if other_doc.metadata_json:
                         other_content += f" {str(other_doc.metadata_json)}"
                         
                    # Check for conflicts using existing logic
                    # We pass TWG IDs (or names if resolved)
                    # For now using IDs as keys
                    twg_outputs = {
                        str(new_doc.twg_id): new_content,
                        str(other_doc.twg_id): other_content
                    }
                    
                    found_conflicts = self.detect_conflicts(twg_outputs)
                    
                    if found_conflicts:
                        conflicts.extend(found_conflicts)
                        
            except Exception as e:
                logger.error(f"Error in check_new_document: {e}")
                
        # Store results
        if conflicts:
            self._conflict_history.extend(conflicts)
            
        return conflicts

    async def detect_project_dependency_conflicts(self, db: Any) -> List[Conflict]:
        """
        Scans project descriptions for dependency indicators using LLM semantic analysis.
        """
        # Get active projects
        result = await db.execute(select(Project).where(Project.status.not_in(["completed", "cancelled"])))
        projects = result.scalars().all()
        
        conflicts = []
        llm = get_llm_service()
        
        # Compare each project pair
        # Limit to recent/relevant pairs to avoid N^2 explosion in prod (or batch)
        # For prototype, we do N^2 but with simple checks first
        
        for i, project_a in enumerate(projects):
            for project_b in projects[i+1:]:
                # Only check if in different pillars/TWGs or explicitly requested
                if project_a.id == project_b.id:
                    continue
                
                # Ask LLM to analyze dependency
                prompt = f"""
                Analyze if Project A depends on Project B:
                
                PROJECT A:
                Name: {project_a.name}
                Description: {project_a.description}
                Sector: {project_a.pillar}
                
                PROJECT B:
                Name: {project_b.name}
                Description: {project_b.description}
                Sector: {project_b.pillar}
                
                Does Project A require Project B to be completed first?
                
                Return VALID JSON ONLY:
                {{
                    "has_dependency": boolean,
                    "dependency_type": "infrastructure|policy|financing|technical|none",
                    "confidence": 0.0-1.0,
                    "reason": "explanation",
                    "estimated_delay_days": integer (0 if no dependency)
                }}
                """
                
                try:
                    analysis_str = llm.chat(prompt, max_tokens=500)
                    # Clean json
                    if "```json" in analysis_str:
                        analysis_str = analysis_str.split("```json")[1].split("```")[0].strip()
                    elif "```" in analysis_str:
                         analysis_str = analysis_str.split("```")[1].split("```")[0].strip()
                         
                    analysis = json.loads(analysis_str)
                    
                    if analysis.get("has_dependency") and analysis.get("confidence", 0) > 0.7:
                        
                        # Determine severity based on delay and type
                        delay = analysis.get("estimated_delay_days", 0)
                        severity = ConflictSeverity.LOW
                        if delay > 180: severity = ConflictSeverity.CRITICAL
                        elif delay > 90: severity = ConflictSeverity.HIGH
                        elif delay > 30: severity = ConflictSeverity.MEDIUM
                        
                        # Create conflict (in memory, caller saves)
                        meta = {
                            "dependent_project_id": str(project_a.id),
                            "prerequisite_project_id": str(project_b.id),
                            "dependency_type": analysis.get("dependency_type"),
                            "confidence": analysis.get("confidence"),
                            "reason": analysis.get("reason"),
                            "estimated_delay_days": delay
                        }
                        
                        conflicts.append(Conflict(
                            conflict_type=ConflictType.PROJECT_DEPENDENCY_CONFLICT,
                            severity=severity,
                            agents_involved=[str(project_a.twg_id), str(project_b.twg_id)],
                            description=f"Dependency: '{project_a.name}' depends on '{project_b.name}' ({analysis.get('reason')})",
                            conflicting_positions={
                                "dependent": f"{project_a.name} (Start: {project_a.metadata_json.get('planned_start', 'TBD') if project_a.metadata_json else 'TBD'})",
                                "prerequisite": f"{project_b.name} (End: {project_b.metadata_json.get('planned_end', 'TBD') if project_b.metadata_json else 'TBD'})"
                            },
                            metadata_json=meta,
                            status=ConflictStatus.DETECTED,
                            detected_at=datetime.utcnow()
                        ))
                except Exception as e:
                    logger.error(f"Error analyzing project dependency: {e}")
                    
        return conflicts

    async def detect_duplicate_projects(self, db: Any) -> List[Conflict]:
        """
        Finds when two or more TWGs are proposing essentially the same project using embeddings.
        """
        result = await db.execute(select(Project).where(Project.status.not_in(["completed", "cancelled"])))
        projects = result.scalars().all()
        
        conflicts = []
        kb = get_knowledge_base()
        
        # Generate embeddings for all project descriptions
        embeddings_cache = {}
        for project in projects:
            combined_text = f"{project.name} {project.description} {project.pillar or ''}"
            # Batching would be better, but assuming low volume for now
            try:
                emb = kb.generate_embeddings([combined_text])[0]
                embeddings_cache[project.id] = emb
            except Exception as e:
                logger.error(f"Failed to embed project {project.id}: {e}")
        
        # Compare pairs
        for i, project_a in enumerate(projects):
            for project_b in projects[i+1:]:
                # Skip if same TWG (internal dupes handled differently usually, but let's check widely)
                if project_a.twg_id == project_b.twg_id:
                     continue
                     
                if project_a.id not in embeddings_cache or project_b.id not in embeddings_cache:
                    continue
                    
                # Cosine Similarity
                similarity = self._cosine_similarity(embeddings_cache[project_a.id], embeddings_cache[project_b.id])
                
                if similarity > 0.75:
                    action = "DIFFERENTIATE"
                    severity = ConflictSeverity.MEDIUM
                    
                    if similarity > 0.95:
                        severity = ConflictSeverity.CRITICAL
                        action = "MERGE"
                    elif similarity > 0.85:
                        severity = ConflictSeverity.HIGH
                        action = "REVIEW"
                        
                    # Check Geography
                    geo_match = (project_a.lead_country == project_b.lead_country)
                    
                    conflicts.append(Conflict(
                        conflict_type=ConflictType.DUPLICATE_PROJECT_CONFLICT,
                        severity=severity,
                        agents_involved=[str(project_a.twg_id), str(project_b.twg_id)],
                        description=f"Potential Duplicate: '{project_a.name}' vs '{project_b.name}' (Similarity: {similarity:.2f})",
                        conflicting_positions={
                            "project_a": f"{project_a.name} ({project_a.pillar})",
                            "project_b": f"{project_b.name} ({project_b.pillar})"
                        },
                        metadata_json={
                            "project_a_id": str(project_a.id),
                            "project_b_id": str(project_b.id),
                            "similarity_score": round(similarity, 3),
                            "suggested_action": action,
                            "geo_match": geo_match
                        },
                        status=ConflictStatus.DETECTED,
                        human_action_required=True,
                        detected_at=datetime.utcnow()
                    ))
                    
        return conflicts

    async def detect_live_conflict(self, chunk_text: str, context: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Sub-second check for conflicts in a live transcript chunk.
        Checks against current context (other TWG targets).
        """
        if not self.llm:
            return None

        # Short, aggressive prompt for real-time feedback
        prompt = f"""
        LIVE MEETING MONITOR:
        Meeting Context: {context.get('twg_name', 'General')} - {context.get('meeting_title', 'Meeting')}
        Transcript Segment: "{chunk_text}"
        
        CRITICAL TASK: Does this statement conflict with known ECOWAS policies or other TWG targets (e.g., Energy vs Environment)?
        
        If CONFLICT exists, return VALID JSON:
        {{
            "is_conflict": true,
            "severity": "high|medium|low",
            "reason": "short explanation",
            "suggestion": "what to say to the chair"
        }}
        Otherwise return: {{"is_conflict": false}}
        """
        
        try:
            # Note: We should ideally use a very fast model here
            response_str = self.llm.chat(prompt, max_tokens=200)
            
            # Clean json
            if "```json" in response_str:
                response_str = response_str.split("```json")[1].split("```")[0].strip()
            elif "```" in response_str:
                 response_str = response_str.split("```")[1].split("```")[0].strip()
                 
            analysis = json.loads(response_str)
            if analysis.get("is_conflict"):
                return analysis
        except Exception as e:
            logger.error(f"Live conflict detection failed: {e}")
            
        return None

    async def analyze_live_agenda(self, chunk_text: str, agenda_content: str, context: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Proactively analyze a transcript chunk to track agenda progress and decisions.
        """
        if not self.llm:
            return None

        prompt = f"""
        LIVE AGENDA MONITOR:
        Meeting: {context.get('meeting_title', 'General')}
        Official Agenda: {agenda_content}
        
        Transcript Chunk: "{chunk_text}"
        
        TASK:
        1. Identify what is currently being discussed (Current Focus).
        2. Extract any explicit decisions reached in this chunk.
        3. Determine which agenda item(s) are being covered or were just completed.
        
        Return VALID JSON:
        {{
            "current_focus": "string (short)",
            "decisions": ["string"],
            "completed_items_indices": [integer (0-based)],
            "insight_summary": "string (very short summary of the chunk action)"
        }}
        
        Rules:
        - If no clear focus or decision, return null for those fields.
        - indices refer to the bullets in the Official Agenda starting from 0.
        """

        try:
            response_str = self.llm.chat(prompt, max_tokens=300)
            
            # Clean json
            if "```json" in response_str:
                response_str = response_str.split("```json")[1].split("```")[0].strip()
            elif "```" in response_str:
                 response_str = response_str.split("```")[1].split("```")[0].strip()
                 
            analysis = json.loads(response_str)
            return analysis
        except Exception as e:
            logger.error(f"Live agenda analysis failed: {e}")
            return None

    def _cosine_similarity(self, v1: List[float], v2: List[float]) -> float:
        """Calculate cosine similarity between two vectors"""
        dot_product = sum(a * b for a, b in zip(v1, v2))
        norm_v1 = math.sqrt(sum(a * a for a in v1))
        norm_v2 = math.sqrt(sum(b * b for b in v2))
        if norm_v1 == 0 or norm_v2 == 0:
            return 0.0
        return dot_product / (norm_v1 * norm_v2) 

