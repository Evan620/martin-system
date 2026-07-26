"""Shared business logic for meeting capabilities and their HTTP routes."""

from __future__ import annotations

import logging
import os
import uuid
from datetime import datetime
from typing import Any, Optional

from fastapi import HTTPException
from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.deps import has_twg_access
from app.core.config import settings
from app.models.models import (
    Agenda,
    Document,
    Meeting,
    MeetingParticipant,
    MinutesStatus,
    TWG,
    User,
    UserRole,
)
from app.services import twg_webhook_service
from app.services.audit_service import audit_service
from app.services.email_service import email_service
from app.services.storage_service import get_storage_service


logger = logging.getLogger(__name__)


async def get_meeting_agenda(
    meeting_id: uuid.UUID,
    current_user: User,
    db: AsyncSession,
) -> Agenda:
    """Return the agenda after applying the route's existing access checks."""

    result = await db.execute(select(Meeting).where(Meeting.id == meeting_id))
    db_meeting = result.scalar_one_or_none()
    if not db_meeting:
        raise HTTPException(status_code=404, detail="Meeting not found")

    if not has_twg_access(current_user, db_meeting.twg_id):
        raise HTTPException(status_code=403, detail="Access denied")

    result = await db.execute(select(Agenda).where(Agenda.meeting_id == meeting_id))
    agenda = result.scalar_one_or_none()
    if not agenda:
        raise HTTPException(status_code=404, detail="Agenda not found")
    return agenda


