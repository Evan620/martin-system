from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload
from typing import List
import uuid

from app.core.database import get_db
from app.models.models import TWG, User, UserRole, Meeting, Project, ActionItem, Document, MeetingStatus, ActionItemStatus
from app.schemas.schemas import TWGCreate, TWGRead, TWGUpdate
from app.api.deps import get_current_active_user, require_admin, require_facilitator

router = APIRouter(prefix="/twgs", tags=["TWGs"])

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
        ]
        
        # We will need to perform separate queries or use scalar subqueries for stats.
        # For simplicity and clarity in this iteration, let's fetch IDs and then load stats.
        # A more optimized approach would use group_by and multiple queries.
        
        # Hide non-core TWGs per client request (only show 4: energy, agri, minerals, digital)
        from app.models.models import TWGPillar
        HIDDEN_PILLARS = {TWGPillar.protocol_logistics, TWGPillar.resource_mobilization}

        result = await db.execute(
            select(TWG)
            .where(TWG.pillar.notin_(HIDDEN_PILLARS))
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
    
    # Resources
    docs_res = await db.execute(
        select(func.count(Document.id)).where(Document.twg_id == twg_id)
    )
    resources_count = docs_res.scalar() or 0
    
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
            selectinload(TWG.action_items),
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
    for key, value in update_data.items():
        setattr(db_twg, key, value)
    
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
    await db.commit()

    return {"message": f"{member_to_remove.full_name} has been removed from {twg.name}."}
