"""
Organization Invitation API Routes

Provides endpoints for inviting external organizations to join TWGs.
Permissions: ADMIN, SECRETARIAT_LEAD have full access.
TWG_FACILITATOR can only invite to their assigned TWGs.
"""

from datetime import datetime, timedelta
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_
from sqlalchemy.orm import selectinload
import uuid
import math

from app.core.database import get_db
from app.models.models import (
    User, UserRole, TWG, OrganizationInvitation, OrganizationInvitationStatus
)
from app.api.deps import get_current_active_user, has_twg_access
from app.schemas.organization_invitation import (
    OrganizationInvitationCreate,
    OrganizationInvitationUpdate,
    OrganizationInvitationResponse,
    OrganizationInvitationListResponse,
    ResendInvitationResponse,
    InvitationRespondRequest,
    InvitationRespondResponse
)
from app.core.config import settings

router = APIRouter(prefix="/organization-invitations", tags=["Organization Invitations"])


def can_send_invitation(user: User, twg_id: uuid.UUID) -> bool:
    """Check if user can send invitation for a specific TWG."""
    if user.role in [UserRole.ADMIN, UserRole.SECRETARIAT_LEAD]:
        return True
    if user.role == UserRole.TWG_FACILITATOR:
        return has_twg_access(user, twg_id)
    return False


def can_access_invitation(user: User, invitation: OrganizationInvitation) -> bool:
    """Check if user can access a specific invitation."""
    if user.role in [UserRole.ADMIN, UserRole.SECRETARIAT_LEAD]:
        return True
    if user.role == UserRole.TWG_FACILITATOR:
        return has_twg_access(user, invitation.twg_id)
    return False


@router.post("/", response_model=OrganizationInvitationResponse, status_code=status.HTTP_201_CREATED)
async def create_invitation(
    invitation_data: OrganizationInvitationCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Create a new organization invitation.

    ADMIN/SECRETARIAT_LEAD: Can invite to any TWG.
    TWG_FACILITATOR: Can only invite to their assigned TWGs.
    """
    # Permission check
    if not can_send_invitation(current_user, invitation_data.twg_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to send invitations for this TWG"
        )

    # Verify TWG exists
    twg_result = await db.execute(select(TWG).where(TWG.id == invitation_data.twg_id))
    twg = twg_result.scalar_one_or_none()
    if not twg:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="TWG not found"
        )

    # Check for existing pending invitation to same email for same TWG
    existing_result = await db.execute(
        select(OrganizationInvitation).where(
            and_(
                OrganizationInvitation.contact_email == invitation_data.contact_email,
                OrganizationInvitation.twg_id == invitation_data.twg_id,
                OrganizationInvitation.status == OrganizationInvitationStatus.PENDING
            )
        )
    )
    existing = existing_result.scalar_one_or_none()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A pending invitation already exists for this organization/email to this TWG"
        )

    # Create invitation with 30-day expiry
    invitation = OrganizationInvitation(
        organization_name=invitation_data.organization_name,
        contact_email=invitation_data.contact_email,
        twg_id=invitation_data.twg_id,
        custom_message=invitation_data.custom_message,
        status=OrganizationInvitationStatus.PENDING,
        expires_at=datetime.utcnow() + timedelta(days=30),
        created_by_id=current_user.id
    )

    db.add(invitation)
    await db.commit()
    await db.refresh(invitation)

    # Send email if requested
    if invitation_data.send_email:
        try:
            from app.services.email_service import email_service
            await email_service.send_organization_invitation(
                to_email=invitation.contact_email,
                organization_name=invitation.organization_name,
                twg_name=twg.name,
                inviter_name=current_user.full_name,
                custom_message=invitation.custom_message,
                invitation_id=str(invitation.id),
                expires_at=invitation.expires_at
            )
            invitation.sent_at = datetime.utcnow()
            await db.commit()
        except Exception as e:
            print(f"Failed to send organization invitation email: {e}")
            # Don't fail the request if email fails

    # Build response with nested data
    return OrganizationInvitationResponse(
        id=invitation.id,
        organization_name=invitation.organization_name,
        contact_email=invitation.contact_email,
        twg_id=invitation.twg_id,
        twg_name=twg.name,
        custom_message=invitation.custom_message,
        status=invitation.status,
        expires_at=invitation.expires_at,
        sent_at=invitation.sent_at,
        responded_at=invitation.responded_at,
        created_by_id=invitation.created_by_id,
        created_by_name=current_user.full_name,
        resend_count=invitation.resend_count,
        last_resend_at=invitation.last_resend_at,
        created_at=invitation.created_at
    )


@router.get("/", response_model=OrganizationInvitationListResponse)
async def list_invitations(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status_filter: Optional[OrganizationInvitationStatus] = Query(None, alias="status"),
    twg_id: Optional[uuid.UUID] = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    List organization invitations with optional filters.

    ADMIN/SECRETARIAT_LEAD: Can see all invitations.
    TWG_FACILITATOR: Can only see invitations for their TWGs.
    """
    # Build base query
    query = (
        select(OrganizationInvitation)
        .options(
            selectinload(OrganizationInvitation.twg),
            selectinload(OrganizationInvitation.created_by)
        )
    )

    # Apply TWG filter based on user role
    if current_user.role == UserRole.TWG_FACILITATOR:
        user_twg_ids = [twg.id for twg in current_user.twgs]
        query = query.where(OrganizationInvitation.twg_id.in_(user_twg_ids))

    # Apply filters
    if status_filter:
        query = query.where(OrganizationInvitation.status == status_filter)
    if twg_id:
        # Check permission for specific TWG
        if current_user.role == UserRole.TWG_FACILITATOR:
            if twg_id not in [twg.id for twg in current_user.twgs]:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Access denied to this TWG's invitations"
                )
        query = query.where(OrganizationInvitation.twg_id == twg_id)

    # Count total
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar()

    # Apply pagination
    offset = (page - 1) * page_size
    query = query.order_by(OrganizationInvitation.created_at.desc()).offset(offset).limit(page_size)

    result = await db.execute(query)
    invitations = result.scalars().all()

    # Build response items
    items = [
        OrganizationInvitationResponse(
            id=inv.id,
            organization_name=inv.organization_name,
            contact_email=inv.contact_email,
            twg_id=inv.twg_id,
            twg_name=inv.twg.name if inv.twg else None,
            custom_message=inv.custom_message,
            status=inv.status,
            expires_at=inv.expires_at,
            sent_at=inv.sent_at,
            responded_at=inv.responded_at,
            created_by_id=inv.created_by_id,
            created_by_name=inv.created_by.full_name if inv.created_by else None,
            resend_count=inv.resend_count,
            last_resend_at=inv.last_resend_at,
            created_at=inv.created_at
        )
        for inv in invitations
    ]

    return OrganizationInvitationListResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        pages=math.ceil(total / page_size) if total > 0 else 0
    )


