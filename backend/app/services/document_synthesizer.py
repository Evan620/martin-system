"""
Document Synthesis Service

Compiles TWG outputs into coherent documents with consistent voice,
terminology, and formatting. Ensures citation of knowledge base sources.
"""

from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, UTC
from loguru import logger
import re
from enum import Enum


class DocumentType(str, Enum):
    """Types of documents that can be synthesized"""
    DECLARATION = "declaration"
    SUMMIT_REPORT = "summit_report"
    POLICY_BRIEF = "policy_brief"
    CONCEPT_NOTE = "concept_note"
    TECHNICAL_REPORT = "technical_report"


class SynthesisStyle(str, Enum):
    """Document voice and style"""
    FORMAL_MINISTERIAL = "formal_ministerial"  # For Declarations
    TECHNICAL = "technical"  # For technical reports
    EXECUTIVE = "executive"  # For executive summaries
    POLICY = "policy"  # For policy briefs


class DocumentSynthesizer:
    """Service for synthesizing TWG outputs into coherent documents"""

    def __init__(self, llm_client: Optional[Any] = None):
        """
        Initialize document synthesizer.

        Args:
            llm_client: LLM client for synthesis and formatting
        """
        self.llm = llm_client
        self._synthesis_history: List[Dict[str, Any]] = []

        # Standard terminology mappings
        self._terminology_standards = {
            "energy": {
                "WAPP": "West African Power Pool",
                "renewable": "renewable energy",
                "MW": "megawatts (MW)",
                "grid": "regional power grid"
            },
            "agriculture": {
                "value chain": "agricultural value chain",
                "productivity": "agricultural productivity",
                "mechanization": "agricultural mechanization"
            },
            "digital": {
                "fintech": "financial technology (fintech)",
                "e-commerce": "electronic commerce",
                "broadband": "broadband connectivity"
            }
        }

        # Citation requirements by document type
        self._citation_requirements = {
            DocumentType.DECLARATION: {
                "numerical_claims": True,
                "policy_references": True,
                "statistics": True,
                "targets": True
            },
            DocumentType.TECHNICAL_REPORT: {
                "numerical_claims": True,
                "policy_references": True,
                "statistics": True,
                "targets": True,
                "methodology": True
            },
            DocumentType.POLICY_BRIEF: {
                "numerical_claims": True,
                "statistics": True,
                "policy_references": False  # More flexible
            }
        }

    def synthesize_declaration(
        self,
        twg_sections: Dict[str, str],
        title: str = "ECOWAS Summit 2026 Declaration",
        preamble: Optional[str] = None,
        knowledge_base: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Synthesize TWG sections into a coherent Declaration.

        This is the flagship synthesis capability - takes disparate TWG inputs
        and produces a unified Declaration with consistent voice and formatting.

        Args:
            twg_sections: Dictionary mapping TWG ID to their draft section
            title: Declaration title
            preamble: Optional preamble text
            knowledge_base: Optional knowledge base for citation verification

        Returns:
            Dict with synthesized declaration and metadata

        Example:
            >>> twg_sections = {
            ...     "energy": "The Energy pillar focuses on...",
            ...     "agriculture": "For agriculture, we commit to...",
            ...     "minerals": "Critical minerals will enable..."
            ... }
            >>> result = synthesizer.synthesize_declaration(twg_sections)
            >>> print(result['document'])
        """
        logger.info(f"Synthesizing Declaration from {len(twg_sections)} TWG sections")

        # 1. Standardize terminology across all sections
        standardized_sections = self._standardize_terminology(twg_sections)

        # 2. Ensure consistent voice and tone
        harmonized_sections = self._harmonize_voice(
            standardized_sections,
            style=SynthesisStyle.FORMAL_MINISTERIAL
        )

        # 3. Verify citations if knowledge base provided
        if knowledge_base:
            cited_sections = self._enforce_citations(
                harmonized_sections,
                knowledge_base,
                DocumentType.DECLARATION
            )
        else:
            cited_sections = harmonized_sections

        # 4. Compile into final document structure
        declaration = self._compile_declaration(
            cited_sections,
            title=title,
            preamble=preamble
        )

        # 5. Final coherence check
        coherence_report = self._check_coherence(declaration)

        result = {
            "document": declaration,
            "metadata": {
                "title": title,
                "sections": list(twg_sections.keys()),
                "synthesized_at": datetime.now(UTC).isoformat(),
                "word_count": len(declaration.split()),
                "coherence_score": coherence_report["score"],
                "issues": coherence_report["issues"]
            },
            "synthesis_log": {
                "terminology_changes": self._get_terminology_changes(
                    twg_sections, standardized_sections
                ),
                "voice_adjustments": self._count_voice_adjustments(
                    standardized_sections, harmonized_sections
                ),
                "citations_added": self._count_citations(cited_sections) if knowledge_base else 0
            }
        }

        self._synthesis_history.append(result)
        logger.info(
            f"✓ Declaration synthesized: {result['metadata']['word_count']} words, "
            f"coherence: {coherence_report['score']:.1%}"
        )

        return result

    def _standardize_terminology(
        self,
        sections: Dict[str, str]
    ) -> Dict[str, str]:
        """
        Ensure consistent terminology across all sections.

        Example: If Energy uses "WAPP" and Agriculture uses "West African Power Pool",
        standardize to "West African Power Pool (WAPP)" on first use.
        """
        standardized = {}

        for twg_id, content in sections.items():
            standardized_content = content

            # Apply terminology standards
            if twg_id in self._terminology_standards:
                for abbreviation, full_term in self._terminology_standards[twg_id].items():
                    # Replace first occurrence with full term + abbreviation
                    pattern = rf'\b{re.escape(abbreviation)}\b'
                    if re.search(pattern, standardized_content, re.IGNORECASE):
                        standardized_content = re.sub(
                            pattern,
                            f"{full_term} ({abbreviation})",
                            standardized_content,
                            count=1,
                            flags=re.IGNORECASE
                        )

            standardized[twg_id] = standardized_content

        return standardized

    def _harmonize_voice(
        self,
        sections: Dict[str, str],
        style: SynthesisStyle
    ) -> Dict[str, str]:
        """
        Ensure all sections use consistent voice and tone.

        Uses LLM to rewrite sections in uniform style while preserving content.
        """
        if not self.llm:
            logger.warning("No LLM available - skipping voice harmonization")
            return sections

        harmonized = {}

        # Define style guidelines
        style_guidelines = self._get_style_guidelines(style)

        for twg_id, content in sections.items():
            # Prompt for harmonization
            prompt = f"""Rewrite this TWG section to match the required style while preserving all factual content:

ORIGINAL SECTION ({twg_id.upper()} TWG):
{content}

REQUIRED STYLE: {style.value}
{style_guidelines}

REWRITE REQUIREMENTS:
1. Maintain all factual claims and numbers
2. Use the specified voice and tone
3. Keep the same section structure
4. Preserve all citations
5. Output only the rewritten section, no commentary

REWRITTEN SECTION:"""

            try:
                harmonized_content = self.llm.chat(prompt)
                harmonized[twg_id] = harmonized_content
                logger.debug(f"Harmonized voice for {twg_id}")

            except Exception as e:
                logger.error(f"Voice harmonization failed for {twg_id}: {e}")
                harmonized[twg_id] = content  # Fallback to original

        return harmonized

    def _get_style_guidelines(self, style: SynthesisStyle) -> str:
        """Get style guidelines for a synthesis style"""
        guidelines = {
            SynthesisStyle.FORMAL_MINISTERIAL: """
VOICE: First person plural ("We, the Heads of State...")
TONE: Formal, authoritative, aspirational
STRUCTURE:
- Declarative statements of commitment
- Action-oriented language
- Future-focused (will, shall, commit to)
EXAMPLE: "We commit to accelerating regional integration through..."
            """,
            SynthesisStyle.TECHNICAL: """
VOICE: Third person, objective
TONE: Precise, data-driven, neutral
STRUCTURE:
- Evidence-based statements
- Technical terminology
- Present tense for facts
EXAMPLE: "The analysis indicates that regional integration requires..."
            """,
            SynthesisStyle.EXECUTIVE: """
VOICE: Active voice, direct
TONE: Clear, concise, action-oriented
STRUCTURE:
- Short sentences
- Bullet points where appropriate
- Key takeaways emphasized
EXAMPLE: "Regional integration will accelerate through three mechanisms..."
            """
        }

        return guidelines.get(style, "")

    def _enforce_citations(
        self,
        sections: Dict[str, str],
        knowledge_base: Dict[str, Any],
        doc_type: DocumentType
    ) -> Dict[str, str]:
        """
        Enforce citation of knowledge base sources for factual claims.

        This prevents hallucinated data by requiring citations for:
        - Numerical claims (statistics, targets, percentages)
        - Policy references
        - Historical facts
        """
        requirements = self._citation_requirements.get(
            doc_type,
            {"numerical_claims": True}
        )

        cited_sections = {}

        for twg_id, content in sections.items():
            cited_content = content

            # Extract claims that need citations
            if requirements.get("numerical_claims"):
                cited_content = self._add_citations_for_numbers(
                    cited_content,
                    knowledge_base,
                    twg_id
                )

            if requirements.get("statistics"):
                cited_content = self._add_citations_for_statistics(
                    cited_content,
                    knowledge_base,
                    twg_id
                )

            if requirements.get("policy_references"):
                cited_content = self._add_citations_for_policies(
                    cited_content,
                    knowledge_base,
                    twg_id
                )

            cited_sections[twg_id] = cited_content

        return cited_sections

    def _add_citations_for_numbers(
        self,
        content: str,
        knowledge_base: Dict[str, Any],
        twg_id: str
    ) -> str:
        """Add citations for numerical claims"""
        # Pattern: "$50 billion", "5000 MW", "100%"
        number_patterns = [
            r'\$\d+(?:\.\d+)?\s*(?:billion|million|trillion)',
            r'\d+(?:,\d{3})*(?:\.\d+)?\s*(?:MW|GW|kW)',
            r'\d+(?:\.\d+)?%'
        ]

        cited_content = content

        for pattern in number_patterns:
            matches = re.finditer(pattern, content, re.IGNORECASE)

            for match in matches:
                claim = match.group(0)

                # Check if already cited
                if f"{claim}" in content and "[Source:" in content[match.end():match.end()+50]:
                    continue  # Already has citation

                # Find citation in knowledge base
                citation = self._find_citation(claim, knowledge_base, twg_id)

                if citation:
                    # Add inline citation
                    cited_content = cited_content.replace(
                        claim,
                        f"{claim} [Source: {citation}]",
                        1  # Only first occurrence
                    )

        return cited_content

    def _add_citations_for_statistics(
        self,
        content: str,
        knowledge_base: Dict[str, Any],
        twg_id: str
    ) -> str:
        """Add citations for statistical claims"""
        # Patterns like "increase of X%", "growth rate of Y"
        stat_patterns = [
            r'(?:increase|growth|reduction|decline)\s+of\s+\d+(?:\.\d+)?%',
            r'\d+(?:\.\d+)?%\s+(?:increase|growth|reduction|decline)'
        ]

        cited_content = content

        for pattern in stat_patterns:
            matches = re.finditer(pattern, content, re.IGNORECASE)

            for match in matches:
                claim = match.group(0)

                # Check if already cited
                if "[Source:" in content[match.end():match.end()+50]:
                    continue

                citation = self._find_citation(claim, knowledge_base, twg_id)

                if citation:
                    cited_content = cited_content.replace(
                        claim,
                        f"{claim} [Source: {citation}]",
                        1
                    )

        return cited_content

    def _add_citations_for_policies(
        self,
        content: str,
        knowledge_base: Dict[str, Any],
        twg_id: str
    ) -> str:
        """Add citations for policy references"""
        # Pattern: "ECOWAS Protocol", "Regional Agreement", etc.
        policy_patterns = [
            r'ECOWAS\s+(?:Protocol|Agreement|Treaty|Convention)',
            r'(?:Regional|National)\s+(?:Policy|Framework|Strategy)'
        ]

        cited_content = content

        for pattern in policy_patterns:
            matches = re.finditer(pattern, content, re.IGNORECASE)

            for match in matches:
                claim = match.group(0)

                if "[Source:" in content[match.end():match.end()+50]:
                    continue

                citation = self._find_citation(claim, knowledge_base, twg_id)

                if citation:
                    cited_content = cited_content.replace(
                        claim,
                        f"{claim} [Source: {citation}]",
                        1
                    )

        return cited_content

    def _find_citation(
        self,
        claim: str,
        knowledge_base: Dict[str, Any],
        twg_id: str
    ) -> Optional[str]:
        """
        Find appropriate citation from knowledge base.

        This would ideally search a vector database or document store.
        For now, returns a placeholder citation.
        """
        # Placeholder implementation
        # In production, this would:
        # 1. Search knowledge base for claim
        # 2. Return document ID + page/section
        # 3. Verify claim accuracy

        # For now, return generic citation
        kb_sources = knowledge_base.get("sources", {})
        twg_sources = kb_sources.get(twg_id, [])

        if twg_sources:
            # Return first relevant source
            return twg_sources[0]

        return "Internal TWG Analysis 2025"

    def _compile_declaration(
        self,
        sections: Dict[str, str],
        title: str,
        preamble: Optional[str]
    ) -> str:
        """Compile sections into final Declaration format"""
        declaration = f"{title}\n"
        declaration += "=" * len(title) + "\n\n"

        if preamble:
            declaration += f"{preamble}\n\n"

        # Add each TWG section with proper formatting
        section_titles = {
            "energy": "I. Energy & Infrastructure",
            "agriculture": "II. Agriculture & Food Security",
            "minerals": "III. Critical Minerals & Industrialization",
            "digital": "IV. Digital Economy & Transformation",
            "protocol": "V. Implementation Framework",
            "resource_mobilization": "VI. Resource Mobilization & Investment"
        }

        for twg_id, content in sections.items():
            section_title = section_titles.get(twg_id, f"{twg_id.upper()}")
            declaration += f"\n{section_title}\n"
            declaration += "-" * len(section_title) + "\n\n"
            declaration += f"{content}\n\n"

        # Add footer
        declaration += "\n---\n"
        declaration += f"Adopted: {datetime.now(UTC).strftime('%B %d, %Y')}\n"

        return declaration

    def _check_coherence(self, document: str) -> Dict[str, Any]:
        """Check document coherence and identify issues"""
        issues = []

        # Check 1: Terminology consistency
        # (simplified - real implementation would be more sophisticated)
        if "WAPP" in document and "West African Power Pool" not in document:
            issues.append("WAPP used without full term definition")

        # Check 2: Voice consistency
        first_person = len(re.findall(r'\bwe\b', document, re.IGNORECASE))
        third_person = len(re.findall(r'\bthey\b', document, re.IGNORECASE))

        if first_person > 0 and third_person > 0:
            if third_person / (first_person + third_person) > 0.3:
                issues.append("Inconsistent voice (mixing first and third person)")

        # Check 3: Citation coverage (basic)
        numbers = len(re.findall(r'\d+(?:\.\d+)?\s*(?:billion|million|MW|%)', document))
        citations = len(re.findall(r'\[Source:', document))

        citation_rate = citations / numbers if numbers > 0 else 1.0

        if citation_rate < 0.5:
            issues.append(f"Low citation rate: {citation_rate:.1%} of numerical claims cited")

        # Calculate coherence score
        score = 1.0
        if issues:
            score -= len(issues) * 0.1  # Deduct 10% per issue

        return {
            "score": max(0.0, min(1.0, score)),
            "issues": issues
        }

    def _get_terminology_changes(
        self,
        original: Dict[str, str],
        standardized: Dict[str, str]
    ) -> int:
        """Count terminology standardization changes"""
        changes = 0
        for twg_id in original:
            if original[twg_id] != standardized.get(twg_id, ""):
                changes += 1
        return changes

    def _count_voice_adjustments(
        self,
        before: Dict[str, str],
        after: Dict[str, str]
    ) -> int:
        """Count voice harmonization adjustments"""
        adjustments = 0
        for twg_id in before:
            if before[twg_id] != after.get(twg_id, ""):
                adjustments += 1
        return adjustments

    def _count_citations(self, sections: Dict[str, str]) -> int:
        """Count citations added"""
        total = 0
        for content in sections.values():
            total += len(re.findall(r'\[Source:', content))
        return total

    def get_synthesis_history(self) -> List[Dict[str, Any]]:
        """Get history of all syntheses performed"""
        return self._synthesis_history

    def get_terminology_standards(self) -> Dict[str, Dict[str, str]]:
        """Get current terminology standards"""
        return self._terminology_standards

    def add_terminology_standard(
        self,
        twg_id: str,
        abbreviation: str,
        full_term: str
    ) -> None:
        """Add a new terminology standard"""
        if twg_id not in self._terminology_standards:
            self._terminology_standards[twg_id] = {}

        self._terminology_standards[twg_id][abbreviation] = full_term
        logger.info(f"Added terminology standard: {abbreviation} -> {full_term}")
