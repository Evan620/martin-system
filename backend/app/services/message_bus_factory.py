"""
Message Bus Factory

Provides singleton factory function for creating and accessing the
RedisMessageBus instance with configuration from app settings.

Usage:
    from backend.app.services.message_bus_factory import get_message_bus

    message_bus = get_message_bus()
    message_bus.send_message(...)
"""

from typing import Optional
from loguru import logger

import redis
from redis.exceptions import ConnectionError

from backend.app.services.redis_message_bus import RedisMessageBus
from backend.app.core.config import get_settings


# Global singleton instance
_message_bus_instance: Optional[RedisMessageBus] = None


def get_message_bus(force_new: bool = False) -> RedisMessageBus:
    """
    Get the singleton RedisMessageBus instance.

    Creates a new instance on first call, then returns the same instance
    on subsequent calls. Loads configuration from app settings.

    Args:
        force_new: If True, create a new instance even if one exists

    Returns:
        RedisMessageBus instance

    Raises:
        ConnectionError: If Redis connection fails

    Example:
        >>> message_bus = get_message_bus()
        >>> message_bus.send_message(delegation_request)
    """
    global _message_bus_instance

    if _message_bus_instance is None or force_new:
        settings = get_settings()

        # Create Redis client
        try:
            if settings.REDIS_URL:
                # Use URL if provided
                redis_client = redis.from_url(
                    settings.REDIS_URL,
                    decode_responses=False,  # We handle decoding ourselves
                    max_connections=settings.REDIS_MAX_CONNECTIONS
                )
            else:
                # Use individual settings
                redis_client = redis.Redis(
                    host=settings.REDIS_HOST,
                    port=settings.REDIS_PORT,
                    db=settings.REDIS_DB,
                    password=settings.REDIS_PASSWORD if settings.REDIS_PASSWORD else None,
                    decode_responses=False,
                    max_connections=settings.REDIS_MAX_CONNECTIONS
                )

            # Test connection
            redis_client.ping()

            logger.info(
                f"Connected to Redis at {settings.REDIS_HOST}:{settings.REDIS_PORT}"
            )

        except ConnectionError as e:
            logger.error(f"Failed to connect to Redis: {e}")
            raise ConnectionError(
                f"Cannot connect to Redis at {settings.REDIS_HOST}:{settings.REDIS_PORT}. "
                f"Ensure Redis is running and accessible."
            ) from e

        # Create message bus instance
        _message_bus_instance = RedisMessageBus(
            redis_client=redis_client,
            namespace="ecowas",
            default_timeout=settings.MESSAGE_BUS_DEFAULT_TIMEOUT,
            max_queue_size=settings.MESSAGE_BUS_MAX_QUEUE_SIZE,
            message_ttl=settings.MESSAGE_BUS_MESSAGE_TTL
        )

        logger.info("RedisMessageBus singleton instance created")

    return _message_bus_instance


def reset_message_bus() -> None:
    """
    Reset the singleton instance (useful for testing).

    This will force creation of a new instance on next get_message_bus() call.
    """
    global _message_bus_instance
    _message_bus_instance = None
    logger.debug("RedisMessageBus singleton instance reset")


def test_message_bus_connection() -> bool:
    """
    Test if the message bus can connect to Redis.

    Returns:
        True if connection successful, False otherwise

    Example:
        >>> if test_message_bus_connection():
        ...     print("Message bus is ready!")
    """
    try:
        message_bus = get_message_bus()
        return message_bus.health_check()
    except Exception as e:
        logger.error(f"Message bus connection test failed: {e}")
        return False
