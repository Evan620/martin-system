from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, or_, and_
from sqlalchemy.orm import selectinload
from typing import List
from datetime import datetime
import asyncio
import logging
import uuid
import csv
import io

from app.core.database import get_db
from app.core.config import settings
from app.models.models import TWG, User, UserRole, Meeting, Project, ActionItem, Document, MeetingStatus, ActionItemStatus, MeetingParticipant, RsvpStatus, SubGroup

logger = logging.getLogger(__name__)
from app.schemas.schemas import TWGCreate, TWGRead, TWGUpdate
from app.api.deps import get_current_active_user, require_admin, require_facilitator

router = APIRouter(prefix="/twgs", tags=["TWGs"])


async def _sync_new_members_to_future_meetings(
    twg_id: uuid.UUID,
    new_user_ids: list[uuid.UUID],
    new_user_emails: list[str],
    db: AsyncSession,
) -> None:
    """
    Auto-add newly-added TWG members as participants to all future
    SCHEDULED / REQUESTED meetings for that TWG.
    GCal sync and email invites run in a fire-and-forget background task.
    """
    if not new_user_ids:
        return

    now = datetime.utcnow()

    # 1. Fetch future meetings for this TWG
    result = await db.execute(
        select(Meeting)
        .options(selectinload(Meeting.participants), selectinload(Meeting.twg))
        .where(
            and_(
                Meeting.twg_id == twg_id,
                Meeting.scheduled_at > now,
                Meeting.status.in_([MeetingStatus.SCHEDULED, MeetingStatus.REQUESTED]),
            )
        )
    )
    future_meetings = result.scalars().all()
    if not future_meetings:
        return

    # 2. Insert MeetingParticipant rows (skip duplicates)
    meetings_to_notify: list[dict] = []
    for meeting in future_meetings:
        existing_user_ids = {p.user_id for p in meeting.participants if p.user_id}
        added_for_meeting = []
        for uid, email in zip(new_user_ids, new_user_emails):
            if uid not in existing_user_ids:
                db.add(MeetingParticipant(
                    meeting_id=meeting.id,
                    user_id=uid,
                    email=email,
                    rsvp_status=RsvpStatus.PENDING,
                ))
                added_for_meeting.append(email)
        if added_for_meeting:
            meetings_to_notify.append({
                "meeting_id": str(meeting.id),
                "title": meeting.title,
                "scheduled_at": meeting.scheduled_at,
                "duration": meeting.duration_minutes,
                "location": meeting.location,
                "video_link": meeting.video_link,
                "twg_name": meeting.twg.name if meeting.twg else "TWG",
                "emails": added_for_meeting,
            })

    await db.commit()

    if not meetings_to_notify:
        return

    # 3. Fire-and-forget: GCal sync + email invites
    async def _bg_sync():
        try:
            from app.services.calendar_service import calendar_service
            from app.services.email_service import email_service
            from app.services.recurring_meeting_service import _gcal_executor
            from app.api.routes.meetings import format_meeting_time_for_email

            loop = asyncio.get_running_loop()
            for info in meetings_to_notify:
                # GCal — mirror the sync-calendar button logic exactly
                try:
                    existing = await loop.run_in_executor(
                        _gcal_executor,
                        lambda m=info: calendar_service.get_meeting_event(m["meeting_id"]),
                    )
                    if existing:
                        # Strip to email-only (like the working sync-calendar button)
                        # Raw GCal attendees include read-only fields (responseStatus,
                        # self, organizer, id) that silently break sendUpdates='all'
                        existing_attendees = [
                            {'email': a['email']}
                            for a in existing.get('attendees', [])
                            if a.get('email')
                        ]
                        existing_emails = {a['email'] for a in existing_attendees}
                        for email in info["emails"]:
                            if email and email not in existing_emails:
                                existing_attendees.append({'email': email})
                        event_id = existing['id']

                        await loop.run_in_executor(
                            _gcal_executor,
                            lambda eid=event_id, att=existing_attendees: calendar_service.service.events().patch(
                                calendarId='primary',
                                eventId=eid,
                                body={'attendees': att},
                                sendUpdates='all'
                            ).execute()
                        )
                        print(f"[TWG Sync] Patched attendees to GCal event {event_id} for meeting {info['meeting_id']}")
                    else:
                        # No GCal event yet — create it with new attendees included
                        created = await loop.run_in_executor(
                            _gcal_executor,
                            lambda m=info: calendar_service.create_meeting_event(
                                title=m["title"],
                                start_time=m["scheduled_at"],
                                duration_minutes=m["duration"],
                                description=f"Meeting: {m['title']}",
                                attendees=m["emails"],
                                meeting_id=m["meeting_id"],
                            ),
                        )
                        print(f"[TWG Sync] Created GCal event for meeting {info['meeting_id']}: {bool(created)}")
                except Exception as e:
                    import traceback
                    print(f"[TWG Sync] GCal sync failed for meeting {info['meeting_id']}: {e}")
                    traceback.print_exc()

                # Email invite
                try:
                    date_str, time_str = format_meeting_time_for_email(info["scheduled_at"])
                    await email_service.send_meeting_invite(
                        to_emails=info["emails"],
                        subject=f"Meeting Invitation: {info['title']}",
                        template_name="meeting_invite.html",
                        template_context={
                            "user_name": "Valued Participant",
                            "meeting_title": info["title"],
                            "meeting_date": date_str,
                            "meeting_time": time_str,
                            "location": info.get("location") or "Virtual",
                            "video_link": info.get("video_link"),
                            "pillar_name": info["twg_name"],
                            "portal_url": settings.FRONTEND_URL + "/schedule",
                        },
                        meeting_details={
                            "title": info["title"],
                            "meeting_id": info["meeting_id"],
                            "start_time": info["scheduled_at"],
                            "duration": info["duration"],
                            "location": info.get("video_link") or info.get("location") or "Virtual",
                        },
                    )
                except Exception as e:
                    logger.warning(f"[TWG Sync] Email invite failed for meeting {info['meeting_id']}: {e}")

                await asyncio.sleep(1)  # Rate-limit between meetings
        except Exception as e:
            logger.warning(f"[TWG Sync] Background sync task failed: {e}")

    asyncio.create_task(_bg_sync())
    logger.info(
        f"[TWG Sync] Queued {len(meetings_to_notify)} future meeting(s) for "
        f"{len(new_user_ids)} new member(s) in TWG {twg_id}"
    )


