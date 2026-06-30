from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload
from typing import List
from datetime import datetime
import uuid

from app.core.database import get_db
from app.models.models import SubGroup, TWG, User, UserRole, Document, subgroup_members, Meeting, ActionItem
from app.schemas.schemas import SubGroupCreate, SubGroupRead, SubGroupUpdate, SubGroupMemberAdd
from app.api.deps import get_current_active_user, filter_confidential_documents, has_twg_access
from app.services.subgroup_health import compute_subgroup_health, compute_subgroup_health_for_id

router = APIRouter(prefix="/twgs", tags=["Subgroups"])


async def _get_twg_or_404(twg_id: uuid.UUID, db: AsyncSession) -> TWG:
    result = await db.execute(
        select(TWG).options(selectinload(TWG.members)).where(TWG.id == twg_id)
    )
    twg = result.scalar_one_or_none()
    if not twg:
        raise HTTPException(status_code=404, detail="TWG not found")
    return twg


async def _check_subgroup_management_access(twg_id: uuid.UUID, current_user: User, db: AsyncSession) -> TWG:
    twg = await _get_twg_or_404(twg_id, db)
    if current_user.role in [UserRole.ADMIN, UserRole.SECRETARIAT_LEAD]:
        return twg
    user_twg_ids = [t.id for t in current_user.twgs]
    if current_user.role == UserRole.TWG_FACILITATOR and twg_id in user_twg_ids:
        return twg
    is_lead = (
        (twg.political_lead_id and twg.political_lead_id == current_user.id) or
        (twg.technical_lead_id and twg.technical_lead_id == current_user.id)
    )
    if is_lead:
        return twg
    raise HTTPException(status_code=403, detail="You do not have permission to manage this TWG's subgroups")


async def _get_subgroup_or_404(sg_id: uuid.UUID, twg_id: uuid.UUID, db: AsyncSession) -> SubGroup:
    result = await db.execute(
        select(SubGroup)
        .options(selectinload(SubGroup.members), selectinload(SubGroup.lead), selectinload(SubGroup.documents))
        .where(SubGroup.id == sg_id, SubGroup.twg_id == twg_id)
    )
    sg = result.scalar_one_or_none()
    if not sg:
        raise HTTPException(status_code=404, detail="Subgroup not found")
    return sg


def _to_user_simple(user: User) -> dict:
    return {"id": str(user.id), "full_name": user.full_name, "email": user.email}


