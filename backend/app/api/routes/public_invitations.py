"""
Public Invitation API Routes

Public endpoints for invitees to view and respond to invitations.
No authentication required - invitation UUID serves as access token.
"""

from datetime import datetime
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from sqlalchemy.orm import selectinload
import uuid

from app.core.database import get_db
from app.models.models import (
    OrganizationInvitation, OrganizationInvitationStatus,
    InvitationMessage, InvitationMessageSender
)
from app.schemas.organization_invitation import (
    InvitationRespondRequest,
    InvitationRespondResponse,
    InvitationMessageCreate,
    InvitationMessageResponse,
    InvitationMessageListResponse,
    PublicInvitationResponse
)

router = APIRouter(prefix="/public/invitations", tags=["Public Invitations"])


@router.get("/{invitation_id}", response_model=PublicInvitationResponse)
async def get_public_invitation(
    invitation_id: uuid.UUID,
    db: AsyncSession = Depends(get_db)
):
    """
    Get invitation details (public, no auth required).

    Returns basic invitation info for the public respond page.
    """
    query = (
        select(OrganizationInvitation)
        .where(OrganizationInvitation.id == invitation_id)
        .options(
            selectinload(OrganizationInvitation.twg),
            selectinload(OrganizationInvitation.messages)
        )
    )
    result = await db.execute(query)
    invitation = result.scalar_one_or_none()

    if not invitation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Invitation not found"
        )

    return PublicInvitationResponse(
        id=invitation.id,
        organization_name=invitation.organization_name,
        twg_name=invitation.twg.name if invitation.twg else "Unknown TWG",
        status=invitation.status,
        expires_at=invitation.expires_at,
        custom_message=invitation.custom_message,
        has_messages=len(invitation.messages) > 0
    )


@router.get("/{invitation_id}/messages", response_model=InvitationMessageListResponse)
async def get_public_invitation_messages(
    invitation_id: uuid.UUID,
    db: AsyncSession = Depends(get_db)
):
    """
    Get all messages for an invitation (public invitee view).

    Marks admin messages as read by invitee when fetched.
    """
    query = (
        select(OrganizationInvitation)
        .where(OrganizationInvitation.id == invitation_id)
        .options(selectinload(OrganizationInvitation.messages))
    )
    result = await db.execute(query)
    invitation = result.scalar_one_or_none()

    if not invitation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Invitation not found"
        )

    # Mark all admin messages as read by invitee
    if invitation.unread_by_invitee_count > 0:
        await db.execute(
            update(InvitationMessage)
            .where(
                InvitationMessage.invitation_id == invitation_id,
                InvitationMessage.sender_type == InvitationMessageSender.ADMIN,
                InvitationMessage.is_read_by_invitee == False
            )
            .values(is_read_by_invitee=True)
        )
        invitation.unread_by_invitee_count = 0
        await db.commit()

    # Build response
    messages = [
        InvitationMessageResponse(
            id=msg.id,
            invitation_id=msg.invitation_id,
            sender_type=msg.sender_type,
            sender_user_id=msg.sender_user_id,
            sender_name=msg.sender_name,
            content=msg.content,
            is_read_by_admin=msg.is_read_by_admin,
            is_read_by_invitee=msg.is_read_by_invitee,
            created_at=msg.created_at,
            is_read=True  # Invitee viewing fetched messages
        )
        for msg in invitation.messages
    ]

    return InvitationMessageListResponse(
        items=messages,
        total=len(messages),
        unread_count=0  # Just marked as read
    )


@router.post("/{invitation_id}/messages", response_model=InvitationMessageResponse, status_code=status.HTTP_201_CREATED)
async def send_public_invitation_message(
    invitation_id: uuid.UUID,
    message_data: InvitationMessageCreate,
    db: AsyncSession = Depends(get_db)
):
    """
    Send a message from invitee to admin (public, no auth required).

    Creates notification for admins.
    """
    query = (
        select(OrganizationInvitation)
        .where(OrganizationInvitation.id == invitation_id)
        .options(selectinload(OrganizationInvitation.messages))
    )
    result = await db.execute(query)
    invitation = result.scalar_one_or_none()

    if not invitation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Invitation not found"
        )

    # Create message
    message = InvitationMessage(
        invitation_id=invitation_id,
        sender_type=InvitationMessageSender.INVITEE,
        sender_user_id=None,
        sender_name=invitation.organization_name,
        content=message_data.content,
        is_read_by_admin=False,
        is_read_by_invitee=True
    )

    db.add(message)
    invitation.unread_by_admin_count += 1
    await db.commit()
    await db.refresh(message)

    # TODO: Could send notification to admin via WebSocket or in-app notification

    return InvitationMessageResponse(
        id=message.id,
        invitation_id=message.invitation_id,
        sender_type=message.sender_type,
        sender_user_id=message.sender_user_id,
        sender_name=message.sender_name,
        content=message.content,
        is_read_by_admin=message.is_read_by_admin,
        is_read_by_invitee=message.is_read_by_invitee,
        created_at=message.created_at,
        is_read=True
    )


@router.post("/{invitation_id}/respond", response_model=InvitationRespondResponse)
async def public_respond_to_invitation(
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
