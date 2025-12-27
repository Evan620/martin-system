from sqlalchemy.ext.asyncio import AsyncSession
import uuid
from datetime import datetime
from typing import Optional

from backend.app.models.models import Notification, NotificationType
from backend.app.core.ws_manager import ws_manager

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
