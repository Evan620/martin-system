"""
Conflict Detection Service

Analyzes TWG outputs to detect conflicts, overlaps, and contradictions.
Triggers automated negotiation or escalation as needed.
"""

from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, UTC
from loguru import logger
import re

from app.schemas.broadcast_messages import (
    ConflictAlert,
    NegotiationRequest,
    create_conflict_alert,
    create_negotiation_request
)


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
            "policy_targets": {
                "description": "Contradictory policy targets or goals",
                "keywords": [
                    "target", "goal", "%", "by 2026", "by 2030",
                    "achieve", "reach", "increase", "reduce"
                ],
                "severity": "high"
            },
            "resource_allocation": {
                "description": "Competing resource allocation needs",
                "keywords": [
                    "budget", "funding", "investment", "allocation",
                    "priority", "million", "billion"
                ],
                "severity": "medium"
            },
            "session_overlap": {
                "description": "Overlapping or conflicting session proposals",
                "keywords": [
                    "session", "panel", "presentation", "workshop",
                    "same time", "concurrent", "parallel"
                ],
                "severity": "low"
            },
            "policy_direction": {
                "description": "Contradictory policy directions",
                "keywords": [
                    "must", "should", "require", "mandate",
                    "prohibit", "ban", "allow", "permit"
                ],
                "severity": "high"
            },
            "technology_choice": {
                "description": "Incompatible technology recommendations",
                "keywords": [
                    "technology", "platform", "standard", "protocol",
                    "system", "infrastructure"
                ],
                "severity": "medium"
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
                conflict_type="policy_target",
                severity="high",
                agents_involved=[agent_a, agent_b],
                description=f"{agent_a.upper()} promotes renewable energy targets while {agent_b.upper()} includes fossil fuel infrastructure",
                conflicting_positions={
                    agent_a: "Renewable energy focus",
                    agent_b: "Includes fossil fuel infrastructure"
                },
                impact="Policy inconsistency may confuse investors and member states",
                urgency="high",
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
            return create_conflict_alert(
                conflict_type=pattern_type,
                severity=pattern_config["severity"],
                agents_involved=[agent_a, agent_b],
                description=f"Potential {pattern_config['description']} between {agent_a} and {agent_b}",
                conflicting_positions={
                    agent_a: " ".join(sentences_a[:2]),
                    agent_b: " ".join(sentences_b[:2])
                },
                impact=f"May cause confusion in {pattern_type} coordination",
                urgency="medium",
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

If conflicts exist, respond with:
CONFLICT: [type]
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
            severity = "medium"
            description = "Conflict detected by LLM"
            impact = "Needs review"

            for line in response.split('\n'):
                if line.startswith("CONFLICT:"):
                    conflict_type = line.split(":", 1)[1].strip()
                elif line.startswith("SEVERITY:"):
                    severity = line.split(":", 1)[1].strip().lower()
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
                urgency="medium",
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
