"""
Redis-Enhanced Agent

Extended BaseAgent with Redis-backed persistent memory.
Supports session-based conversations with distributed state management.
"""

from typing import List, Dict, Optional
from loguru import logger

from backend.app.agents.base_agent import BaseAgent
from backend.app.services.redis_memory import get_redis_memory


class RedisAgent(BaseAgent):
    """
    Agent with Redis-backed persistent memory.

    This agent extends BaseAgent to use Redis for conversation history
    instead of in-memory storage, enabling:
    - Persistence across server restarts
    - Distributed state sharing across multiple instances
    - Session-based conversation tracking
    - Automatic TTL management
    """

    def __init__(
        self,
        agent_id: str,
        session_id: str,
        keep_history: bool = True,
        max_history: int = 10,
        memory_ttl: Optional[int] = None,
        use_redis: bool = True
    ):
        """
        Initialize a Redis-enhanced agent.

        Args:
            agent_id: Unique identifier for the agent (e.g., 'supervisor', 'energy')
            session_id: Session identifier for conversation tracking
            keep_history: Whether to maintain conversation history
            max_history: Maximum number of message pairs to keep in history
            memory_ttl: Time-to-live for Redis keys in seconds (optional)
            use_redis: If False, falls back to in-memory storage
        """
        # Initialize base agent (this sets up agent_id, system_prompt, llm, etc.)
        super().__init__(
            agent_id=agent_id,
            keep_history=keep_history,
            max_history=max_history
        )

        self.session_id = session_id
        self.memory_ttl = memory_ttl
        self.use_redis = use_redis

        if self.use_redis:
            try:
                self.redis_memory = get_redis_memory()

                # Load existing history from Redis
                if self.keep_history:
                    self.history = self.redis_memory.get_conversation_history(
                        agent_id=self.agent_id,
                        session_id=self.session_id
                    )

                    if self.history:
                        logger.info(
                            f"[{self.agent_id}:{self.session_id}] "
                            f"Loaded {len(self.history)} messages from Redis"
                        )

                logger.info(
                    f"Redis-enabled agent '{agent_id}' initialized for session '{session_id}'"
                )
            except Exception as e:
                logger.error(f"Failed to initialize Redis memory, falling back to in-memory: {e}")
                self.use_redis = False
        else:
            logger.info(f"Agent '{agent_id}' using in-memory storage (Redis disabled)")

    def chat(self, message: str, temperature: Optional[float] = None) -> str:
        """
        Send a message to the agent and get a response.
        Automatically saves conversation history to Redis if enabled.

        Args:
            message: User message/question
            temperature: Optional temperature override (0-1)

        Returns:
            str: Agent response
        """
        try:
            logger.info(
                f"[{self.agent_id}:{self.session_id}] "
                f"Received message: {message[:100]}..."
            )

            if self.keep_history and self.history:
                # Use conversation history
                self.history.append({"role": "user", "content": message})

                # Trim history if too long
                if len(self.history) > self.max_history * 2:  # *2 for user+assistant pairs
                    self.history = self.history[-(self.max_history * 2):]

                response = self.llm.chat_with_history(
                    messages=self.history,
                    system_prompt=self.system_prompt,
                    temperature=temperature
                )

                # Add response to history
                self.history.append({"role": "assistant", "content": response})

                # Save to Redis if enabled
                if self.use_redis:
                    self.redis_memory.save_conversation_history(
                        agent_id=self.agent_id,
                        session_id=self.session_id,
                        history=self.history,
                        ttl=self.memory_ttl
                    )

            else:
                # No history - simple chat
                response = self.llm.chat(
                    prompt=message,
                    system_prompt=self.system_prompt,
                    temperature=temperature
                )

            logger.info(
                f"[{self.agent_id}:{self.session_id}] "
                f"Generated response: {response[:100]}..."
            )
            return response

        except Exception as e:
            error_msg = f"Error in {self.agent_id} agent: {str(e)}"
            logger.error(error_msg)
            return f"I apologize, but I encountered an error: {str(e)}"

    def reset_history(self):
        """Clear the conversation history (both in-memory and Redis)"""
        self.history = []

        if self.use_redis:
            self.redis_memory.clear_conversation_history(
                agent_id=self.agent_id,
                session_id=self.session_id
            )

        logger.info(
            f"[{self.agent_id}:{self.session_id}] Conversation history cleared"
        )

    def save_state(self, state: Dict) -> bool:
        """
        Save custom agent state to Redis.

        Args:
            state: State dictionary to save

        Returns:
            bool: True if successful
        """
        if not self.use_redis:
            logger.warning("Redis not enabled, cannot save state")
            return False

        return self.redis_memory.save_agent_state(
            agent_id=f"{self.agent_id}:{self.session_id}",
            state=state,
            ttl=self.memory_ttl
        )

    def load_state(self) -> Optional[Dict]:
        """
        Load custom agent state from Redis.

        Returns:
            State dictionary or None if not found
        """
        if not self.use_redis:
            logger.warning("Redis not enabled, cannot load state")
            return None

        return self.redis_memory.get_agent_state(
            agent_id=f"{self.agent_id}:{self.session_id}"
        )

    def extend_session(self, ttl: Optional[int] = None):
        """
        Extend the TTL of the current session.

        Args:
            ttl: New time-to-live in seconds (optional)
        """
        if not self.use_redis:
            logger.warning("Redis not enabled, cannot extend session")
            return

        self.redis_memory.extend_ttl(
            agent_id=self.agent_id,
            session_id=self.session_id,
            ttl=ttl or self.memory_ttl
        )

    def get_session_info(self) -> Dict:
        """
        Get information about the current session.

        Returns:
            Dictionary with session information
        """
        info = {
            "agent_id": self.agent_id,
            "session_id": self.session_id,
            "use_redis": self.use_redis,
            "keep_history": self.keep_history,
            "history_length": len(self.history),
            "max_history": self.max_history,
            "memory_ttl": self.memory_ttl
        }

        if self.use_redis:
            info["redis_health"] = self.redis_memory.health_check()

        return info

    def __repr__(self) -> str:
        return f"<RedisAgent: {self.agent_id}:{self.session_id}>"
