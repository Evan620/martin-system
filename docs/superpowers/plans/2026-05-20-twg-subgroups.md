# TWG Subgroups Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add the ability to create named sub-groups within any TWG workspace, each with its own member list and documents, sharing the parent TWG's meetings and agent.

**Architecture:** New `SubGroup` SQLAlchemy model + `subgroup_members` join table + nullable `subgroup_id` FK on `Document`. A dedicated FastAPI router at `/twgs/{twg_id}/subgroups/` handles CRUD. The frontend adds a "Subgroups" tab to `TwgWorkspace.tsx` backed by two new components: `SubgroupsManager` (list) and `SubgroupDetail` (members + docs).

**Tech Stack:** FastAPI, SQLAlchemy async (Mapped/mapped_column), Alembic, Pydantic v2, React 18, TypeScript, Tailwind CSS, Axios.

---

## File Map

| Action | Path |
|---|---|
| Modify | `backend/app/models/models.py` |
| Create | `backend/alembic/versions/add_subgroups_20260520.py` |
| Modify | `backend/app/schemas/schemas.py` |
| Create | `backend/app/api/routes/subgroups.py` |
| Modify | `backend/app/api/routes/twgs.py` (cascade removal only) |
| Modify | `backend/app/main.py` |
| Modify | `frontend/src/services/api.ts` |
| Create | `frontend/src/components/workspace/SubgroupsManager.tsx` |
| Create | `frontend/src/components/workspace/SubgroupDetail.tsx` |
| Modify | `frontend/src/pages/workspace/TwgWorkspace.tsx` |

---

## Task 1: Add SubGroup model to models.py

**Files:**
- Modify: `backend/app/models/models.py`

- [ ] **Step 1: Add `subgroup_members` association table after `twg_members` (around line 171)**

In `backend/app/models/models.py`, after the `twg_members` Table block (after line 171), add:

```python
subgroup_members = Table(
    "subgroup_members",
    Base.metadata,
    Column("subgroup_id", Uuid, ForeignKey("subgroups.id", ondelete="CASCADE"), primary_key=True),
    Column("user_id", Uuid, ForeignKey("users.id", ondelete="CASCADE"), primary_key=True),
    Column("joined_at", DateTime, default=datetime.utcnow),
    extend_existing=True
)
```

- [ ] **Step 2: Add `SubGroup` class after the `TWG` class (after line 318)**

After the closing of the `TWG` class (after the `dependencies_as_target` relationship), add:

```python
class SubGroup(Base):
    __tablename__ = "subgroups"
    __table_args__ = {'extend_existing': True}

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(255))
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    twg_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("twgs.id", ondelete="CASCADE"))
    lead_id: Mapped[Optional[uuid.UUID]] = mapped_column(Uuid, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    status: Mapped[str] = mapped_column(String(50), default="active")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # Relationships
    twg: Mapped["TWG"] = relationship("TWG", back_populates="subgroups")
    lead: Mapped[Optional["User"]] = relationship("User", foreign_keys=[lead_id])
    members: Mapped[List["User"]] = relationship("User", secondary=subgroup_members)
    documents: Mapped[List["Document"]] = relationship("Document", back_populates="subgroup")
```

- [ ] **Step 3: Add `subgroups` relationship to the `TWG` class**

Inside the `TWG` class, after the `documents` relationship line (line 313), add:

```python
    subgroups: Mapped[List["SubGroup"]] = relationship("SubGroup", back_populates="twg", cascade="all, delete-orphan")
```

- [ ] **Step 4: Add `subgroup_id` FK + relationship to the `Document` class**

In the `Document` class (around line 628), add a column after the `project_id` FK:

```python
    subgroup_id: Mapped[Optional[uuid.UUID]] = mapped_column(Uuid, ForeignKey("subgroups.id", ondelete="SET NULL"), nullable=True)
```

And after the `project` relationship (line 643), add:

```python
    subgroup: Mapped[Optional["SubGroup"]] = relationship("SubGroup", back_populates="documents")
```

- [ ] **Step 5: Add `SubGroup` to the models.py imports used in routes**

