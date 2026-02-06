"""
Broadcast Service

Manages the distribution of knowledge across the multi-agent system.
Implements the "Knowledge Broadcasting" phase of the Supervisor architecture.
"""

from typing import List, Dict, Optional, Any, Union
from datetime import datetime
import json
import logging
import redis
from pydantic import BaseModel

# Use loguru for consistency if available, else standard logging
try:
    from loguru import logger
except ImportError:
    logger = logging.getLogger(__name__)

from app.models.models import Document
from app.core.config import settings
from app.core.knowledge_base import get_knowledge_base

class BroadcastService:
    """
    Supervisor's knowledge distribution mechanism.
    
    Handles:
    1. Updating global knowledge base with broadcast scope
    2. Notifying relevant agents via Redis pub/sub or lists
    3. Logging broadcast events
    """
    
    def __init__(self):
        self.redis_client = None
        # Try connecting to Redis
        try:
            if settings.REDIS_URL:
                self.redis_client = redis.Redis.from_url(settings.REDIS_URL)
                logger.debug(f"BroadcastService connected to Redis at {settings.REDIS_URL}")
            elif settings.REDIS_HOST:
                self.redis_client = redis.Redis(
                    host=settings.REDIS_HOST,
                    port=settings.REDIS_PORT,
                    db=settings.REDIS_DB,
                    password=settings.REDIS_PASSWORD
                )
                logger.debug(f"BroadcastService connected to Redis at {settings.REDIS_HOST}:{settings.REDIS_PORT}")
            else:
                logger.warning("No Redis configuration found. Broadcasts will not be sent to agents.")
        except Exception as e:
            logger.error(f"BroadcastService failed to connect to Redis: {e}")

        self.knowledge_base = get_knowledge_base()

    async def broadcast_document(
        self,
        doc: Document,
        target_agents: Union[List[str], str] = "ALL",
        notification_type: str = "new_document"
    ):
        """
        Supervisor distributes knowledge to agent swarm.
        
        Args:
            doc: The Document model instance to broadcast
            target_agents: List of agent IDs (e.g. "energy", "agriculture") or "ALL"
            notification_type: Type of notification (new_document, critical_update, etc.)
        """
        try:
            # 1. Add to global knowledge base with updated scope
            # Ensure "global" is in the scope if likely to be broadcasted widely
            # Metadata for vector DB
            metadata = {
                "title": doc.file_name, 
                "source": "supervisor_broadcast",
                "category": getattr(doc, "category", "general"),
                "version": getattr(doc, "version", 1),
                "scope": doc.scope, 
                "broadcast_at": datetime.utcnow().isoformat()
            }
            if doc.metadata_json:
                metadata.update(doc.metadata_json)

            # Upsert to Vector DB (Pinecone)
            # We use "global" namespace for broadcasted items to keep them distinct? 
            # Or reliance on metadata filtering.
            # Using specific namespace 'global' ensures we can easily retrieve *just* broadcasted items if needed,
            # but usually RAG queries specific TWG namespaces. Use 'global' to separate.
            
            # Note: doc.file_path is used as content placeholder if content text isn't available
            content_to_embed = doc.file_name  # Ideally real content
            
            self.knowledge_base.add_document(
                content=content_to_embed,
                doc_id=str(doc.id),
                metadata=metadata,
                namespace="global" 
            )
            
            # 2. Determine recipients
            all_agents = [
                "energy", "agriculture", "minerals",
                "digital", "protocol", "resource_mobilization"
            ]
            
            if target_agents == "ALL":
                recipients = all_agents
            else:
                if isinstance(target_agents, str):
                    recipients = [target_agents]
                else:
                    recipients = [a for a in target_agents if a in all_agents]
            
            # 3. Create notification for each agent
            for agent_id in recipients:
                self._notify_agent(agent_id, doc, notification_type)
            
            # 4. Log broadcast
            self._log_broadcast(str(doc.id), recipients)
            
            logger.info(f"Broadcast complete: Document {doc.id} sent to {len(recipients)} agents")
            
        except Exception as e:
            logger.error(f"Broadcast failed: {e}")
            # Don't crash the caller, just log
            # raise e 

    def _notify_agent(self, agent_id: str, doc: Document, notif_type: str):
        """
        Alert agent about new broadcast content via Redis.
        """
        if not self.redis_client:
            logger.warning("Redis client not initialized, skipping notification")
            return

        notification = {
            "type": notif_type,
            "document_id": str(doc.id),
            "title": doc.file_name,
            "category": getattr(doc, "category", "general"),
            "version": getattr(doc, "version", 1),
            "action": "reload_context" if getattr(doc, "category", "") == "evolving" else "context_available",
            "timestamp": datetime.utcnow().isoformat()
        }
        
        # Store in agent's notification queue
        queue_key = f"notifications:{agent_id}"
        try:
            self.redis_client.lpush(queue_key, json.dumps(notification))
            # Keep queue size manageable (last 100 notifications)
            self.redis_client.ltrim(queue_key, 0, 99) 
            logger.debug(f"Notification sent to {agent_id}: {notif_type}")
        except Exception as e:
            logger.error(f"Failed to push notification to Redis for {agent_id}: {e}")

    async def notify_live_meeting(
        self,
        meeting_id: str,
        content: str,
        source: str = "live_insight",
        original_question: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """
        Notify the live meeting dashboard of a new insight or response.
        """
        if not self.redis_client:
            logger.warning("Redis client not initialized, skipping live notification")
            return

        payload = {
            "type": "live_meeting_update",
            "meeting_id": str(meeting_id),
            "source": source,
            "content": content,
            "original_question": original_question,
            "metadata": metadata,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        try:
            # 1. Push to a list for persistence/polling
            queue_key = f"live_updates:{meeting_id}"
            self.redis_client.lpush(queue_key, json.dumps(payload))
            self.redis_client.ltrim(queue_key, 0, 49) # Keep last 50 updates
            
            # 2. Publish for real-time WebSocket clients
            self.redis_client.publish("live_meeting_stream", json.dumps(payload))
            
            logger.info(f"✓ Post LIVE UPDATE for meeting {meeting_id} from {source}")
        except Exception as e:
            logger.error(f"Failed to push live update to Redis: {e}")

    async def notify_meeting_update(
        self,
        meeting_id,
        update_data: Optional[Dict[str, Any]] = None
    ):
        """
        Push a real-time meeting update to all connected WebSocket clients.
        Used after transcript processing completes so the frontend auto-refreshes.
        """
        from app.core.ws_manager import ws_manager

        update_data = update_data or {}
        message = {
            "type": "transcript_processed",
            "meeting_id": str(meeting_id),
            "data": {
                "meeting_id": str(meeting_id),
                "message": update_data.get("message", "Transcript and minutes are now available."),
                **update_data
            }
        }

        # 1. Push to all dashboard WebSocket clients
        try:
            await ws_manager.broadcast(message)
            logger.info(f"WebSocket broadcast sent for meeting {meeting_id}")
        except Exception as e:
            logger.error(f"WebSocket broadcast failed: {e}")

        # 2. Also publish to Redis for live meeting WebSocket subscribers
        if self.redis_client:
            try:
                payload = {
                    "type": "live_meeting_update",
                    "meeting_id": str(meeting_id),
                    "source": "transcript_processed",
                    "content": "Transcript and minutes are now available.",
                    "metadata": update_data,
                    "timestamp": datetime.utcnow().isoformat()
                }
                self.redis_client.publish("live_meeting_stream", json.dumps(payload))
            except Exception as e:
                logger.error(f"Redis publish failed for meeting update: {e}")

    def _log_broadcast(self, doc_id: str, recipients: List[str]):
        """Log the broadcast event."""
        logger.info(f"[BROADCAST_LOG] Doc: {doc_id} -> Agents: {recipients}")

# Singleton
_broadcast_service = None

def get_broadcast_service() -> BroadcastService:
    global _broadcast_service
    if not _broadcast_service:
        _broadcast_service = BroadcastService()
    return _broadcast_service