@router.get("/{invitation_id}", response_model=OrganizationInvitationResponse)
async def get_invitation(
    invitation_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get a single organization invitation by ID."""
    query = (
        select(OrganizationInvitation)
        .where(OrganizationInvitation.id == invitation_id)
        .options(
            selectinload(OrganizationInvitation.twg),
            selectinload(OrganizationInvitation.created_by)
        )
    )
    result = await db.execute(query)
    invitation = result.scalar_one_or_none()

    if not invitation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Invitation not found"
        )

    # Permission check
    if not can_access_invitation(current_user, invitation):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied to this invitation"
        )

    return OrganizationInvitationResponse(
        id=invitation.id,
        organization_name=invitation.organization_name,
        contact_email=invitation.contact_email,
        twg_id=invitation.twg_id,
        twg_name=invitation.twg.name if invitation.twg else None,
        custom_message=invitation.custom_message,
        status=invitation.status,
        expires_at=invitation.expires_at,
        sent_at=invitation.sent_at,
        responded_at=invitation.responded_at,
        created_by_id=invitation.created_by_id,
        created_by_name=invitation.created_by.full_name if invitation.created_by else None,
        resend_count=invitation.resend_count,
        last_resend_at=invitation.last_resend_at,
        created_at=invitation.created_at
    )


@router.patch("/{invitation_id}", response_model=OrganizationInvitationResponse)
async def update_invitation(
    invitation_id: uuid.UUID,
    update_data: OrganizationInvitationUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Update a pending organization invitation.

    Only pending invitations can be updated.
    """
    query = (
        select(OrganizationInvitation)
        .where(OrganizationInvitation.id == invitation_id)
        .options(
            selectinload(OrganizationInvitation.twg),
            selectinload(OrganizationInvitation.created_by)
        )
    )
    result = await db.execute(query)
    invitation = result.scalar_one_or_none()

    if not invitation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Invitation not found"
        )

    # Permission check
    if not can_access_invitation(current_user, invitation):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied to this invitation"
        )

    # Only pending invitations can be updated
    if invitation.status != OrganizationInvitationStatus.PENDING:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only pending invitations can be updated"
        )

    # Apply updates
    update_dict = update_data.model_dump(exclude_unset=True)

    # If TWG is being changed, verify permissions for new TWG
    if "twg_id" in update_dict and update_dict["twg_id"] != invitation.twg_id:
        if not can_send_invitation(current_user, update_dict["twg_id"]):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You don't have permission to move invitations to this TWG"
            )
        # Verify new TWG exists
        twg_result = await db.execute(select(TWG).where(TWG.id == update_dict["twg_id"]))
        if not twg_result.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="TWG not found"
            )

    for field, value in update_dict.items():
        setattr(invitation, field, value)

    await db.commit()
    await db.refresh(invitation, attribute_names=["twg", "created_by"])

    return OrganizationInvitationResponse(
        id=invitation.id,
        organization_name=invitation.organization_name,
        contact_email=invitation.contact_email,
        twg_id=invitation.twg_id,
        twg_name=invitation.twg.name if invitation.twg else None,
        custom_message=invitation.custom_message,
        status=invitation.status,
        expires_at=invitation.expires_at,
        sent_at=invitation.sent_at,
        responded_at=invitation.responded_at,
        created_by_id=invitation.created_by_id,
        created_by_name=invitation.created_by.full_name if invitation.created_by else None,
        resend_count=invitation.resend_count,
        last_resend_at=invitation.last_resend_at,
        created_at=invitation.created_at
    )