Verify that `SubGroup` and `subgroup_members` will be importable. No extra step needed — they are defined in the same file.

- [ ] **Step 6: Commit**

```bash
git add backend/app/models/models.py
git commit -m "feat: add SubGroup model and subgroup_members association table"
```

---

## Task 2: Alembic migration

**Files:**
- Create: `backend/alembic/versions/add_subgroups_20260520.py`

- [ ] **Step 1: Create the migration file**

Create `backend/alembic/versions/add_subgroups_20260520.py` with this content:

```python
"""add subgroups tables and document subgroup_id

Revision ID: add_subgroups_20260520
Revises: eaa36aa892bd
Create Date: 2026-05-20
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

revision = 'add_subgroups_20260520'
down_revision = 'eaa36aa892bd'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'subgroups',
        sa.Column('id', UUID(as_uuid=True), primary_key=True),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('description', sa.Text, nullable=True),
        sa.Column('twg_id', UUID(as_uuid=True), sa.ForeignKey('twgs.id', ondelete='CASCADE'), nullable=False),
        sa.Column('lead_id', UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),
        sa.Column('status', sa.String(50), nullable=False, server_default='active'),
        sa.Column('created_at', sa.DateTime, nullable=False, server_default=sa.func.now()),
    )
    op.create_index('ix_subgroups_twg_id', 'subgroups', ['twg_id'])

    op.create_table(
        'subgroup_members',
        sa.Column('subgroup_id', UUID(as_uuid=True), sa.ForeignKey('subgroups.id', ondelete='CASCADE'), primary_key=True),
        sa.Column('user_id', UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='CASCADE'), primary_key=True),
        sa.Column('joined_at', sa.DateTime, nullable=False, server_default=sa.func.now()),
    )

    op.add_column('documents', sa.Column(
        'subgroup_id', UUID(as_uuid=True),
        sa.ForeignKey('subgroups.id', ondelete='SET NULL'),
        nullable=True
    ))


def downgrade():
    op.drop_column('documents', 'subgroup_id')
    op.drop_table('subgroup_members')
    op.drop_index('ix_subgroups_twg_id', table_name='subgroups')
    op.drop_table('subgroups')
```

- [ ] **Step 2: Run the migration**

```bash
cd backend
source venv/bin/activate
alembic upgrade head
```

Expected output ends with: `Running upgrade eaa36aa892bd -> add_subgroups_20260520`

- [ ] **Step 3: Verify tables exist**

```bash
python3 -c "
import asyncio
from app.core.database import engine
from sqlalchemy import text

async def check():
    async with engine.connect() as conn:
        result = await conn.execute(text(\"SELECT table_name FROM information_schema.tables WHERE table_name IN ('subgroups','subgroup_members')\"))
        print([r[0] for r in result.fetchall()])

asyncio.run(check())
"
```

Expected: `['subgroups', 'subgroup_members']`

- [ ] **Step 4: Commit**

```bash
git add backend/alembic/versions/add_subgroups_20260520.py
git commit -m "feat: alembic migration — add subgroups, subgroup_members, documents.subgroup_id"
```

---

## Task 3: Pydantic schemas

**Files:**
- Modify: `backend/app/schemas/schemas.py`

- [ ] **Step 1: Add SubGroup schemas after the TWG schemas (after the `TWGRead` class)**

In `backend/app/schemas/schemas.py`, after the `TWGRead` class, add:

```python
# --- SubGroup Schemas ---

class SubGroupBase(SchemaBase):
    name: str
    description: Optional[str] = None
    lead_id: Optional[uuid.UUID] = None

class SubGroupCreate(SubGroupBase):
    pass

class SubGroupUpdate(SchemaBase):
    name: Optional[str] = None
    description: Optional[str] = None
    lead_id: Optional[uuid.UUID] = None
    status: Optional[str] = None

class SubGroupMemberAdd(SchemaBase):
    user_id: uuid.UUID

class SubGroupRead(SubGroupBase):
    id: uuid.UUID
    twg_id: uuid.UUID
    status: str
    created_at: datetime
    lead: Optional["UserSimple"] = None
    members: List["UserSimple"] = []
    member_count: int = 0
    document_count: int = 0
```

