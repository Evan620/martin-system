"""
Redis Memory Factory

Factory functions to create Redis memory service from configuration.
"""

from typing import Optional
from loguru import logger

from app.services.redis_memory import RedisMemoryService, get_redis_memory
from app.core.config import get_settings


def create_redis_memory_from_config() -> Optional[RedisMemoryService]:
    """
    Create Redis memory service from application configuration.

    Returns:
        RedisMemoryService instance or None if connection fails
    """
    try:
        settings = get_settings()

        redis_memory = get_redis_memory(
            host=settings.REDIS_HOST,
            port=settings.REDIS_PORT,
            db=settings.REDIS_DB,
            password=settings.REDIS_PASSWORD
        )

        # Override default TTL if configured
        redis_memory.default_ttl = settings.REDIS_MEMORY_TTL

        logger.info(
            f"Redis memory service initialized from config: "
            f"{settings.REDIS_HOST}:{settings.REDIS_PORT}/{settings.REDIS_DB}"
        )

        return redis_memory

    except Exception as e:
        logger.error(f"Failed to create Redis memory service from config: {e}")
        return None


def test_redis_connection() -> bool:
    """
    Test Redis connection using configuration settings.

    Returns:
        bool: True if connection successful, False otherwise
    """
    try:
        redis_memory = create_redis_memory_from_config()

        if redis_memory is None:
            logger.error("Redis memory service creation failed")
            return False

        # Test health check
        if not redis_memory.health_check():
            logger.error("Redis health check failed")
            return False

        # Test basic operations
        test_key = "test_connection"
        test_value = {"test": "data", "timestamp": "2025-12-25"}

        # Save test data
        redis_memory.set_session_data("test-session", test_key, test_value, ttl=60)

        # Retrieve test data
        retrieved = redis_memory.get_session_data("test-session", test_key)

        if retrieved != test_value:
            logger.error("Redis read/write test failed")
            return False

        # Get stats
        stats = redis_memory.get_memory_stats()
        logger.info(f"Redis stats: {stats}")

        logger.info("✅ Redis connection test successful!")
        return True

    except Exception as e:
        logger.error(f"Redis connection test failed: {e}")
        return False
