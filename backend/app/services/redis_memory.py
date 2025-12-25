"""
Redis Memory Service

Provides persistent, distributed memory storage for agent conversations using Redis.
Supports conversation history tracking, session management, and cross-instance state sharing.
"""

import json
from typing import List, Dict, Optional, Any
from datetime import timedelta
import redis
from loguru import logger


class RedisMemoryService:
    """Redis-based memory service for agent conversation persistence"""

    def __init__(
        self,
        host: str = "localhost",
        port: int = 6379,
        db: int = 0,
        password: Optional[str] = None,
        default_ttl: int = 86400  # 24 hours in seconds
    ):
        """
        Initialize Redis memory service.

        Args:
            host: Redis server host
            port: Redis server port
            db: Redis database number
            password: Redis password (optional)
            default_ttl: Default time-to-live for keys in seconds (default: 24h)
        """
        self.default_ttl = default_ttl

        try:
            self.client = redis.Redis(
                host=host,
                port=port,
                db=db,
                password=password,
                decode_responses=True,
                socket_connect_timeout=5,
                socket_keepalive=True
            )
            # Test connection
            self.client.ping()
            logger.info(f"Redis Memory Service connected to {host}:{port}")
        except redis.ConnectionError as e:
            logger.error(f"Failed to connect to Redis: {e}")
            raise Exception(f"Cannot connect to Redis at {host}:{port}")

    def _make_key(self, namespace: str, identifier: str) -> str:
        """
        Create a Redis key with namespace.

        Args:
            namespace: Key namespace (e.g., 'agent', 'session')
            identifier: Unique identifier

        Returns:
            Formatted Redis key
        """
        return f"ecowas:{namespace}:{identifier}"

    def save_conversation_history(
        self,
        agent_id: str,
        session_id: str,
        history: List[Dict[str, str]],
        ttl: Optional[int] = None
    ) -> bool:
        """
        Save conversation history to Redis.

        Args:
            agent_id: Agent identifier
            session_id: Session identifier
            history: List of message dictionaries
            ttl: Time-to-live in seconds (optional, uses default if not provided)

        Returns:
            bool: True if successful, False otherwise
        """
        try:
            key = self._make_key("history", f"{agent_id}:{session_id}")
            value = json.dumps(history)
            ttl = ttl or self.default_ttl

            self.client.setex(key, ttl, value)
            logger.debug(f"Saved history for {agent_id}:{session_id} (TTL: {ttl}s)")
            return True
        except Exception as e:
            logger.error(f"Failed to save conversation history: {e}")
            return False

    def get_conversation_history(
        self,
        agent_id: str,
        session_id: str
    ) -> List[Dict[str, str]]:
        """
        Retrieve conversation history from Redis.

        Args:
            agent_id: Agent identifier
            session_id: Session identifier

        Returns:
            List of message dictionaries (empty list if not found)
        """
        try:
            key = self._make_key("history", f"{agent_id}:{session_id}")
            value = self.client.get(key)

            if value is None:
                logger.debug(f"No history found for {agent_id}:{session_id}")
                return []

            history = json.loads(value)
            logger.debug(f"Retrieved {len(history)} messages for {agent_id}:{session_id}")
            return history
        except Exception as e:
            logger.error(f"Failed to get conversation history: {e}")
            return []

    def append_to_history(
        self,
        agent_id: str,
        session_id: str,
        message: Dict[str, str],
        max_history: Optional[int] = None,
        ttl: Optional[int] = None
    ) -> bool:
        """
        Append a message to conversation history.

        Args:
            agent_id: Agent identifier
            session_id: Session identifier
            message: Message dictionary with 'role' and 'content'
            max_history: Maximum number of messages to keep (optional)
            ttl: Time-to-live in seconds (optional)

        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Get current history
            history = self.get_conversation_history(agent_id, session_id)

            # Append new message
            history.append(message)

            # Trim if max_history is specified
            if max_history and len(history) > max_history:
                history = history[-max_history:]

            # Save updated history
            return self.save_conversation_history(agent_id, session_id, history, ttl)
        except Exception as e:
            logger.error(f"Failed to append to history: {e}")
            return False

    def clear_conversation_history(
        self,
        agent_id: str,
        session_id: str
    ) -> bool:
        """
        Clear conversation history for a session.

        Args:
            agent_id: Agent identifier
            session_id: Session identifier

        Returns:
            bool: True if successful, False otherwise
        """
        try:
            key = self._make_key("history", f"{agent_id}:{session_id}")
            self.client.delete(key)
            logger.info(f"Cleared history for {agent_id}:{session_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to clear conversation history: {e}")
            return False

    def save_agent_state(
        self,
        agent_id: str,
        state: Dict[str, Any],
        ttl: Optional[int] = None
    ) -> bool:
        """
        Save agent state to Redis.

        Args:
            agent_id: Agent identifier
            state: State dictionary
            ttl: Time-to-live in seconds (optional)

        Returns:
            bool: True if successful, False otherwise
        """
        try:
            key = self._make_key("state", agent_id)
            value = json.dumps(state)
            ttl = ttl or self.default_ttl

            self.client.setex(key, ttl, value)
            logger.debug(f"Saved state for {agent_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to save agent state: {e}")
            return False

    def get_agent_state(self, agent_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve agent state from Redis.

        Args:
            agent_id: Agent identifier

        Returns:
            State dictionary or None if not found
        """
        try:
            key = self._make_key("state", agent_id)
            value = self.client.get(key)

            if value is None:
                logger.debug(f"No state found for {agent_id}")
                return None

            state = json.loads(value)
            logger.debug(f"Retrieved state for {agent_id}")
            return state
        except Exception as e:
            logger.error(f"Failed to get agent state: {e}")
            return None

    def set_session_data(
        self,
        session_id: str,
        key: str,
        value: Any,
        ttl: Optional[int] = None
    ) -> bool:
        """
        Store arbitrary session data.

        Args:
            session_id: Session identifier
            key: Data key
            value: Data value (will be JSON serialized)
            ttl: Time-to-live in seconds (optional)

        Returns:
            bool: True if successful, False otherwise
        """
        try:
            redis_key = self._make_key("session", f"{session_id}:{key}")
            serialized = json.dumps(value)
            ttl = ttl or self.default_ttl

            self.client.setex(redis_key, ttl, serialized)
            logger.debug(f"Set session data {key} for {session_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to set session data: {e}")
            return False

    def get_session_data(self, session_id: str, key: str) -> Optional[Any]:
        """
        Retrieve session data.

        Args:
            session_id: Session identifier
            key: Data key

        Returns:
            Data value or None if not found
        """
        try:
            redis_key = self._make_key("session", f"{session_id}:{key}")
            value = self.client.get(redis_key)

            if value is None:
                return None

            return json.loads(value)
        except Exception as e:
            logger.error(f"Failed to get session data: {e}")
            return None

    def get_all_sessions_for_agent(self, agent_id: str) -> List[str]:
        """
        Get all active session IDs for an agent.

        Args:
            agent_id: Agent identifier

        Returns:
            List of session IDs
        """
        try:
            pattern = self._make_key("history", f"{agent_id}:*")
            keys = self.client.keys(pattern)

            # Extract session IDs from keys
            sessions = []
            prefix = self._make_key("history", f"{agent_id}:")
            for key in keys:
                session_id = key[len(prefix):]
                sessions.append(session_id)

            logger.debug(f"Found {len(sessions)} sessions for {agent_id}")
            return sessions
        except Exception as e:
            logger.error(f"Failed to get sessions for agent: {e}")
            return []

    def extend_ttl(
        self,
        agent_id: str,
        session_id: str,
        ttl: Optional[int] = None
    ) -> bool:
        """
        Extend the TTL of a conversation history.

        Args:
            agent_id: Agent identifier
            session_id: Session identifier
            ttl: New time-to-live in seconds (optional, uses default if not provided)

        Returns:
            bool: True if successful, False otherwise
        """
        try:
            key = self._make_key("history", f"{agent_id}:{session_id}")
            ttl = ttl or self.default_ttl

            self.client.expire(key, ttl)
            logger.debug(f"Extended TTL for {agent_id}:{session_id} to {ttl}s")
            return True
        except Exception as e:
            logger.error(f"Failed to extend TTL: {e}")
            return False

    def get_memory_stats(self) -> Dict[str, Any]:
        """
        Get memory usage statistics.

        Returns:
            Dictionary with Redis memory statistics
        """
        try:
            info = self.client.info("memory")
            stats = {
                "used_memory": info.get("used_memory_human", "N/A"),
                "used_memory_peak": info.get("used_memory_peak_human", "N/A"),
                "total_keys": self.client.dbsize(),
                "connected": True
            }
            return stats
        except Exception as e:
            logger.error(f"Failed to get memory stats: {e}")
            return {"connected": False, "error": str(e)}

    def clear_all_agent_data(self, agent_id: str) -> int:
        """
        Clear all data for a specific agent (history, state, etc.).

        Args:
            agent_id: Agent identifier

        Returns:
            Number of keys deleted
        """
        try:
            patterns = [
                self._make_key("history", f"{agent_id}:*"),
                self._make_key("state", agent_id)
            ]

            deleted = 0
            for pattern in patterns:
                keys = self.client.keys(pattern)
                if keys:
                    deleted += self.client.delete(*keys)

            logger.info(f"Cleared {deleted} keys for agent {agent_id}")
            return deleted
        except Exception as e:
            logger.error(f"Failed to clear agent data: {e}")
            return 0

    def health_check(self) -> bool:
        """
        Check if Redis connection is healthy.

        Returns:
            bool: True if healthy, False otherwise
        """
        try:
            return self.client.ping()
        except Exception as e:
            logger.error(f"Redis health check failed: {e}")
            return False

    def close(self):
        """Close Redis connection"""
        try:
            self.client.close()
            logger.info("Redis connection closed")
        except Exception as e:
            logger.error(f"Error closing Redis connection: {e}")


# Singleton instance
_redis_memory = None


def get_redis_memory(
    host: str = "localhost",
    port: int = 6379,
    db: int = 0,
    password: Optional[str] = None
) -> RedisMemoryService:
    """
    Get or create the Redis memory service singleton.

    Args:
        host: Redis server host
        port: Redis server port
        db: Redis database number
        password: Redis password (optional)

    Returns:
        RedisMemoryService: The memory service instance
    """
    global _redis_memory
    if _redis_memory is None:
        _redis_memory = RedisMemoryService(
            host=host,
            port=port,
            db=db,
            password=password
        )
    return _redis_memory