# NOTE: this route intentionally does NOT declare response_model=SubGroupRead.
# It returns every field SubGroupRead declares (unchanged) PLUS additive health
# fields (health_status / last_active_at / health). Pydantic's default
# extra="ignore" on the schema would silently strip those extra keys, so the
# response_model is dropped here to let the additive fields reach the client.
# The shape of every pre-existing key is preserved exactly.
@router.get("/{twg_id}/subgroups/")
async def list_subgroups(
    twg_id: uuid.UUID,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    await _get_twg_or_404(twg_id, db)
    result = await db.execute(
        select(SubGroup)
        .options(selectinload(SubGroup.lead), selectinload(SubGroup.members), selectinload(SubGroup.documents))
        .where(SubGroup.twg_id == twg_id)
        .order_by(SubGroup.created_at)
    )
    subgroups = result.scalars().all()

    # Bulk-fetch meetings + action items attributed to these sub-groups (via the
    # new subgroup_id FK) in two queries, then group in-memory to avoid N+1.
    sg_ids = [sg.id for sg in subgroups]
    meetings_by_sg: dict = {}
    items_by_sg: dict = {}
    if sg_ids:
        m_res = await db.execute(
            select(Meeting).where(Meeting.subgroup_id.in_(sg_ids))
        )
        for m in m_res.scalars().all():
            meetings_by_sg.setdefault(m.subgroup_id, []).append(m)
        ai_res = await db.execute(
            select(ActionItem).where(ActionItem.subgroup_id.in_(sg_ids))
        )
        for ai in ai_res.scalars().all():
            items_by_sg.setdefault(ai.subgroup_id, []).append(ai)

    out = []
    for sg in subgroups:
        health = compute_subgroup_health(
            sg,
            meetings=meetings_by_sg.get(sg.id, []),
            action_items=items_by_sg.get(sg.id, []),
            documents=list(sg.documents),
        )
        d = {
            "id": sg.id,
            "name": sg.name,
            "description": sg.description,
            "twg_id": sg.twg_id,
            "lead_id": sg.lead_id,
            "status": sg.status,
            "created_at": sg.created_at,
            "lead": _to_user_simple(sg.lead) if sg.lead else None,
            "members": [_to_user_simple(m) for m in sg.members],
            "member_count": len(sg.members),
            "document_count": len(sg.documents),
            # --- additive health fields (R4) ---
            "health_status": health["status"],
            "last_active_at": health["last_active_at"],
            "days_since_active": health["days_since_active"],
            "health": health,
        }
        out.append(d)
    return out


@router.post("/{twg_id}/subgroups/", response_model=SubGroupRead, status_code=status.HTTP_201_CREATED)
async def create_subgroup(
    twg_id: uuid.UUID,
    body: SubGroupCreate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    twg = await _check_subgroup_management_access(twg_id, current_user, db)

    # Unique name within TWG
    existing = await db.execute(
        select(SubGroup).where(SubGroup.twg_id == twg_id, SubGroup.name == body.name)
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="A subgroup with this name already exists in this TWG")

    # Validate lead is a TWG member
    if body.lead_id:
        twg_member_ids = {m.id for m in twg.members}
        if body.lead_id not in twg_member_ids:
            raise HTTPException(status_code=400, detail="Subgroup lead must be a member of the parent TWG")

    sg = SubGroup(
        id=uuid.uuid4(),
        name=body.name,
        description=body.description,
        twg_id=twg_id,
        lead_id=body.lead_id,
        status="active",
        created_at=datetime.utcnow(),
    )
    db.add(sg)
    await db.flush()

    # Auto-add lead as member if provided
    if body.lead_id:
        lead_result = await db.execute(select(User).where(User.id == body.lead_id))
        lead_user = lead_result.scalar_one_or_none()
        if lead_user:
            sg.members.append(lead_user)

    await db.commit()
    await db.refresh(sg)

    # Reload with relationships
    sg = await _get_subgroup_or_404(sg.id, twg_id, db)
    return {
        "id": sg.id, "name": sg.name, "description": sg.description,
        "twg_id": sg.twg_id, "lead_id": sg.lead_id, "status": sg.status,
        "created_at": sg.created_at,
        "lead": _to_user_simple(sg.lead) if sg.lead else None,
        "members": [_to_user_simple(m) for m in sg.members],
        "member_count": len(sg.members),
        "document_count": len(sg.documents),
    }


@router.get("/{twg_id}/subgroups/{sg_id}", response_model=SubGroupRead)
async def get_subgroup(
    twg_id: uuid.UUID,
    sg_id: uuid.UUID,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    sg = await _get_subgroup_or_404(sg_id, twg_id, db)
    return {
        "id": sg.id, "name": sg.name, "description": sg.description,
        "twg_id": sg.twg_id, "lead_id": sg.lead_id, "status": sg.status,
        "created_at": sg.created_at,
        "lead": _to_user_simple(sg.lead) if sg.lead else None,
        "members": [_to_user_simple(m) for m in sg.members],
        "member_count": len(sg.members),
        "document_count": len(sg.documents),
    }


@router.get("/{twg_id}/subgroups/{sg_id}/health")
async def get_subgroup_health(
    twg_id: uuid.UUID,
    sg_id: uuid.UUID,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Detailed effectiveness/health signal for a single sub-group (R4).

    Access control: a sub-group's health is only visible to users with access
    to its parent TWG, so health never leaks across TWGs. Reuses the shared
    has_twg_access guard used elsewhere in the platform.
    """
    if not has_twg_access(current_user, twg_id):
        raise HTTPException(
            status_code=403,
            detail="You do not have access to this TWG's sub-groups",
        )
    sg = await _get_subgroup_or_404(sg_id, twg_id, db)
    health = await compute_subgroup_health_for_id(db, sg)
    return {
        "id": str(sg.id),
        "twg_id": str(sg.twg_id),
        "name": sg.name,
        "lead": _to_user_simple(sg.lead) if sg.lead else None,
        **health,
    }


@router.patch("/{twg_id}/subgroups/{sg_id}", response_model=SubGroupRead)
async def update_subgroup(
    twg_id: uuid.UUID,
    sg_id: uuid.UUID,
    body: SubGroupUpdate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    twg = await _check_subgroup_management_access(twg_id, current_user, db)
    sg = await _get_subgroup_or_404(sg_id, twg_id, db)

    if body.name is not None:
        # Check name uniqueness (exclude self)
        existing = await db.execute(
            select(SubGroup).where(
                SubGroup.twg_id == twg_id,
                SubGroup.name == body.name,
                SubGroup.id != sg_id,
            )
        )
        if existing.scalar_one_or_none():
            raise HTTPException(status_code=409, detail="A subgroup with this name already exists in this TWG")
        sg.name = body.name

    if body.description is not None:
        sg.description = body.description

    if body.status is not None:
        sg.status = body.status

    if body.lead_id is not None:
        # New lead must be a subgroup member
        member_ids = {m.id for m in sg.members}
        if body.lead_id not in member_ids:
            raise HTTPException(status_code=400, detail="Subgroup lead must be a member of the subgroup")
        sg.lead_id = body.lead_id

    await db.commit()
    await db.refresh(sg)
    sg = await _get_subgroup_or_404(sg_id, twg_id, db)
    return {
        "id": sg.id, "name": sg.name, "description": sg.description,
        "twg_id": sg.twg_id, "lead_id": sg.lead_id, "status": sg.status,
        "created_at": sg.created_at,
        "lead": _to_user_simple(sg.lead) if sg.lead else None,
        "members": [_to_user_simple(m) for m in sg.members],
        "member_count": len(sg.members),
        "document_count": len(sg.documents),
    }


@router.delete("/{twg_id}/subgroups/{sg_id}", status_code=status.HTTP_200_OK)
async def delete_subgroup(
    twg_id: uuid.UUID,
    sg_id: uuid.UUID,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    await _check_subgroup_management_access(twg_id, current_user, db)
    sg = await _get_subgroup_or_404(sg_id, twg_id, db)

    # Unlink documents (set subgroup_id to null)
    from sqlalchemy import update as sa_update
    await db.execute(
        sa_update(Document).where(Document.subgroup_id == sg_id).values(subgroup_id=None)
    )

    await db.delete(sg)
    await db.commit()
    return {"message": f"Subgroup '{sg.name}' deleted. Documents have been unlinked."}


# --- Member routes ---

@router.get("/{twg_id}/subgroups/{sg_id}/members")
async def list_subgroup_members(
    twg_id: uuid.UUID,
    sg_id: uuid.UUID,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    sg = await _get_subgroup_or_404(sg_id, twg_id, db)
    return [_to_user_simple(m) for m in sg.members]


@router.post("/{twg_id}/subgroups/{sg_id}/members", status_code=status.HTTP_201_CREATED)
async def add_subgroup_member(
    twg_id: uuid.UUID,
    sg_id: uuid.UUID,
    body: SubGroupMemberAdd,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    twg = await _check_subgroup_management_access(twg_id, current_user, db)
    sg = await _get_subgroup_or_404(sg_id, twg_id, db)

    # Must be a TWG member first
    twg_member_ids = {m.id for m in twg.members}
    if body.user_id not in twg_member_ids:
        raise HTTPException(status_code=400, detail="User must be a TWG member before joining a subgroup")

    # No duplicate membership
    current_member_ids = {m.id for m in sg.members}
    if body.user_id in current_member_ids:
        raise HTTPException(status_code=409, detail="User is already a member of this subgroup")

    user_result = await db.execute(select(User).where(User.id == body.user_id))
    user = user_result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    sg.members.append(user)
    await db.commit()
    return {"message": f"{user.full_name} added to {sg.name}."}


@router.delete("/{twg_id}/subgroups/{sg_id}/members/{user_id}", status_code=status.HTTP_200_OK)
async def remove_subgroup_member(
    twg_id: uuid.UUID,
    sg_id: uuid.UUID,
    user_id: uuid.UUID,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    await _check_subgroup_management_access(twg_id, current_user, db)
    sg = await _get_subgroup_or_404(sg_id, twg_id, db)

    # Cannot remove lead without reassigning
    if sg.lead_id == user_id:
        raise HTTPException(status_code=400, detail="Reassign the subgroup lead before removing this member")

    member_to_remove = next((m for m in sg.members if m.id == user_id), None)
    if not member_to_remove:
        raise HTTPException(status_code=404, detail="User is not a member of this subgroup")

    sg.members.remove(member_to_remove)
    await db.commit()
    return {"message": f"{member_to_remove.full_name} removed from {sg.name}."}


# --- Document routes ---

@router.get("/{twg_id}/subgroups/{sg_id}/documents")
async def list_subgroup_documents(
    twg_id: uuid.UUID,
    sg_id: uuid.UUID,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    await _get_subgroup_or_404(sg_id, twg_id, db)
    result = await db.execute(
        select(Document).where(Document.subgroup_id == sg_id).order_by(Document.created_at.desc())
    )
    docs = result.scalars().all()
    # P0-9: members never receive confidential documents
    docs = filter_confidential_documents(current_user, docs)
    return [
        {
            "id": str(d.id),
            "file_name": d.file_name,
            "file_type": d.file_type,
            "created_at": d.created_at.isoformat(),
            "is_confidential": d.is_confidential,
        }
        for d in docs
    ]
