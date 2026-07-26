from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
import uuid
from datetime import datetime
from typing import Any, Optional

from app.models.models import Notification, NotificationType, User
from app.core.ws_manager import ws_manager


async def list_notifications(
    db: AsyncSession,
    current_user: User,
    *,
    skip: int = 0,
    limit: int = 50,
) -> list[Notification]:
    """List the current user's notifications using the route's pagination."""

    query = (
        select(Notification)
        .where(Notification.user_id == current_user.id)
        .order_by(Notification.created_at.desc())
        .offset(skip)
        .limit(limit)
    )
    result = await db.execute(query)
    return list(result.scalars().all())


async def mark_all_notifications_read(
    db: AsyncSession,
    current_user: User,
) -> dict[str, Any]:
    """Mark every notification owned by the current user as read."""

    query = (
        update(Notification)
        .where(
            Notification.user_id == current_user.id,
            Notification.is_read == False,  # noqa: E712
        )
        .values(is_read=True)
    )
    await db.execute(query)
    await db.commit()
    return {"status": "success", "message": "All notifications marked as read"}

async def create_notification(
    db: AsyncSession,
    user_id: uuid.UUID,
    type: NotificationType,
    title: str,
    content: str,
    link: Optional[str] = None
) -> Notification:
    """
    Create a notification in the database and broadcast it via WebSocket.
    """
    notification = Notification(
        user_id=user_id,
        type=type,
        title=title,
        content=content,
        link=link,
        is_read=False,
        created_at=datetime.utcnow()
    )
    
    db.add(notification)
    await db.commit()
    await db.refresh(notification)
    
    # Broadcast via WebSocket
    await ws_manager.send_personal_message(
        {
            "type": "NEW_NOTIFICATION",
            "data": {
                "id": str(notification.id),
                "type": notification.type.value,
                "title": notification.title,
                "content": notification.content,
                "link": notification.link,
                "created_at": notification.created_at.isoformat()
            }
        },
        str(user_id)
    )
    
    return notification
