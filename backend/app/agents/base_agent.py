"""
Base Agent Class

Provides common functionality for all TWG agents including:
- LLM initialization
- System prompt loading
- Chat interface
- Conversation history management (in-memory or Redis)
- Logging
"""

from typing import List, Dict, Optional
from loguru import logger

from backend.app.services.llm_service import get_llm_service
from backend.app.agents.prompts import get_prompt


class BaseAgent:
    """Base class for all TWG agents with optional Redis memory"""

    def __init__(
        self,
        agent_id: str,
        keep_history: bool = False,
        max_history: int = 10,
        session_id: Optional[str] = None,
        use_redis: bool = False,
        memory_ttl: Optional[int] = None
    ):
        """
        Initialize a base agent.

        Args:
            agent_id: Unique identifier for the agent (e.g., 'supervisor', 'energy')
            keep_history: Whether to maintain conversation history
            max_history: Maximum number of messages to keep in history
            session_id: Session identifier for Redis-based memory (optional)
            use_redis: If True, use Redis for persistent memory
            memory_ttl: TTL for Redis keys in seconds (optional)
        """
        self.agent_id = agent_id
        self.keep_history = keep_history
        self.max_history = max_history
        self.session_id = session_id or "default"
        self.use_redis = use_redis
        self.memory_ttl = memory_ttl

        # Load system prompt for this agent
        try:
            self.system_prompt = get_prompt(agent_id)
            logger.info(f"Initialized {agent_id} agent with system prompt")
        except ValueError as e:
            logger.error(f"Failed to load prompt for {agent_id}: {e}")
            raise

        # Get LLM service
        self.llm = get_llm_service()

        # Conversation history
        self.history: List[Dict[str, str]] = []

        # Initialize Redis memory if enabled
        self.redis_memory = None
        if self.use_redis:
            try:
                from backend.app.services.redis_memory import get_redis_memory
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
                logger.info(f"Agent '{agent_id}' using Redis memory for session '{self.session_id}'")
            except Exception as e:
                logger.warning(f"Failed to initialize Redis memory, using in-memory: {e}")
                self.use_redis = False

        logger.info(f"Agent '{agent_id}' initialized successfully")

    def chat(self, message: str, temperature: Optional[float] = None) -> str:
        """
        Send a message to the agent and get a response.
        Automatically saves to Redis if enabled.

        Args:
            message: User message/question
            temperature: Optional temperature override (0-1)

        Returns:
            str: Agent response
        """
        try:
            session_info = f"[{self.agent_id}:{self.session_id}]" if self.use_redis else f"[{self.agent_id}]"
            logger.info(f"{session_info} Received message: {message[:100]}...")

            if self.keep_history:
                # Add user message to history
                self.history.append({"role": "user", "content": message})

                # Trim history if too long
                if len(self.history) > self.max_history * 2:  # *2 for user+assistant pairs
                    self.history = self.history[-(self.max_history * 2):]

                # Use history if we have messages
                if len(self.history) > 1:
                    response = self.llm.chat_with_history(
                        messages=self.history,
                        system_prompt=self.system_prompt,
                        temperature=temperature
                    )
                else:
                    # First message - use simple chat
                    response = self.llm.chat(
                        prompt=message,
                        system_prompt=self.system_prompt,
                        temperature=temperature
                    )

                # Add response to history
                self.history.append({"role": "assistant", "content": response})

                # Save to Redis if enabled
                if self.use_redis and self.redis_memory:
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

            logger.info(f"{session_info} Generated response: {response[:100]}...")
            return response

        except Exception as e:
            error_msg = f"Error in {self.agent_id} agent: {str(e)}"
            logger.error(error_msg)
            return f"I apologize, but I encountered an error: {str(e)}"

    def reset_history(self):
        """Clear the conversation history (both in-memory and Redis)"""
        self.history = []

        # Clear from Redis if enabled
        if self.use_redis and self.redis_memory:
            self.redis_memory.clear_conversation_history(
                agent_id=self.agent_id,
                session_id=self.session_id
            )

        session_info = f"[{self.agent_id}:{self.session_id}]" if self.use_redis else f"[{self.agent_id}]"
        logger.info(f"{session_info} Conversation history cleared")

    def get_history(self) -> List[Dict[str, str]]:
        """
        Get the current conversation history.

        Returns:
            List of message dictionaries
        """
        return self.history.copy()

    def get_agent_info(self) -> Dict[str, any]:
        """
        Get information about this agent.

        Returns:
            Dictionary with agent metadata
        """
        return {
            "agent_id": self.agent_id,
            "system_prompt": self.system_prompt[:200] + "...",  # Truncated
            "keep_history": self.keep_history,
            "max_history": self.max_history,
            "history_length": len(self.history)
        }

    def __repr__(self) -> str:
        return f"<Agent: {self.agent_id}>"