- [ ] **Step 2: Verify the file is valid Python**

```bash
cd backend
source venv/bin/activate
python3 -c "from app.schemas.schemas import SubGroupRead, SubGroupCreate, SubGroupUpdate, SubGroupMemberAdd; print('OK')"
```

Expected: `OK`

- [ ] **Step 3: Commit**

```bash
git add backend/app/schemas/schemas.py
git commit -m "feat: add SubGroup pydantic schemas"
```

---

## Task 4: Subgroups API router

**Files:**
- Create: `backend/app/api/routes/subgroups.py`

- [ ] **Step 1: Create the router file**

Create `backend/app/api/routes/subgroups.py`:

```python
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload
from typing import List
from datetime import datetime
import uuid

from app.core.database import get_db
from app.models.models import SubGroup, TWG, User, UserRole, Document, subgroup_members
from app.schemas.schemas import SubGroupCreate, SubGroupRead, SubGroupUpdate, SubGroupMemberAdd
from app.api.deps import get_current_active_user

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


@router.get("/{twg_id}/subgroups/", response_model=List[SubGroupRead])
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
    out = []
    for sg in subgroups:
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
```

- [ ] **Step 2: Verify the router imports cleanly**

```bash
cd backend
source venv/bin/activate
python3 -c "from app.api.routes.subgroups import router; print('OK')"
```

Expected: `OK`

- [ ] **Step 3: Commit**

```bash
git add backend/app/api/routes/subgroups.py
git commit -m "feat: add subgroups API router with CRUD, member management, documents"
```

---

## Task 5: Register router + cascade TWG member removal

**Files:**
- Modify: `backend/app/main.py`
- Modify: `backend/app/api/routes/twgs.py`

- [ ] **Step 1: Register the subgroups router in main.py**

In `backend/app/main.py`, find the import line (line 24):

```python
from app.api.routes import twgs, meetings, auth, ...
```

Add `subgroups` to that import:

```python
from app.api.routes import twgs, meetings, auth, projects, action_items, documents, audit, agents, dashboard, users, notifications, supervisor, debug, pipeline, conflicts, settings as settings_router, shared_documents, organization_invitations, public_invitations, recurring_meetings, subgroups
```

Then after `app.include_router(twgs.router, ...)` (line 237), add:

```python
app.include_router(subgroups.router, prefix=f"{settings.API_V1_STR}")
```

- [ ] **Step 2: Cascade subgroup removal when a TWG member is removed**

In `backend/app/api/routes/twgs.py`, find the `remove_twg_member` function. After the line `twg.members.remove(member_to_remove)` and before `await db.commit()`, add:

```python
    # Remove the user from all subgroups in this TWG
    from app.models.models import SubGroup
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
```

Also add `SubGroup` to the import at the top of `twgs.py`:

```python
from app.models.models import TWG, User, UserRole, Meeting, Project, ActionItem, Document, MeetingStatus, ActionItemStatus, MeetingParticipant, RsvpStatus, SubGroup
```

- [ ] **Step 3: Smoke-test the server starts cleanly**

```bash
cd backend
source venv/bin/activate
venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload &
sleep 3
curl -s http://127.0.0.1:8000/api/v1/docs | grep -c "subgroup" && echo "Router registered OK"
kill %1
```

Expected: prints a number > 0 and `Router registered OK`

- [ ] **Step 4: Commit**

```bash
git add backend/app/main.py backend/app/api/routes/twgs.py
git commit -m "feat: register subgroups router and cascade subgroup removal on TWG member remove"
```

---

## Task 6: Frontend API service

**Files:**
- Modify: `frontend/src/services/api.ts`

- [ ] **Step 1: Add `subgroups` export after the `twgs` export (after line 178)**

In `frontend/src/services/api.ts`, after the closing `};` of the `twgs` export, add:

