"""
Document Pipeline Service

Orchestrates total document production for the ECOWAS Summit system.
Manages the lifecycle of documents from Zero Draft to Final version,
coordinating synthesis across TWG agents.
"""

from typing import Dict, List, Optional, Any
from datetime import datetime, timezone
UTC = timezone.utc
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
import uuid

from app.models.models import Document, TWG, WeeklyPacket
from app.services.document_synthesizer import DocumentSynthesizer, DocumentType
from app.services.llm_service import get_llm_service
from app.services.audit_service import audit_service


class DocumentVersion:
    """Document version stages"""
    ZERO_DRAFT = 0
    FIRST_DRAFT = 1
    FINAL = 2


class DocumentPipelineService:
    """
    Service for orchestrating document production pipeline.
    
    Manages:
    - Declaration synthesis from TWG sections
    - Document versioning (Zero Draft -> First Draft -> Final)
    - Milestone-triggered document generation
    """

    def __init__(self, db: AsyncSession):
        """
        Initialize document pipeline service.

        Args:
            db: Async database session
        """
        self.db = db
        self.synthesizer = DocumentSynthesizer(llm_client=get_llm_service())

    async def trigger_declaration_synthesis(
        self,
        milestone: str,
        title: str = "ECOWAS Summit 2026 Declaration",
        preamble: Optional[str] = None,
        triggered_by_user_id: Optional[uuid.UUID] = None
    ) -> Dict[str, Any]:
        """
        Trigger auto-compilation of Declaration document.

        Args:
            milestone: The milestone that triggered this synthesis (e.g., "phase_completion", "weekly_update")
            title: Title for the declaration
            preamble: Optional preamble text
            triggered_by_user_id: User ID who triggered this (for audit logging)

        Returns:
            Dict containing:
                - document: The synthesized document record
                - synthesis_result: Metadata about the synthesis process
                - version: The version number of this document
        """
        logger.info(f"Triggering declaration synthesis for milestone: {milestone}")

        twg_sections = await self._gather_twg_sections()

        if not twg_sections:
            logger.warning("No TWG sections available for synthesis")
            return {
                "document": None,
                "synthesis_result": None,
                "version": None,
                "error": "No TWG sections available for synthesis"
            }

        synthesis_result = self.synthesizer.synthesize_declaration(
            twg_sections=twg_sections,
            title=title,
            preamble=preamble
        )

        latest_version = await self._get_latest_declaration_version(title)
        new_version = latest_version + 1 if latest_version is not None else DocumentVersion.ZERO_DRAFT

        parent_document_id = None
        if latest_version is not None:
            parent_doc = await self._get_latest_declaration(title)
            if parent_doc:
                parent_document_id = parent_doc.id

        document = Document(
            file_name=f"{title.replace(' ', '_')}_v{new_version}.md",
            file_path=f"declarations/{title.replace(' ', '_')}_v{new_version}.md",
            file_type="text/markdown",
            uploaded_by_id=triggered_by_user_id or uuid.UUID("00000000-0000-0000-0000-000000000000"),
            version=new_version,
            parent_document_id=parent_document_id,
            metadata_json={
                "milestone": milestone,
                "synthesized_at": datetime.now(UTC).isoformat(),
                "title": title,
                "coherence_score": synthesis_result["metadata"]["coherence_score"],
                "word_count": synthesis_result["metadata"]["word_count"],
                "sections": synthesis_result["metadata"]["sections"],
                "document_type": DocumentType.DECLARATION.value,
                "synthesis_log": synthesis_result["synthesis_log"]
            },
            category="declaration",
            scope=["all_twg", "secretariat"],
            access_control="secretariat_restricted"
        )

        self.db.add(document)
        await self.db.flush()

        if triggered_by_user_id:
            await audit_service.log_activity(
                db=self.db,
                user_id=triggered_by_user_id,
                action="declaration_synthesis",
                resource_type="document",
                resource_id=document.id,
                details={
                    "milestone": milestone,
                    "version": new_version,
                    "title": title
                }
            )

        await self.db.commit()
        await self.db.refresh(document)

        logger.info(
            f"✓ Declaration synthesized: version {new_version}, "
            f"{synthesis_result['metadata']['word_count']} words"
        )

        return {
            "document": document,
            "synthesis_result": synthesis_result,
            "version": new_version
        }

    async def _gather_twg_sections(self) -> Dict[str, str]:
        """
        Pull latest content from all TWG agents.

        Retrieves the most recent weekly packet from each TWG
        and compiles the content into sections suitable for declaration synthesis.

        Returns:
            Dict mapping TWG pillar name to their compiled section content
        """
        logger.info("Gathering TWG sections from latest weekly packets")

        result = await self.db.execute(select(TWG))
        twgs = result.scalars().all()

        twg_sections: Dict[str, str] = {}

        for twg in twgs:
            latest_packet = await self._get_latest_packet_for_twg(twg.id)

            if latest_packet:
                section_content = self._compile_packet_to_section(latest_packet, twg)
                twg_sections[twg.pillar.value] = section_content
            else:
                logger.debug(f"No weekly packet found for TWG: {twg.name}")

        logger.info(f"Gathered sections from {len(twg_sections)} TWGs")
        return twg_sections

    async def _get_latest_packet_for_twg(self, twg_id: uuid.UUID) -> Optional[WeeklyPacket]:
        """Get the most recent weekly packet for a TWG."""
        result = await self.db.execute(
            select(WeeklyPacket)
            .where(WeeklyPacket.twg_id == twg_id)
            .where(WeeklyPacket.status == "submitted")
            .order_by(desc(WeeklyPacket.created_at))
            .limit(1)
        )
        return result.scalars().first()

    def _compile_packet_to_section(self, packet: WeeklyPacket, twg: TWG) -> str:
        """
        Compile a weekly packet into a section suitable for declaration synthesis.

        Args:
            packet: The weekly packet to compile
            twg: The TWG this packet belongs to

        Returns:
            Formatted section content string
        """
        lines = []

        if packet.accomplishments:
            lines.append("Key Accomplishments:")
            for acc in packet.accomplishments:
                lines.append(f"  • {acc}")
            lines.append("")

        if packet.proposed_sessions:
            lines.append("Upcoming Sessions:")
            for session in packet.proposed_sessions:
                title = session.get("title", "Untitled")
                date = session.get("date", "TBD")
                lines.append(f"  • {title} ({date})")
            lines.append("")

        if packet.dependencies:
            lines.append("Cross-TWG Dependencies:")
            for dep in packet.dependencies:
                desc = dep.get("description", str(dep))
                lines.append(f"  • {desc}")
            lines.append("")

        if packet.risks_and_blockers:
            lines.append("Identified Risks:")
            for risk in packet.risks_and_blockers:
                desc = risk.get("description", str(risk))
                severity = risk.get("severity", "unknown")
                lines.append(f"  • [{severity.upper()}] {desc}")

        return "\n".join(lines) if lines else f"The {twg.name} working group continues to make progress."

    async def _get_latest_declaration_version(self, title: str) -> Optional[int]:
        """Get the latest version number for a declaration with the given title."""
        result = await self.db.execute(
            select(Document)
            .where(Document.category == "declaration")
            .where(Document.metadata_json["title"].astext == title)
            .order_by(desc(Document.version))
            .limit(1)
        )
        doc = result.scalars().first()
        return doc.version if doc else None

    async def _get_latest_declaration(self, title: str) -> Optional[Document]:
        """Get the latest declaration document with the given title."""
        result = await self.db.execute(
            select(Document)
            .where(Document.category == "declaration")
            .where(Document.metadata_json["title"].astext == title)
            .order_by(desc(Document.version))
            .limit(1)
        )
        return result.scalars().first()

    async def finalize_declaration(
        self,
        document_id: uuid.UUID,
        finalized_by_user_id: uuid.UUID
    ) -> Dict[str, Any]:
        """
        Mark a declaration as final.

        Args:
            document_id: ID of the document to finalize
            finalized_by_user_id: User ID who finalized this

        Returns:
            Dict with the finalized document and status
        """
        result = await self.db.execute(
            select(Document).where(Document.id == document_id)
        )
        document = result.scalars().first()

        if not document:
            return {"error": "Document not found", "document": None}

        document.version = DocumentVersion.FINAL
        document.metadata_json = {
            **(document.metadata_json or {}),
            "finalized_at": datetime.now(UTC).isoformat(),
            "finalized_by": str(finalized_by_user_id)
        }

        await audit_service.log_activity(
            db=self.db,
            user_id=finalized_by_user_id,
            action="declaration_finalized",
            resource_type="document",
            resource_id=document.id,
            details={
                "title": document.metadata_json.get("title"),
                "version": document.version
            }
        )

        await self.db.commit()
        await self.db.refresh(document)

        logger.info(f"✓ Declaration finalized: {document.file_name}")

        return {"document": document, "status": "finalized"}

    async def get_declaration_history(self, title: str) -> List[Document]:
        """
        Get all versions of a declaration.

        Args:
            title: The title of the declaration

        Returns:
            List of Document records ordered by version
        """
        result = await self.db.execute(
            select(Document)
            .where(Document.category == "declaration")
            .where(Document.metadata_json["title"].astext == title)
            .order_by(Document.version)
        )
        return list(result.scalars().all())