@router.delete("/{invitation_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_invitation(
    invitation_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Delete an organization invitation."""
    query = select(OrganizationInvitation).where(OrganizationInvitation.id == invitation_id)
    result = await db.execute(query)
    invitation = result.scalar_one_or_none()

    if not invitation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Invitation not found"
        )

    # Permission check
    if not can_access_invitation(current_user, invitation):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied to this invitation"
        )

    await db.delete(invitation)
    await db.commit()

    return None


@router.post("/{invitation_id}/resend", response_model=ResendInvitationResponse)
async def resend_invitation(
    invitation_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Resend an organization invitation email.

    Resets expiry to 30 days from now. Only pending invitations can be resent.
    """
    query = (
        select(OrganizationInvitation)
        .where(OrganizationInvitation.id == invitation_id)
        .options(selectinload(OrganizationInvitation.twg))
    )
    result = await db.execute(query)
    invitation = result.scalar_one_or_none()

    if not invitation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Invitation not found"
        )

    # Permission check
    if not can_access_invitation(current_user, invitation):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied to this invitation"
        )

    # Only pending invitations can be resent
    if invitation.status != OrganizationInvitationStatus.PENDING:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only pending invitations can be resent"
        )

    # Reset expiry and send email
    invitation.expires_at = datetime.utcnow() + timedelta(days=30)

    try:
        from app.services.email_service import email_service
        await email_service.send_organization_invitation(
            to_email=invitation.contact_email,
            organization_name=invitation.organization_name,
            twg_name=invitation.twg.name,
            inviter_name=current_user.full_name,
            custom_message=invitation.custom_message,
            invitation_id=str(invitation.id),
            expires_at=invitation.expires_at
        )
        invitation.sent_at = datetime.utcnow()
        invitation.resend_count += 1
        invitation.last_resend_at = datetime.utcnow()
        await db.commit()

        return ResendInvitationResponse(
            id=invitation.id,
            organization_name=invitation.organization_name,
            contact_email=invitation.contact_email,
            invite_sent=True,
            message="Invitation resent successfully"
        )
    except Exception as e:
        print(f"Failed to resend organization invitation email: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to send invitation email"
        )


@router.post("/{invitation_id}/respond", response_model=InvitationRespondResponse)
async def respond_to_invitation(
    invitation_id: uuid.UUID,
    respond_data: InvitationRespondRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Public endpoint for organizations to accept or decline invitations.

    No authentication required - invitation ID serves as the access token.
    """
    query = (
        select(OrganizationInvitation)
        .where(OrganizationInvitation.id == invitation_id)
        .options(selectinload(OrganizationInvitation.twg))
    )
    result = await db.execute(query)
    invitation = result.scalar_one_or_none()

    if not invitation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Invitation not found"
        )

    # Check if invitation is still pending
    if invitation.status != OrganizationInvitationStatus.PENDING:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"This invitation has already been {invitation.status.value}"
        )

    # Check if expired
    if invitation.expires_at < datetime.utcnow():
        invitation.status = OrganizationInvitationStatus.EXPIRED
        await db.commit()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This invitation has expired"
        )

    # Process response
    response = respond_data.response.lower()
    if response not in ["accept", "decline"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Response must be 'accept' or 'decline'"
        )

    invitation.status = (
        OrganizationInvitationStatus.ACCEPTED
        if response == "accept"
        else OrganizationInvitationStatus.DECLINED
    )
    invitation.responded_at = datetime.utcnow()
    await db.commit()

    twg_name = invitation.twg.name if invitation.twg else "Unknown TWG"

    return InvitationRespondResponse(
        id=invitation.id,
        organization_name=invitation.organization_name,
        twg_name=twg_name,
        status=invitation.status,
        message=f"Invitation {response}ed successfully. "
                f"You will be contacted by the {twg_name} team shortly."
                if response == "accept"
                else f"Invitation to join {twg_name} has been declined."
    )