```typescript
export const subgroups = {
    list: (twgId: string) =>
        api.get(`/twgs/${twgId}/subgroups/`),
    create: (twgId: string, data: { name: string; description?: string; lead_id?: string }) =>
        api.post(`/twgs/${twgId}/subgroups/`, data),
    get: (twgId: string, sgId: string) =>
        api.get(`/twgs/${twgId}/subgroups/${sgId}`),
    update: (twgId: string, sgId: string, data: { name?: string; description?: string; lead_id?: string; status?: string }) =>
        api.patch(`/twgs/${twgId}/subgroups/${sgId}`, data),
    delete: (twgId: string, sgId: string) =>
        api.delete(`/twgs/${twgId}/subgroups/${sgId}`),
    listMembers: (twgId: string, sgId: string) =>
        api.get(`/twgs/${twgId}/subgroups/${sgId}/members`),
    addMember: (twgId: string, sgId: string, userId: string) =>
        api.post(`/twgs/${twgId}/subgroups/${sgId}/members`, { user_id: userId }),
    removeMember: (twgId: string, sgId: string, userId: string) =>
        api.delete(`/twgs/${twgId}/subgroups/${sgId}/members/${userId}`),
    listDocuments: (twgId: string, sgId: string) =>
        api.get(`/twgs/${twgId}/subgroups/${sgId}/documents`),
};
```

- [ ] **Step 2: Verify TypeScript compiles**

```bash
cd frontend
npm run build 2>&1 | tail -5
```

Expected: no TypeScript errors related to the new export.

- [ ] **Step 3: Commit**

```bash
git add frontend/src/services/api.ts
git commit -m "feat: add subgroups API service namespace"
```

---

## Task 7: SubgroupsManager component (list view)

**Files:**
- Create: `frontend/src/components/workspace/SubgroupsManager.tsx`

- [ ] **Step 1: Create the component**

Create `frontend/src/components/workspace/SubgroupsManager.tsx`:

```tsx
import { useState, useEffect } from 'react'
import { subgroups as subgroupsApi, twgs as twgsApi } from '../../services/api'

interface SubGroup {
    id: string
    name: string
    description: string | null
    lead: { id: string; full_name: string; email: string } | null
    member_count: number
    document_count: number
    status: string
}

interface SubgroupsManagerProps {
    twgId: string
    canEdit: boolean
    onOpenSubgroup: (sg: SubGroup) => void
}

export default function SubgroupsManager({ twgId, canEdit, onOpenSubgroup }: SubgroupsManagerProps) {
    const [sgList, setSgList] = useState<SubGroup[]>([])
    const [loading, setLoading] = useState(true)
    const [showCreate, setShowCreate] = useState(false)
    const [newName, setNewName] = useState('')
    const [newDesc, setNewDesc] = useState('')
    const [creating, setCreating] = useState(false)
    const [error, setError] = useState<string | null>(null)

    const load = async () => {
        try {
            setLoading(true)
            const res = await subgroupsApi.list(twgId)
            setSgList(res.data)
        } catch {
            setError('Failed to load subgroups.')
        } finally {
            setLoading(false)
        }
    }

    useEffect(() => { load() }, [twgId])

    const handleCreate = async () => {
        if (!newName.trim()) return
        try {
            setCreating(true)
            setError(null)
            await subgroupsApi.create(twgId, { name: newName.trim(), description: newDesc.trim() || undefined })
            setNewName('')
            setNewDesc('')
            setShowCreate(false)
            await load()
        } catch (e: any) {
            setError(e.response?.data?.detail || 'Failed to create subgroup.')
        } finally {
            setCreating(false)
        }
    }

    if (loading) {
        return <p className="text-slate-500 text-sm py-6">Loading subgroups...</p>
    }

    return (
        <div className="space-y-4">
            {/* Header */}
            <div className="flex items-center justify-between">
                <h3 className="text-lg font-display font-bold text-slate-900 dark:text-white">
                    Subgroups <span className="text-slate-400 font-normal text-sm ml-1">({sgList.length})</span>
                </h3>
                {canEdit && (
                    <button
                        onClick={() => setShowCreate(!showCreate)}
                        className="text-sm font-bold text-blue-600 hover:text-blue-500 transition-colors uppercase tracking-widest"
                    >
                        {showCreate ? 'Cancel' : '+ New Subgroup'}
                    </button>
                )}
            </div>

            {/* Create form */}
            {showCreate && (
                <div className="bg-slate-50 dark:bg-slate-800/50 rounded-xl p-4 space-y-3 border border-slate-200 dark:border-slate-700">
                    <input
                        type="text"
                        placeholder="Subgroup name *"
                        value={newName}
                        onChange={e => setNewName(e.target.value)}
                        className="w-full px-3 py-2 rounded-lg border border-slate-300 dark:border-slate-600 bg-white dark:bg-slate-900 text-sm text-slate-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-blue-500"
                    />
                    <input
                        type="text"
                        placeholder="Description (optional)"
                        value={newDesc}
                        onChange={e => setNewDesc(e.target.value)}
                        className="w-full px-3 py-2 rounded-lg border border-slate-300 dark:border-slate-600 bg-white dark:bg-slate-900 text-sm text-slate-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-blue-500"
                    />
                    {error && <p className="text-red-500 text-xs">{error}</p>}
                    <div className="flex gap-2">
                        <button
                            onClick={handleCreate}
                            disabled={creating || !newName.trim()}
                            className="px-4 py-2 bg-blue-600 text-white text-sm font-bold rounded-lg hover:bg-blue-500 disabled:opacity-50 transition-colors"
                        >
                            {creating ? 'Creating...' : 'Create'}
                        </button>
                        <button
                            onClick={() => { setShowCreate(false); setError(null) }}
                            className="px-4 py-2 text-sm font-bold text-slate-500 hover:text-slate-700 transition-colors"
                        >
                            Cancel
                        </button>
                    </div>
                </div>
            )}

            {/* Empty state */}
            {sgList.length === 0 && !showCreate && (
                <div className="text-center py-12 text-slate-400">
                    <p className="text-sm">No subgroups yet.</p>
                    {canEdit && (
                        <p className="text-xs mt-1">Click "+ New Subgroup" to create one.</p>
                    )}
                </div>
            )}

            {/* Subgroup cards */}
            {sgList.map(sg => (
                <div
                    key={sg.id}
                    className="flex items-center justify-between p-4 rounded-xl bg-white dark:bg-slate-800/50 border border-slate-100 dark:border-slate-700 hover:border-blue-300 dark:hover:border-blue-500 transition-all group"
                >
                    <div className="min-w-0">
                        <div className="font-bold text-slate-900 dark:text-white group-hover:text-blue-600 transition-colors truncate">
                            {sg.name}
                        </div>
                        <div className="text-xs text-slate-400 mt-0.5 flex items-center gap-2 flex-wrap">
                            {sg.lead && <span>Lead: {sg.lead.full_name}</span>}
                            <span>·</span>
                            <span>{sg.member_count} member{sg.member_count !== 1 ? 's' : ''}</span>
                            <span>·</span>
                            <span>{sg.document_count} doc{sg.document_count !== 1 ? 's' : ''}</span>
                        </div>
                        {sg.description && (
                            <p className="text-xs text-slate-500 mt-1 truncate max-w-md">{sg.description}</p>
                        )}
                    </div>
                    <div className="flex items-center gap-3 ml-4 shrink-0">
                        <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${sg.status === 'active' ? 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400' : 'bg-slate-100 text-slate-500'}`}>
                            {sg.status}
                        </span>
                        <button
                            onClick={() => onOpenSubgroup(sg)}
                            className="text-sm font-bold text-blue-600 hover:text-blue-500 transition-colors whitespace-nowrap"
                        >
                            Open →
                        </button>
                    </div>
                </div>
            ))}
        </div>
    )
}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/components/workspace/SubgroupsManager.tsx
git commit -m "feat: add SubgroupsManager list component"
```

---

## Task 8: SubgroupDetail component (detail view)

**Files:**
- Create: `frontend/src/components/workspace/SubgroupDetail.tsx`

- [ ] **Step 1: Create the component**

Create `frontend/src/components/workspace/SubgroupDetail.tsx`:

```tsx
import { useState, useEffect } from 'react'
import { subgroups as subgroupsApi, twgs as twgsApi } from '../../services/api'

interface SubGroupMember {
    id: string
    full_name: string
    email: string
}

