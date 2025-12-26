"""
Redis Message Bus Service

Provides a Redis-backed message bus for agent-to-agent communication with:
- Message queuing (point-to-point)
- Pub/sub (broadcast events)
- Message tracking and acknowledgment
- Delivery guarantees

Redis Key Structure:
- Queues: ecowas:agent:{agent_id}:queue (LIST)
- Channels: ecowas:agent:{agent_id}:channel (PUB/SUB)
- Message status: ecowas:message:{message_id}:status (HASH)
- Event streams: ecowas:events:{event_type} (STREAM)
"""

import json
import time
from typing import Optional, List, Dict, Any, Callable
from uuid import UUID
from datetime import datetime, timedelta
from loguru import logger

import redis
from redis.exceptions import RedisError, ConnectionError

from backend.app.schemas.agent_messages import (
    AgentMessage,
    AgentEvent,
    MessageStatus,
    MessageType
)


class RedisMessageBus:
    """
    Redis-backed message bus for agent communication.

    Provides:
    - Reliable message queuing between agents
    - Pub/sub event broadcasting
    - Message status tracking
    - Delivery acknowledgment
    """

    def __init__(
        self,
        redis_client: redis.Redis,
        namespace: str = "ecowas",
        default_timeout: int = 30,
        max_queue_size: int = 1000,
        message_ttl: int = 3600
    ):
        """
        Initialize the message bus.

        Args:
            redis_client: Redis client instance
            namespace: Namespace prefix for all Redis keys
            default_timeout: Default timeout for blocking operations (seconds)
            max_queue_size: Maximum messages per agent queue
            message_ttl: Message TTL in seconds (default 1 hour)
        """
        self.client = redis_client
        self.namespace = namespace
        self.default_timeout = default_timeout
        self.max_queue_size = max_queue_size
        self.message_ttl = message_ttl

        logger.info(
            f"RedisMessageBus initialized with namespace '{namespace}', "
            f"timeout={default_timeout}s, ttl={message_ttl}s"
        )

    # =========================================================================
    # Key Generation
    # =========================================================================

    def _make_queue_key(self, agent_id: str) -> str:
        """Generate Redis key for agent's message queue"""
        return f"{self.namespace}:agent:{agent_id}:queue"

    def _make_channel_key(self, agent_id: str) -> str:
        """Generate Redis key for agent's pub/sub channel"""
        return f"{self.namespace}:agent:{agent_id}:channel"

    def _make_message_status_key(self, message_id: UUID) -> str:
        """Generate Redis key for message status tracking"""
        return f"{self.namespace}:message:{message_id}:status"

    def _make_event_stream_key(self, event_type: str) -> str:
        """Generate Redis key for event stream"""
        return f"{self.namespace}:events:{event_type}"

    # =========================================================================
    # Message Queuing (Point-to-Point)
    # =========================================================================

    def send_message(self, message: AgentMessage) -> UUID:
        """
        Send a message to an agent's queue.

        Uses Redis LIST with LPUSH for FIFO queue semantics.
        Tracks message status and enforces queue size limits.

        Args:
            message: AgentMessage to send

        Returns:
            UUID: Message ID

        Raises:
            RedisError: If send fails
            ValueError: If queue is full
        """
        try:
            recipient_id = message.metadata.recipient_id
            queue_key = self._make_queue_key(recipient_id)
            message_id = message.metadata.message_id

            # Check queue size
            current_size = self.client.llen(queue_key)
            if current_size >= self.max_queue_size:
                raise ValueError(
                    f"Queue full for agent '{recipient_id}' "
                    f"({current_size}/{self.max_queue_size})"
                )

            # Serialize message
            message_json = json.dumps(message.to_dict())

            # Push to queue (LPUSH for FIFO with BRPOP)
            self.client.lpush(queue_key, message_json)

            # Track message status
            self._update_message_status(
                message_id=message_id,
                status=MessageStatus.DELIVERED,
                agent_id=recipient_id
            )

            logger.debug(
                f"Sent message {message_id} to agent '{recipient_id}' "
                f"(type={message.type}, priority={message.priority})"
            )

            return message_id

        except RedisError as e:
            logger.error(f"Failed to send message {message.metadata.message_id}: {e}")
            raise

    def receive_message(
        self,
        agent_id: str,
        timeout: Optional[int] = None
    ) -> Optional[AgentMessage]:
        """
        Receive a message from an agent's queue (blocking).

        Uses Redis BRPOP for blocking pop with timeout.

        Args:
            agent_id: Agent ID to receive messages for
            timeout: Timeout in seconds (None = use default)

        Returns:
            AgentMessage if available, None if timeout

        Raises:
            RedisError: If receive fails
        """
        try:
            queue_key = self._make_queue_key(agent_id)
            timeout = timeout if timeout is not None else self.default_timeout

            # Blocking pop from queue
            result = self.client.brpop(queue_key, timeout=timeout)

            if result is None:
                return None

            # Parse message
            _, message_json = result
            message_dict = json.loads(message_json)

            # Reconstruct message (determine type from dict)
            message = self._deserialize_message(message_dict)

            # Update status to processing
            self._update_message_status(
                message_id=message.metadata.message_id,
                status=MessageStatus.PROCESSING,
                agent_id=agent_id
            )

            logger.debug(
                f"Agent '{agent_id}' received message {message.metadata.message_id} "
                f"(type={message.type})"
            )

            return message

        except RedisError as e:
            logger.error(f"Failed to receive message for agent '{agent_id}': {e}")
            raise

    def get_pending_messages(self, agent_id: str) -> List[AgentMessage]:
        """
        Get all pending messages for an agent (non-blocking).

        Args:
            agent_id: Agent ID

        Returns:
            List of pending messages
        """
        try:
            queue_key = self._make_queue_key(agent_id)

            # Get all messages without removing them
            messages_json = self.client.lrange(queue_key, 0, -1)

            messages = []
            for msg_json in messages_json:
                message_dict = json.loads(msg_json)
                message = self._deserialize_message(message_dict)
                messages.append(message)

            logger.debug(f"Agent '{agent_id}' has {len(messages)} pending messages")

            return messages

        except RedisError as e:
            logger.error(f"Failed to get pending messages for '{agent_id}': {e}")
            return []

    # =========================================================================
    # Pub/Sub (Broadcast Events)
    # =========================================================================

    def publish_event(self, event: AgentEvent) -> int:
        """
        Publish an event to a channel (fire-and-forget).

        Uses Redis PUBLISH for pub/sub messaging.

        Args:
            event: AgentEvent to publish

        Returns:
            int: Number of subscribers that received the event

        Raises:
            RedisError: If publish fails
        """
        try:
            event_type = event.event_type
            channel_key = self._make_event_stream_key(event_type)

            # Serialize event
            event_json = json.dumps(event.to_dict())

            # Publish to channel
            subscriber_count = self.client.publish(channel_key, event_json)

            # Also add to stream for history
            stream_key = self._make_event_stream_key(event_type)
            self.client.xadd(
                stream_key,
                {"data": event_json},
                maxlen=1000  # Keep last 1000 events
            )

            logger.debug(
                f"Published event '{event_type}' to {subscriber_count} subscribers "
                f"(sender={event.metadata.sender_id})"
            )

            return subscriber_count

        except RedisError as e:
            logger.error(f"Failed to publish event: {e}")
            raise

    def subscribe_to_channel(
        self,
        agent_id: str,
        callback: Callable[[AgentEvent], None]
    ) -> None:
        """
        Subscribe to an agent's channel for events.

        This is a BLOCKING operation - runs in a loop until interrupted.
        Consider running in a background thread.

        Args:
            agent_id: Agent ID to subscribe for
            callback: Function to call with each event

        Raises:
            RedisError: If subscription fails
        """
        try:
            channel_key = self._make_channel_key(agent_id)
            pubsub = self.client.pubsub()
            pubsub.subscribe(channel_key)

            logger.info(f"Agent '{agent_id}' subscribed to channel '{channel_key}'")

            for message in pubsub.listen():
                if message['type'] == 'message':
                    event_dict = json.loads(message['data'])
                    event = self._deserialize_message(event_dict)

                    if isinstance(event, AgentEvent):
                        callback(event)

        except RedisError as e:
            logger.error(f"Subscription failed for agent '{agent_id}': {e}")
            raise

    def subscribe_to_event_type(
        self,
        event_type: str,
        callback: Callable[[AgentEvent], None]
    ) -> None:
        """
        Subscribe to a specific event type.

        Args:
            event_type: Type of event to subscribe to
            callback: Function to call with each event

        Raises:
            RedisError: If subscription fails
        """
        try:
            channel_key = self._make_event_stream_key(event_type)
            pubsub = self.client.pubsub()
            pubsub.subscribe(channel_key)

            logger.info(f"Subscribed to event type '{event_type}'")

            for message in pubsub.listen():
                if message['type'] == 'message':
                    event_dict = json.loads(message['data'])
                    event = self._deserialize_message(event_dict)

                    if isinstance(event, AgentEvent):
                        callback(event)

        except RedisError as e:
            logger.error(f"Event subscription failed for '{event_type}': {e}")
            raise

    # =========================================================================
    # Message Status Tracking
    # =========================================================================

    def acknowledge_message(self, message_id: UUID, agent_id: str) -> bool:
        """
        Acknowledge that a message has been successfully processed.

        Args:
            message_id: Message ID to acknowledge
            agent_id: Agent that processed the message

        Returns:
            bool: True if acknowledged

        Raises:
            RedisError: If acknowledgment fails
        """
        try:
            self._update_message_status(
                message_id=message_id,
                status=MessageStatus.COMPLETED,
                agent_id=agent_id
            )

            logger.debug(f"Message {message_id} acknowledged by '{agent_id}'")
            return True

        except RedisError as e:
            logger.error(f"Failed to acknowledge message {message_id}: {e}")
            raise

    def fail_message(
        self,
        message_id: UUID,
        agent_id: str,
        error: str
    ) -> bool:
        """
        Mark a message as failed.

        Args:
            message_id: Message ID
            agent_id: Agent that failed to process
            error: Error description

        Returns:
            bool: True if marked failed

        Raises:
            RedisError: If update fails
        """
        try:
            self._update_message_status(
                message_id=message_id,
                status=MessageStatus.FAILED,
                agent_id=agent_id,
                error=error
            )

            logger.warning(
                f"Message {message_id} marked failed by '{agent_id}': {error}"
            )
            return True

        except RedisError as e:
            logger.error(f"Failed to mark message {message_id} as failed: {e}")
            raise

    def get_message_status(self, message_id: UUID) -> Optional[Dict[str, Any]]:
        """
        Get the status of a message.

        Args:
            message_id: Message ID

        Returns:
            Dictionary with status info, or None if not found
        """
        try:
            status_key = self._make_message_status_key(message_id)
            status = self.client.hgetall(status_key)

            if not status:
                return None

            return {
                k.decode('utf-8'): v.decode('utf-8')
                for k, v in status.items()
            }

        except RedisError as e:
            logger.error(f"Failed to get message status for {message_id}: {e}")
            return None

    def _update_message_status(
        self,
        message_id: UUID,
        status: MessageStatus,
        agent_id: str,
        error: Optional[str] = None
    ) -> None:
        """Internal: Update message status in Redis"""
        status_key = self._make_message_status_key(message_id)

        status_data = {
            "message_id": str(message_id),
            "status": status.value,
            "agent_id": agent_id,
            "updated_at": datetime.utcnow().isoformat()
        }

        if error:
            status_data["error"] = error

        self.client.hset(status_key, mapping=status_data)
        self.client.expire(status_key, self.message_ttl)

    # =========================================================================
    # Utility Methods
    # =========================================================================

    def _deserialize_message(self, message_dict: Dict[str, Any]) -> AgentMessage:
        """
        Deserialize a message dict to the appropriate message type.

        Args:
            message_dict: Message dictionary

        Returns:
            Appropriate AgentMessage subclass
        """
        from backend.app.schemas.agent_messages import (
            DelegationRequest,
            AgentResponse,
            ErrorMessage
        )

        message_type = message_dict.get('type')

        if message_type == MessageType.DELEGATION.value:
            return DelegationRequest.from_dict(message_dict)
        elif message_type == MessageType.RESPONSE.value:
            return AgentResponse.from_dict(message_dict)
        elif message_type == MessageType.ERROR.value:
            return ErrorMessage.from_dict(message_dict)
        elif message_type == MessageType.EVENT.value:
            return AgentEvent.from_dict(message_dict)
        else:
            return AgentMessage.from_dict(message_dict)

    def clear_agent_queue(self, agent_id: str) -> int:
        """
        Clear all messages from an agent's queue.

        Args:
            agent_id: Agent ID

        Returns:
            Number of messages cleared
        """
        try:
            queue_key = self._make_queue_key(agent_id)
            count = self.client.llen(queue_key)
            self.client.delete(queue_key)

            logger.info(f"Cleared {count} messages from agent '{agent_id}' queue")
            return count

        except RedisError as e:
            logger.error(f"Failed to clear queue for '{agent_id}': {e}")
            return 0

    def get_queue_size(self, agent_id: str) -> int:
        """
        Get the current size of an agent's queue.

        Args:
            agent_id: Agent ID

        Returns:
            Number of messages in queue
        """
        try:
            queue_key = self._make_queue_key(agent_id)
            return self.client.llen(queue_key)

        except RedisError as e:
            logger.error(f"Failed to get queue size for '{agent_id}': {e}")
            return 0

    def health_check(self) -> bool:
        """
        Check if Redis connection is healthy.

        Returns:
            True if healthy, False otherwise
        """
        try:
            self.client.ping()
            return True
        except (RedisError, ConnectionError):
            return False

    def get_bus_stats(self) -> Dict[str, Any]:
        """
        Get message bus statistics.

        Returns:
            Dictionary with bus statistics
        """
        try:
            # Get all agent queues
            pattern = f"{self.namespace}:agent:*:queue"
            queue_keys = self.client.keys(pattern)

            queue_stats = {}
            total_messages = 0

            for key in queue_keys:
                agent_id = key.decode('utf-8').split(':')[2]
                size = self.client.llen(key)
                queue_stats[agent_id] = size
                total_messages += size

            return {
                "total_agents": len(queue_keys),
                "total_messages": total_messages,
                "queue_stats": queue_stats,
                "max_queue_size": self.max_queue_size,
                "healthy": self.health_check()
            }

        except RedisError as e:
            logger.error(f"Failed to get bus stats: {e}")
            return {
                "error": str(e),
                "healthy": False
            }

    def __repr__(self) -> str:
        return (
            f"<RedisMessageBus namespace='{self.namespace}' "
            f"timeout={self.default_timeout}s>"
        )