async def approve_meeting_minutes(
    meeting_id: uuid.UUID,
    current_user: User,
    db: AsyncSession,
    *,
    client_ip: Optional[str] = None,
) -> dict[str, Any]:
    """Approve and publish minutes using the existing route behavior."""

    result = await db.execute(
        select(Meeting)
        .options(
            selectinload(Meeting.minutes),
            selectinload(Meeting.participants).selectinload(MeetingParticipant.user),
            selectinload(Meeting.twg),
        )
        .where(Meeting.id == meeting_id)
    )
    db_meeting = result.scalar_one_or_none()

    if not db_meeting:
        raise HTTPException(status_code=404, detail="Meeting not found")

    if not has_twg_access(current_user, db_meeting.twg_id):
        raise HTTPException(status_code=403, detail="Access denied")

    if current_user.role not in [UserRole.SECRETARIAT_LEAD, UserRole.ADMIN]:
        raise HTTPException(
            status_code=403,
            detail=(
                "Only Secretariat Leads can approve minutes. "
                "Please submit for approval instead."
            ),
        )

    if not db_meeting.minutes:
        raise HTTPException(status_code=400, detail="No minutes to approve")

    current_status_val = (
        db_meeting.minutes.status.value
        if hasattr(db_meeting.minutes.status, "value")
        else str(db_meeting.minutes.status)
    )
    if current_status_val != MinutesStatus.PENDING_APPROVAL.value:
        raise HTTPException(
            status_code=400,
            detail=(
                "Minutes must be PENDING_APPROVAL to approve. "
                f"Current: {current_status_val}"
            ),
        )

    db_meeting.minutes.status = MinutesStatus.APPROVED
    await db.commit()
    await db.refresh(db_meeting.minutes)

    pdf_bytes = None
    try:
        from app.services.pdf_service import pdf_service

        pillar_display = (
            db_meeting.twg.pillar.value.replace("_", " ").title()
            if db_meeting.twg
            else "General"
        )
        pdf_context = {
            "pillar_name": pillar_display,
            "meeting_title": db_meeting.title,
            "meeting_date": (
                db_meeting.scheduled_at.strftime("%Y-%m-%d")
                if db_meeting.scheduled_at
                else "TBD"
            ),
            "meeting_time": (
                db_meeting.scheduled_at.strftime("%H:%M")
                if db_meeting.scheduled_at
                else ""
            ),
            "location": db_meeting.location or "Virtual",
        }
        pdf_bytes = pdf_service.generate_minutes_pdf(
            minutes_markdown=db_meeting.minutes.content,
            template_context=pdf_context,
        )
    except Exception as exc:
        logging.error(f"PDF Gen Failure: {exc}")

    if pdf_bytes:
        try:
            pdf_filename = f"Minutes - {db_meeting.title}.pdf"
            existing = await db.execute(
                select(Document).where(
                    and_(
                        Document.meeting_id == db_meeting.id,
                        Document.document_type == "minutes",
                    )
                )
            )
            if not existing.scalar_one_or_none():
                file_path = None
                metadata_extra = {}

                try:
                    storage = get_storage_service()
                    twg_result = await db.execute(
                        select(TWG).where(TWG.id == db_meeting.twg_id)
                    )
                    twg = twg_result.scalar_one_or_none()
                    target_folder_id = None
                    if twg:
                        target_folder_id = storage.get_or_create_twg_folder(twg.name)

                    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
                    safe_filename = f"{timestamp}_minutes_{db_meeting.id}.pdf"
                    cloud_file_id, cloud_view_link, cloud_download_url = (
                        storage.upload_bytes(
                            file_bytes=pdf_bytes,
                            file_name=safe_filename,
                            mime_type="application/pdf",
                            folder_id=target_folder_id,
                        )
                    )
                    if cloud_file_id:
                        file_path = cloud_file_id
                        metadata_extra = {
                            "storage_mode": "cloud",
                            "cloud_file_id": cloud_file_id,
                            "cloud_view_link": cloud_view_link,
                            "cloud_download_url": cloud_download_url,
                        }
                        logging.info(
                            f"Uploaded minutes PDF to cloud storage: {cloud_file_id}"
                        )
                except Exception as cloud_err:
                    logging.warning(
                        "Cloud storage upload failed, falling back to local: "
                        f"{cloud_err}"
                    )

                if not file_path:
                    upload_dir = os.path.join(settings.UPLOAD_DIR, "minutes")
                    os.makedirs(upload_dir, exist_ok=True)
                    local_path = os.path.join(
                        upload_dir,
                        f"minutes_{db_meeting.id}.pdf",
                    )
                    with open(local_path, "wb") as pdf_file:
                        pdf_file.write(pdf_bytes)
                    file_path = local_path
                    metadata_extra = {"storage_mode": "local"}
                    logging.info(f"Saved minutes PDF to local disk: {local_path}")

                minutes_doc = Document(
                    twg_id=db_meeting.twg_id,
                    meeting_id=db_meeting.id,
                    file_name=pdf_filename,
                    file_path=file_path,
                    file_type="application/pdf",
                    document_type="minutes",
                    uploaded_by_id=current_user.id,
                    metadata_json={
                        "meeting_id": str(db_meeting.id),
                        "meeting_title": db_meeting.title,
                        "status": "approved",
                        "file_size": len(pdf_bytes),
                        **metadata_extra,
                    },
                )
                db.add(minutes_doc)
                await db.commit()
        except Exception as exc:
            logging.error(f"Minutes Document creation failed: {exc}")

    try:
        from app.core.knowledge_base import get_knowledge_base

        kb = get_knowledge_base()
        kb.add_document(
            content=db_meeting.minutes.content,
            metadata={
                "source": "official_minutes",
                "meeting_id": str(db_meeting.id),
                "date": (
                    db_meeting.scheduled_at.isoformat()
                    if db_meeting.scheduled_at
                    else None
                ),
                "pillar": (
                    db_meeting.twg.pillar.value if db_meeting.twg else "unknown"
                ),
                "status": "approved",
                "file_name": f"Minutes - {db_meeting.title}",
            },
            namespace=(
                f"twg-{db_meeting.twg_id}" if db_meeting.twg_id else "global"
            ),
        )
    except Exception as exc:
        logging.error(f"KB Indexing Failed: {exc}")

    recipients = set()
    for participant in db_meeting.participants:
        if participant.user and participant.user.email:
            recipients.add(participant.user.email)
        elif participant.email:
            recipients.add(participant.email)
    recipient_list = list(recipients)

    if pdf_bytes and recipient_list:
        try:
            email_context = {
                "recipient_name": "Colleague",
                "meeting_title": db_meeting.title,
                "date_str": (
                    db_meeting.scheduled_at.strftime("%Y-%m-%d")
                    if db_meeting.scheduled_at
                    else "TBD"
                ),
                "pillar_name": pillar_display,
                "dashboard_url": (
                    f"{settings.FRONTEND_URL}/meetings/{db_meeting.id}"
                ),
            }
            await email_service.send_minutes_published_email(
                to_emails=recipient_list,
                template_context=email_context,
                pdf_content=pdf_bytes,
                pdf_filename="minutes.pdf",
            )
        except Exception as exc:
            logging.error(f"Email Sending Failed: {exc}")

    await audit_service.log_activity(
        db,
        user_id=current_user.id,
        action="MEETING_MINUTES_APPROVED",
        resource_type="meeting",
        resource_id=meeting_id,
        details={
            "meeting_title": db_meeting.title,
            "actions": "generated_pdf, sent_email, indexed_kb",
            "recipients": recipient_list,
        },
        ip_address=client_ip,
    )

    try:
        if db_meeting.minutes.public_summary:
            emit_result = await twg_webhook_service.emit_minutes_published(
                db_meeting,
                db_meeting.minutes.public_summary,
            )
            logger.info(
                f"[TWG webhook] emit result for meeting {meeting_id}: {emit_result}"
            )
            await audit_service.log_activity(
                db,
                user_id=current_user.id,
                action="MEETING_MINUTES_WEBHOOK_EMITTED",
                resource_type="meeting",
                resource_id=meeting_id,
                details={"emit_result": emit_result},
                ip_address=client_ip,
            )
            await db.commit()
    except Exception as exc:
        logging.error(
            f"[TWG webhook] emit/audit failed — approval unaffected: {exc}"
        )

    return {
        "message": "Minutes approved and published",
        "status": (
            db_meeting.minutes.status.value
            if hasattr(db_meeting.minutes.status, "value")
            else str(db_meeting.minutes.status)
        ),
        "workflows_triggered": ["pdf", "email", "audit", "kb_indexing"],
    }