@router.post("/", response_model=TWGRead, status_code=status.HTTP_201_CREATED)
async def create_twg(
    twg_in: TWGCreate,
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
):
    """
    Create a new TWG.
    
    Requires ADMIN role.
    """
    db_twg = TWG(**twg_in.model_dump())
    db.add(db_twg)
    await db.commit()
    await db.refresh(db_twg)
    return db_twg

@router.get("/dropdown")
async def list_twgs_dropdown(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Lightweight TWG list for dropdown selectors. Returns only id, name, pillar, group_type.
    """
    from app.models.models import TWGPillar
    HIDDEN_PILLARS = {TWGPillar.protocol_logistics, TWGPillar.resource_mobilization}

    result = await db.execute(
        select(TWG.id, TWG.name, TWG.pillar, TWG.group_type)
        .where(
            or_(
                (TWG.pillar.notin_(HIDDEN_PILLARS)) & (TWG.group_type == "twg"),
                TWG.group_type == "leads_council"
            )
        )
    )
    rows = result.all()
    return [
        {"id": str(r.id), "name": r.name, "pillar": r.pillar.value if r.pillar else None, "group_type": r.group_type}
        for r in rows
    ]


@router.get("/members/export")
async def export_all_twg_members(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Export all members across all TWGs as a single CSV (admin/facilitator only)."""
    if current_user.role not in (UserRole.ADMIN, UserRole.SECRETARIAT_LEAD, UserRole.TWG_FACILITATOR):
        raise HTTPException(status_code=403, detail="Not authorized")

    result = await db.execute(
        select(TWG).options(selectinload(TWG.members)).order_by(TWG.name)
    )
    all_twgs = result.scalars().all()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["TWG", "Full Name", "Email", "Role", "Organization", "Status"])
    for twg in all_twgs:
        for m in twg.members:
            if twg.political_lead_id == m.id:
                role_label = "Political Lead"
            elif twg.technical_lead_id == m.id:
                role_label = "Technical Lead"
            elif m.role == UserRole.TWG_FACILITATOR:
                role_label = "Facilitator"
            else:
                role_label = "Member"
            writer.writerow([
                twg.name,
                m.full_name,
                m.email,
                role_label,
                m.organization or "",
                "Active" if m.is_active else "Inactive",
            ])

    output.seek(0)
    from datetime import date
    filename = f"all_twg_members_{date.today().isoformat()}.csv"
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/", response_model=List[TWGRead])
async def list_twgs(
    skip: int = 0,
    limit: int = 100,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    List all TWGs.
    
    Accessible to all active users.
    """
    try:
        # Common loading options with selectinload for leads
        query_options = [
            selectinload(TWG.political_lead),
            selectinload(TWG.technical_lead),
            selectinload(TWG.members),
            selectinload(TWG.action_items).selectinload(ActionItem.owner),
            selectinload(TWG.documents),
        ]
        
        # We will need to perform separate queries or use scalar subqueries for stats.
        # For simplicity and clarity in this iteration, let's fetch IDs and then load stats.
        # A more optimized approach would use group_by and multiple queries.
        
        # Hide non-core TWGs per client request (only show 4 core + leads_council)
        from app.models.models import TWGPillar
        from sqlalchemy import or_
        HIDDEN_PILLARS = {TWGPillar.protocol_logistics, TWGPillar.resource_mobilization}

        result = await db.execute(
            select(TWG)
            .where(
                or_(
                    # Standard TWGs (exclude hidden pillars)
                    (TWG.pillar.notin_(HIDDEN_PILLARS)) & (TWG.group_type == "twg"),
                    # Always show leads_council
                    TWG.group_type == "leads_council"
                )
            )
            .options(*query_options)
            .offset(skip).limit(limit)
        )
        twgs = result.scalars().all()
        
        # Enrich with stats
        for twg in twgs:
            try:
                # Meetings Held (Completed)
                meetings_res = await db.execute(
                    select(func.count(Meeting.id)).where(Meeting.twg_id == twg.id, Meeting.status == MeetingStatus.COMPLETED)
                )
                meetings_held = meetings_res.scalar() or 0
                
                # Open Actions (Not Completed)
                # Fix Cartesian product: Remove implicit TWG reference (TWG.id == twg.id)
                actions_res = await db.execute(
                    select(func.count(ActionItem.id)).where(ActionItem.twg_id == twg.id, ActionItem.status.in_([ActionItemStatus.PENDING, ActionItemStatus.IN_PROGRESS, ActionItemStatus.OVERDUE]))
                )
                open_actions = actions_res.scalar() or 0
                
                # Pipeline Projects (All)
                projects_res = await db.execute(
                     select(func.count(Project.id)).where(Project.twg_id == twg.id)
                )
                pipeline_projects = projects_res.scalar() or 0
                
                # Resources (Documents)
                docs_res = await db.execute(
                    select(func.count(Document.id)).where(Document.twg_id == twg.id)
                )
                resources_count = docs_res.scalar() or 0
                
                twg.stats = {
                    "meetings_held": meetings_held,
                    "open_actions": open_actions,
                    "pipeline_projects": pipeline_projects,
                    "resources_count": resources_count
                }
            except Exception as e:
                # Fallback stats on error
                print(f"Error calculating stats for TWG {twg.name}: {e}")
                twg.stats = {
                    "meetings_held": 0,
                    "open_actions": 0,
                    "pipeline_projects": 0,
                    "resources_count": 0
                }
            
        return twgs
    except Exception as e:
        import traceback
        print(f"CRITICAL ERROR in list_twgs: {e}")
        print(traceback.format_exc())
        raise HTTPException(status_code=500, detail="Internal Server Error listing TWGs")

@router.get("/{twg_id}", response_model=TWGRead)
async def get_twg(
    twg_id: uuid.UUID,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get TWG details by ID with stats.
    """
    result = await db.execute(
        select(TWG)
        .options(
            selectinload(TWG.political_lead),
            selectinload(TWG.technical_lead),
            selectinload(TWG.action_items).selectinload(ActionItem.owner),
            selectinload(TWG.documents).selectinload(Document.uploaded_by),
            selectinload(TWG.members)
        )
        .where(TWG.id == twg_id)
    )
    db_twg = result.scalar_one_or_none()
    if not db_twg:
        raise HTTPException(status_code=404, detail="TWG not found")
        
    # Fetch stats
    # Meetings Held
    meetings_res = await db.execute(
        select(func.count(Meeting.id)).where(Meeting.twg_id == twg_id, Meeting.status == MeetingStatus.COMPLETED)
    )
    meetings_held = meetings_res.scalar() or 0
    
    # Open Actions
    actions_res = await db.execute(
        select(func.count(ActionItem.id)).where(ActionItem.twg_id == twg_id, ActionItem.status.in_([ActionItemStatus.PENDING, ActionItemStatus.IN_PROGRESS, ActionItemStatus.OVERDUE]))
    )
    open_actions = actions_res.scalar() or 0
    
    # Pipeline Projects
    projects_res = await db.execute(
            select(func.count(Project.id)).where(Project.twg_id == twg_id)
    )
    pipeline_projects = projects_res.scalar() or 0
    
    # Resources - explicitly fetch documents for this TWG
    # Exclude transcripts and shared_workspace from the count
    docs_res = await db.execute(
        select(Document).options(selectinload(Document.uploaded_by))
        .where(
            Document.twg_id == twg_id,
            or_(
                Document.document_type.notin_(["transcript", "transcript_placeholder", "shared_workspace"]),
                Document.document_type.is_(None)
            )
        )
    )
    twg_documents = docs_res.scalars().all()
    resources_count = len(twg_documents)

    db_twg.stats = {
        "meetings_held": meetings_held,
        "open_actions": open_actions,
        "pipeline_projects": pipeline_projects,
        "resources_count": resources_count
    }

    return db_twg

@router.patch("/{twg_id}", response_model=TWGRead)
async def update_twg(
    twg_id: uuid.UUID,
    twg_in: TWGUpdate,
    current_user: User = Depends(require_facilitator),
    db: AsyncSession = Depends(get_db)
):
    """
    Update TWG details.
    
    Requires ADMIN or FACILITATOR role.
    If FACILITATOR, ideally should check if assigned to this TWG (logic can be added).
    """
    result = await db.execute(
        select(TWG)
        .options(
            selectinload(TWG.political_lead),
            selectinload(TWG.technical_lead),
            selectinload(TWG.action_items).selectinload(ActionItem.owner),
            selectinload(TWG.documents),
            selectinload(TWG.members),
        )
        .where(TWG.id == twg_id)
    )
    db_twg = result.scalar_one_or_none()
    if not db_twg:
        raise HTTPException(status_code=404, detail="TWG not found")
    
    # Additional check: If facilitator, ensure they are the lead?
    # For now, allow generic facilitator access as per simplified reqs.
    # Admins can edit anything.
    
    update_data = twg_in.model_dump(exclude_unset=True)
    leads_changed = "political_lead_id" in update_data or "technical_lead_id" in update_data

    for key, value in update_data.items():
        setattr(db_twg, key, value)

    await db.commit()

    # Auto-sync Leads Council membership when any TWG's leads change
    if leads_changed:
        await _sync_leads_council_membership(db)
        await db.commit()

    # Refresh with eager loading to ensure relationships are loaded
    await db.refresh(db_twg, attribute_names=['political_lead', 'technical_lead', 'action_items', 'documents', 'members'])
    return db_twg


# --- TWG Member Management Endpoints ---

async def _check_twg_management_access(twg_id: uuid.UUID, current_user: User, db: AsyncSession) -> TWG:
    """
    Verify user has management access to a TWG (admin, facilitator of this TWG, or lead).
    Returns the TWG object if access is granted.
    """
    result = await db.execute(
        select(TWG)
        .options(selectinload(TWG.members), selectinload(TWG.political_lead), selectinload(TWG.technical_lead))
        .where(TWG.id == twg_id)
    )
    twg = result.scalar_one_or_none()
    if not twg:
        raise HTTPException(status_code=404, detail="TWG not found")

    # Admins and secretariat leads can manage any TWG
    if current_user.role in [UserRole.ADMIN, UserRole.SECRETARIAT_LEAD]:
        return twg

    # Facilitators can manage TWGs they are assigned to
    user_twg_ids = [t.id for t in current_user.twgs]
    is_member = twg_id in user_twg_ids

    # Check if user is a lead of this TWG
    is_lead = (
        (twg.political_lead_id and twg.political_lead_id == current_user.id) or
        (twg.technical_lead_id and twg.technical_lead_id == current_user.id)
    )

    if current_user.role == UserRole.TWG_FACILITATOR and is_member:
        return twg
    if is_lead:
        return twg

    raise HTTPException(status_code=403, detail="You do not have permission to manage members of this TWG")


@router.get("/{twg_id}/members")
async def list_twg_members(
    twg_id: uuid.UUID,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    List all members of a TWG.
    Accessible to any member of the TWG, facilitators, and admins.
    """
    # Any TWG member can view the list (not just managers)
    from app.api.deps import require_twg_access
    await require_twg_access(twg_id, current_user, db)

    result = await db.execute(
        select(TWG)
        .options(selectinload(TWG.members))
        .where(TWG.id == twg_id)
    )
    twg = result.scalar_one_or_none()
    if not twg:
        raise HTTPException(status_code=404, detail="TWG not found")

    return [
        {
            "id": str(m.id),
            "full_name": m.full_name,
            "email": m.email,
            "role": m.role.value,
            "organization": m.organization,
            "is_active": m.is_active,
            "is_political_lead": twg.political_lead_id == m.id if twg.political_lead_id else False,
            "is_technical_lead": twg.technical_lead_id == m.id if twg.technical_lead_id else False,
        }
        for m in twg.members
    ]


@router.get("/{twg_id}/members/export")
async def export_twg_members(
    twg_id: uuid.UUID,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Export members of a single TWG as CSV."""
    from app.api.deps import require_twg_access
    await require_twg_access(twg_id, current_user, db)

    result = await db.execute(
        select(TWG).options(selectinload(TWG.members)).where(TWG.id == twg_id)
    )
    twg = result.scalar_one_or_none()
    if not twg:
        raise HTTPException(status_code=404, detail="TWG not found")

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["TWG", "Full Name", "Email", "Role", "Organization", "Status"])
    for m in twg.members:
        if twg.political_lead_id == m.id:
            role_label = "Political Lead"
        elif twg.technical_lead_id == m.id:
            role_label = "Technical Lead"
        elif m.role == UserRole.TWG_FACILITATOR:
            role_label = "Facilitator"
        else:
            role_label = "Member"
        writer.writerow([
            twg.name,
            m.full_name,
            m.email,
            role_label,
            m.organization or "",
            "Active" if m.is_active else "Inactive",
        ])

    output.seek(0)
    filename = f"{twg.name.replace(' ', '_')}_members.csv"
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


from pydantic import BaseModel
import secrets

class AddMemberRequest(BaseModel):
    email: str
    full_name: str = ""  # Required when creating a new user


@router.post("/{twg_id}/members", status_code=status.HTTP_201_CREATED)
async def add_twg_member(
    twg_id: uuid.UUID,
    body: AddMemberRequest,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Add a member to a TWG by email.
    If the user doesn't exist, facilitators/admins can auto-create them as a TWG_MEMBER.
    """
    from app.utils.security import hash_password

    twg = await _check_twg_management_access(twg_id, current_user, db)

    if twg.group_type == "leads_council":
        raise HTTPException(status_code=400, detail="Leads Council membership is auto-managed. Change TWG leads to update membership.")

    # Find user by email
    email = body.email.strip().lower()
    result = await db.execute(
        select(User).where(User.email == email).options(selectinload(User.twgs))
    )
    user_to_add = result.scalar_one_or_none()
    created_new = False

    if not user_to_add:
        # Auto-create the user as TWG_MEMBER
        if not body.full_name.strip():
            raise HTTPException(
                status_code=400,
                detail="full_name is required when adding a new user who is not yet registered."
            )

        temp_password = secrets.token_urlsafe(16)
        user_to_add = User(
            full_name=body.full_name.strip(),
            email=email,
            hashed_password=hash_password(temp_password),
            role=UserRole.TWG_MEMBER,
            is_active=True,
        )
        db.add(user_to_add)
        await db.flush()  # Get the ID assigned
        created_new = True

    # Check if already a member
    member_ids = [m.id for m in twg.members]
    if user_to_add.id in member_ids:
        raise HTTPException(
            status_code=400,
            detail=f"{user_to_add.full_name} is already a member of this TWG."
        )

    # Add to TWG
    twg.members.append(user_to_add)
    await db.commit()

    # Auto-add new member to future meetings for this TWG
    try:
        await _sync_new_members_to_future_meetings(
            twg_id=twg.id,
            new_user_ids=[user_to_add.id],
            new_user_emails=[user_to_add.email],
            db=db,
        )
    except Exception as e:
        logger.warning(f"[TWG Members] Failed to sync new member to future meetings: {e}")

    # Send invitation email for newly created users
    invite_sent = False
    if created_new:
        try:
            from app.services.email_service import email_service
            from app.core.config import settings

            login_url = settings.FRONTEND_URL
            await email_service.send_user_invite(
                to_email=email,
                full_name=user_to_add.full_name,
                password=temp_password,
                role=user_to_add.role.value,
                login_url=login_url
            )
            invite_sent = True
        except Exception as e:
            print(f"[TWG Members] Failed to send invite email to {email}: {e}")

    msg = f"{user_to_add.full_name} has been added to {twg.name}."
    if created_new:
        msg = f"New account created for {user_to_add.full_name} ({email}) and added to {twg.name}."
        if invite_sent:
            msg += " An invitation email has been sent."
        else:
            msg += " (Email invitation could not be sent — share the login details manually.)"

    return {
        "message": msg,
        "created_new": created_new,
        "member": {
            "id": str(user_to_add.id),
            "full_name": user_to_add.full_name,
            "email": user_to_add.email,
            "role": user_to_add.role.value,
            "organization": user_to_add.organization,
        }
    }


class BulkAddMemberEntry(BaseModel):
    email: str
    full_name: str = ""


class BulkAddMembersRequest(BaseModel):
    members: list[BulkAddMemberEntry]


@router.post("/{twg_id}/members/bulk", status_code=status.HTTP_201_CREATED)
async def bulk_add_twg_members(
    twg_id: uuid.UUID,
    body: BulkAddMembersRequest,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Bulk add members to a TWG.
    Accepts a list of {email, full_name} entries.
    Skips duplicates, auto-creates new users, sends invite emails.
    """
    from app.utils.security import hash_password

    twg = await _check_twg_management_access(twg_id, current_user, db)

    if twg.group_type == "leads_council":
        raise HTTPException(status_code=400, detail="Leads Council membership is auto-managed. Change TWG leads to update membership.")

    existing_member_emails = {m.email.lower() for m in twg.members}

    results = {"added": [], "skipped": [], "errors": []}

    for entry in body.members:
        email = entry.email.strip().lower()
        if not email:
            continue

        # Skip duplicates
        if email in existing_member_emails:
            results["skipped"].append({"email": email, "reason": "Already a member"})
            continue

        try:
            # Find or create user
            result = await db.execute(
                select(User).where(User.email == email).options(selectinload(User.twgs))
            )
            user_to_add = result.scalar_one_or_none()
            created_new = False

            if not user_to_add:
                if not entry.full_name.strip():
                    results["errors"].append({"email": email, "reason": "Full name required for new users"})
                    continue

                temp_password = secrets.token_urlsafe(16)
                user_to_add = User(
                    full_name=entry.full_name.strip(),
                    email=email,
                    hashed_password=hash_password(temp_password),
                    role=UserRole.TWG_MEMBER,
                    is_active=True,
                )
                db.add(user_to_add)
                await db.flush()
                created_new = True

            twg.members.append(user_to_add)
            existing_member_emails.add(email)

            added_entry = {
                "id": str(user_to_add.id),
                "email": email,
                "full_name": user_to_add.full_name,
                "created_new": created_new,
            }

            # Send invite for new users
            if created_new:
                try:
                    from app.services.email_service import email_service
                    from app.core.config import settings
                    await email_service.send_user_invite(
                        to_email=email,
                        full_name=user_to_add.full_name,
                        password=temp_password,
                        role=user_to_add.role.value,
                        login_url=settings.FRONTEND_URL
                    )
                    added_entry["invite_sent"] = True
                except Exception as e:
                    added_entry["invite_sent"] = False
                    print(f"[TWG Bulk] Failed to send invite to {email}: {e}")

            results["added"].append(added_entry)

        except Exception as e:
            results["errors"].append({"email": email, "reason": str(e)})

    await db.commit()

    # Auto-add new members to future meetings for this TWG
    added_user_ids = [uuid.UUID(e["id"]) for e in results["added"]]
    added_user_emails = [e["email"] for e in results["added"]]
    if added_user_ids:
        try:
            await _sync_new_members_to_future_meetings(
                twg_id=twg.id,
                new_user_ids=added_user_ids,
                new_user_emails=added_user_emails,
                db=db,
            )
        except Exception as e:
            logger.warning(f"[TWG Bulk] Failed to sync new members to future meetings: {e}")

    total_added = len(results["added"])
    total_skipped = len(results["skipped"])
    total_errors = len(results["errors"])
    new_accounts = sum(1 for a in results["added"] if a.get("created_new"))

    return {
        "message": f"Added {total_added} member{'s' if total_added != 1 else ''} to {twg.name}."
                   + (f" {new_accounts} new account{'s' if new_accounts != 1 else ''} created." if new_accounts else "")
                   + (f" {total_skipped} skipped (already members)." if total_skipped else "")
                   + (f" {total_errors} failed." if total_errors else ""),
        "summary": {"added": total_added, "skipped": total_skipped, "errors": total_errors, "new_accounts": new_accounts},
        "results": results,
    }


@router.delete("/{twg_id}/members/{user_id}", status_code=status.HTTP_200_OK)
async def remove_twg_member(
    twg_id: uuid.UUID,
    user_id: uuid.UUID,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Remove a member from a TWG.
    Cannot remove yourself or a TWG lead.
    """
    twg = await _check_twg_management_access(twg_id, current_user, db)

    if twg.group_type == "leads_council":
        raise HTTPException(status_code=400, detail="Leads Council membership is auto-managed. Change TWG leads to update membership.")

    # Prevent removing yourself
    if user_id == current_user.id:
        raise HTTPException(status_code=400, detail="You cannot remove yourself from the TWG.")

    # Prevent removing leads
    if twg.political_lead_id == user_id or twg.technical_lead_id == user_id:
        raise HTTPException(status_code=400, detail="Cannot remove a TWG lead. Change the lead assignment first.")

    # Find the member
    member_to_remove = None
    for m in twg.members:
        if m.id == user_id:
            member_to_remove = m
            break

    if not member_to_remove:
        raise HTTPException(status_code=404, detail="User is not a member of this TWG.")

    twg.members.remove(member_to_remove)

    # Remove the user from all subgroups in this TWG
    sg_result = await db.execute(
        select(SubGroup)
        .options(selectinload(SubGroup.members))
        .where(SubGroup.twg_id == twg_id)
    )
    for sg in sg_result.scalars().all():
        sg.members = [m for m in sg.members if m.id != user_id]
        # Clear lead if this user was the subgroup lead
        if sg.lead_id == user_id:
            sg.lead_id = None

    await db.commit()

    return {"message": f"{member_to_remove.full_name} has been removed from {twg.name}."}


async def _sync_leads_council_membership(db: AsyncSession) -> dict:
    """
    Sync the TWG Leads Council membership from all active TWGs' leads.
    Adds new leads and removes users who are no longer a lead of any TWG.
    Uses flush() so the caller controls the transaction.
    Returns {"added": int, "removed": int, "total_members": int}.
    """
    # Find the leads_council group
    result = await db.execute(
        select(TWG)
        .options(selectinload(TWG.members))
        .where(TWG.group_type == "leads_council")
    )
    council = result.scalar_one_or_none()
    if not council:
        return {"added": 0, "removed": 0, "total_members": 0}

    # Fetch all active TWGs (standard TWGs only)
    twgs_result = await db.execute(
        select(TWG).where(TWG.group_type == "twg", TWG.status == "active")
    )
    all_twgs = twgs_result.scalars().all()

    # Collect lead user IDs
    lead_ids = set()
    for t in all_twgs:
        if t.political_lead_id:
            lead_ids.add(t.political_lead_id)
        if t.technical_lead_id:
            lead_ids.add(t.technical_lead_id)

    existing_member_ids = {m.id for m in council.members}

    # Add new leads
    added = 0
    if lead_ids:
        ids_to_add = lead_ids - existing_member_ids
        if ids_to_add:
            users_result = await db.execute(
                select(User).where(User.id.in_(ids_to_add))
            )
            for user in users_result.scalars().all():
                council.members.append(user)
                added += 1

    # Remove stale members (no longer a lead of any TWG)
    removed = 0
    stale = [m for m in council.members if m.id not in lead_ids]
    for m in stale:
        council.members.remove(m)
        removed += 1

    await db.flush()

    return {"added": added, "removed": removed, "total_members": len(council.members)}


@router.post("/{twg_id}/sync-leads", status_code=status.HTTP_200_OK)
async def sync_leads_council(
    twg_id: uuid.UUID,
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
):
    """
    Sync the TWG Leads Council membership.
    Auto-populates from all active TWGs' political and technical leads.
    Requires ADMIN role.
    """
    # Verify this is the leads council
    result = await db.execute(
        select(TWG).where(TWG.id == twg_id)
    )
    council = result.scalar_one_or_none()
    if not council:
        raise HTTPException(status_code=404, detail="TWG not found")
    if council.group_type != "leads_council":
        raise HTTPException(status_code=400, detail="This endpoint is only for leads_council groups")

    sync_result = await _sync_leads_council_membership(db)
    await db.commit()

    return {
        "message": f"Synced leads council: {sync_result['added']} added, {sync_result['removed']} removed. Total members: {sync_result['total_members']}.",
        "synced": sync_result["added"],
        "removed": sync_result["removed"],
        "total_members": sync_result["total_members"]
    }