interface SubGroupDoc {
    id: string
    file_name: string
    file_type: string
    created_at: string
    is_confidential: boolean
}

interface SubGroup {
    id: string
    name: string
    description: string | null
    lead_id: string | null
    lead: SubGroupMember | null
    members: SubGroupMember[]
    member_count: number
    document_count: number
    status: string
}

interface SubgroupDetailProps {
    twgId: string
    twgName: string
    subgroup: SubGroup
    canEdit: boolean
    onBack: () => void
}

export default function SubgroupDetail({ twgId, twgName, subgroup: initialSubgroup, canEdit, onBack }: SubgroupDetailProps) {
    const [activeTab, setActiveTab] = useState<'members' | 'documents'>('members')
    const [sg, setSg] = useState<SubGroup>(initialSubgroup)
    const [members, setMembers] = useState<SubGroupMember[]>([])
    const [docs, setDocs] = useState<SubGroupDoc[]>([])
    const [twgMembers, setTwgMembers] = useState<SubGroupMember[]>([])
    const [loadingMembers, setLoadingMembers] = useState(true)
    const [loadingDocs, setLoadingDocs] = useState(false)
    const [showAddMember, setShowAddMember] = useState(false)
    const [selectedUserId, setSelectedUserId] = useState('')
    const [adding, setAdding] = useState(false)
    const [error, setError] = useState<string | null>(null)

    const loadMembers = async () => {
        try {
            setLoadingMembers(true)
            const res = await subgroupsApi.listMembers(twgId, sg.id)
            setMembers(res.data)
        } catch {
            setError('Failed to load members.')
        } finally {
            setLoadingMembers(false)
        }
    }

    const loadDocs = async () => {
        try {
            setLoadingDocs(true)
            const res = await subgroupsApi.listDocuments(twgId, sg.id)
            setDocs(res.data)
        } catch {
            setError('Failed to load documents.')
        } finally {
            setLoadingDocs(false)
        }
    }

    const loadTwgMembers = async () => {
        try {
            const res = await twgsApi.listMembers(twgId)
            setTwgMembers(res.data)
        } catch {}
    }

    useEffect(() => {
        loadMembers()
        loadTwgMembers()
    }, [sg.id])

    useEffect(() => {
        if (activeTab === 'documents') loadDocs()
    }, [activeTab])

    const availableToAdd = twgMembers.filter(m => !members.some(sm => sm.id === m.id))

    const handleAddMember = async () => {
        if (!selectedUserId) return
        try {
            setAdding(true)
            setError(null)
            await subgroupsApi.addMember(twgId, sg.id, selectedUserId)
            setSelectedUserId('')
            setShowAddMember(false)
            await loadMembers()
        } catch (e: any) {
            setError(e.response?.data?.detail || 'Failed to add member.')
        } finally {
            setAdding(false)
        }
    }

    const handleRemoveMember = async (userId: string) => {
        try {
            setError(null)
            await subgroupsApi.removeMember(twgId, sg.id, userId)
            await loadMembers()
        } catch (e: any) {
            setError(e.response?.data?.detail || 'Failed to remove member.')
        }
    }

    return (
        <div className="space-y-4">
            {/* Back link */}
            <button
                onClick={onBack}
                className="text-sm text-blue-600 hover:text-blue-500 font-bold transition-colors"
            >
                ← Back to Subgroups
            </button>

            {/* Header */}
            <div>
                <h3 className="text-xl font-display font-bold text-slate-900 dark:text-white">{sg.name}</h3>
                <p className="text-xs text-slate-400 mt-1">
                    {sg.lead && <>Lead: {sg.lead.full_name} &nbsp;·&nbsp; </>}
                    {twgName}
                </p>
                {sg.description && (
                    <p className="text-sm text-slate-500 mt-2 italic">{sg.description}</p>
                )}
            </div>

            {/* Inner tabs */}
            <div className="border-b border-slate-200 dark:border-slate-700">
                <div className="flex gap-6">
                    {(['members', 'documents'] as const).map(tab => (
                        <button
                            key={tab}
                            onClick={() => setActiveTab(tab)}
                            className={`pb-3 text-sm font-bold transition-all border-b-2 capitalize ${activeTab === tab
                                ? 'border-blue-600 text-blue-600 dark:text-blue-400'
                                : 'border-transparent text-slate-500 hover:text-slate-700 dark:hover:text-slate-300'
                            }`}
                        >
                            {tab}
                        </button>
                    ))}
                </div>
            </div>

            {error && (
                <p className="text-red-500 text-sm bg-red-50 dark:bg-red-900/20 px-3 py-2 rounded-lg">{error}</p>
            )}

            {/* Members tab */}
            {activeTab === 'members' && (
                <div className="space-y-3">
                    <div className="flex items-center justify-between">
                        <span className="text-sm text-slate-500">{members.length} member{members.length !== 1 ? 's' : ''}</span>
                        {canEdit && (
                            <button
                                onClick={() => setShowAddMember(!showAddMember)}
                                className="text-sm font-bold text-blue-600 hover:text-blue-500 transition-colors uppercase tracking-widest"
                            >
                                {showAddMember ? 'Cancel' : '+ Add Member'}
                            </button>
                        )}
                    </div>

                    {/* Add member form */}
                    {showAddMember && (
                        <div className="bg-slate-50 dark:bg-slate-800/50 rounded-xl p-4 space-y-3 border border-slate-200 dark:border-slate-700">
                            <p className="text-xs text-slate-500">Select from existing TWG members:</p>
                            <select
                                value={selectedUserId}
                                onChange={e => setSelectedUserId(e.target.value)}
                                className="w-full px-3 py-2 rounded-lg border border-slate-300 dark:border-slate-600 bg-white dark:bg-slate-900 text-sm text-slate-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-blue-500"
                            >
                                <option value="">-- Select a member --</option>
                                {availableToAdd.map(m => (
                                    <option key={m.id} value={m.id}>{m.full_name} ({m.email})</option>
                                ))}
                            </select>
                            {availableToAdd.length === 0 && (
                                <p className="text-xs text-slate-400">All TWG members are already in this subgroup.</p>
                            )}
                            <button
                                onClick={handleAddMember}
                                disabled={adding || !selectedUserId}
                                className="px-4 py-2 bg-blue-600 text-white text-sm font-bold rounded-lg hover:bg-blue-500 disabled:opacity-50 transition-colors"
                            >
                                {adding ? 'Adding...' : 'Add'}
                            </button>
                        </div>
                    )}

                    {/* Member list */}
                    {loadingMembers ? (
                        <p className="text-slate-500 text-sm">Loading...</p>
                    ) : members.length === 0 ? (
                        <p className="text-slate-400 text-sm text-center py-8">No members yet.</p>
                    ) : (
                        <div className="space-y-2">
                            {members.map(m => (
                                <div key={m.id} className="flex items-center justify-between px-4 py-3 rounded-xl bg-white dark:bg-slate-800/50 border border-slate-100 dark:border-slate-700">
                                    <div>
                                        <span className="text-sm font-medium text-slate-900 dark:text-white">{m.full_name}</span>
                                        {sg.lead_id === m.id && (
                                            <span className="ml-2 text-xs px-2 py-0.5 rounded-full bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-400 font-medium">Lead</span>
                                        )}
                                        <p className="text-xs text-slate-400">{m.email}</p>
                                    </div>
                                    {canEdit && sg.lead_id !== m.id && (
                                        <button
                                            onClick={() => handleRemoveMember(m.id)}
                                            className="text-xs text-red-500 hover:text-red-400 font-medium transition-colors"
                                        >
                                            Remove
                                        </button>
                                    )}
                                </div>
                            ))}
                        </div>
                    )}
                </div>
            )}

            {/* Documents tab */}
            {activeTab === 'documents' && (
                <div className="space-y-2">
                    {loadingDocs ? (
                        <p className="text-slate-500 text-sm">Loading...</p>
                    ) : docs.length === 0 ? (
                        <p className="text-slate-400 text-sm text-center py-8">No documents in this subgroup yet.</p>
                    ) : (
                        docs.map(doc => (
                            <div key={doc.id} className="flex items-center justify-between px-4 py-3 rounded-xl bg-white dark:bg-slate-800/50 border border-slate-100 dark:border-slate-700">
                                <div>
                                    <p className="text-sm font-medium text-slate-900 dark:text-white">{doc.file_name}</p>
                                    <p className="text-xs text-slate-400">{doc.file_type} · {new Date(doc.created_at).toLocaleDateString()}</p>
                                </div>
                                {doc.is_confidential && (
                                    <span className="text-xs text-slate-400 font-medium">Confidential</span>
                                )}
                            </div>
                        ))
                    )}
                </div>
            )}
        </div>
    )
}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/components/workspace/SubgroupDetail.tsx
git commit -m "feat: add SubgroupDetail component with Members and Documents tabs"
```

---

## Task 9: Wire Subgroups tab into TwgWorkspace

**Files:**
- Modify: `frontend/src/pages/workspace/TwgWorkspace.tsx`

- [ ] **Step 1: Add imports at the top of TwgWorkspace.tsx**

After the `TwgMemberManager` import, add:

```tsx
import SubgroupsManager from '../../components/workspace/SubgroupsManager'
import SubgroupDetail from '../../components/workspace/SubgroupDetail'
```

- [ ] **Step 2: Expand the `activeTab` type and add subgroup state**

Change line 80 from:

```tsx
const [activeTab, setActiveTab] = useState<'overview' | 'factory' | 'members'>('overview');
```

to:

```tsx
const [activeTab, setActiveTab] = useState<'overview' | 'factory' | 'members' | 'subgroups'>('overview');
const [activeSubgroup, setActiveSubgroup] = useState<any>(null);
```

- [ ] **Step 3: Add the Subgroups tab button in the tab bar**

In the tab bar `<div className="flex gap-6">` (around line 232), after the Members button and before the closing `</div>`, add:

```tsx
                            <button
                                onClick={() => { setActiveTab('subgroups'); setActiveSubgroup(null); }}
                                className={`pb-3 text-sm font-bold transition-all border-b-2 ${activeTab === 'subgroups'
                                    ? 'border-blue-600 text-blue-600 dark:text-blue-400'
                                    : 'border-transparent text-slate-500 hover:text-slate-700 dark:hover:text-slate-300'
                                    }`}
                            >
                                Subgroups
                            </button>
```

- [ ] **Step 4: Add the Subgroups tab content panel**

After the `{activeTab === 'members' && ...}` block (after line 451), add:

```tsx
                    {activeTab === 'subgroups' && (
                        activeSubgroup ? (
                            <SubgroupDetail
                                twgId={twgId}
                                twgName={twg?.name || ''}
                                subgroup={activeSubgroup}
                                canEdit={canManageMembers}
                                onBack={() => setActiveSubgroup(null)}
                            />
                        ) : (
                            <SubgroupsManager
                                twgId={twgId}
                                canEdit={canManageMembers}
                                onOpenSubgroup={(sg) => setActiveSubgroup(sg)}
                            />
                        )
                    )}
```

- [ ] **Step 5: Build the frontend and check for TypeScript errors**

```bash
cd frontend
npm run build 2>&1 | tail -10
```

Expected: build succeeds with no TypeScript errors.

- [ ] **Step 6: Commit**

```bash
git add frontend/src/pages/workspace/TwgWorkspace.tsx
git commit -m "feat: add Subgroups tab to TWG workspace"
```

---

## Verification Checklist

After all tasks are complete, verify end-to-end:

- [ ] Backend starts without error: `venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8000`
- [ ] `GET /api/v1/twgs/{twg_id}/subgroups/` returns `[]` for a TWG with no subgroups
- [ ] `POST /api/v1/twgs/{twg_id}/subgroups/` creates a subgroup
- [ ] Frontend builds: `cd frontend && npm run build`
- [ ] Subgroups tab appears in TWG workspace
- [ ] Can create a subgroup from the UI
- [ ] Can add a TWG member to a subgroup
- [ ] Adding a non-TWG-member returns an error toast
- [ ] Removing a TWG member also removes them from subgroups
