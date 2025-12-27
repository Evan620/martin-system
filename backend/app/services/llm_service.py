"""
LLM Service for Local Ollama Integration

This service provides an interface to connect to a local Ollama instance
running the qwen2.5:0.5b model for AI agent interactions.
"""

import requests
from typing import List, Dict, Optional
from loguru import logger
from app.core.config import settings


class OllamaLLMService:
    """Service for interacting with local Ollama LLM"""

    def __init__(
        self,
        base_url: str = "http://localhost:11434",
        model: str = "qwen2.5:0.5b",
        temperature: float = 0.7,
        timeout: int = 120
    ):
        """
        Initialize the Ollama LLM service.

        Args:
            base_url: Ollama server URL
            model: Model name to use
            temperature: Sampling temperature (0-1)
            timeout: Request timeout in seconds (default: 120)
        """
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.temperature = temperature
        self.timeout = timeout
        self.api_endpoint = f"{self.base_url}/api/generate"

        logger.info(f"Initialized Ollama LLM Service: {self.model} @ {self.base_url} (timeout: {timeout}s)")

    def check_connection(self) -> bool:
        """
        Check if Ollama server is reachable.

        Returns:
            bool: True if server is reachable, False otherwise
        """
        try:
            response = requests.get(f"{self.base_url}/api/tags", timeout=5)
            return response.status_code == 200
        except Exception as e:
            logger.error(f"Ollama connection check failed: {e}")
            return False

    def chat(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: int = 1000
    ) -> str:
        """
        Send a chat message to the LLM and get a response.

        Args:
            prompt: User message/prompt
            system_prompt: Optional system prompt to set context
            temperature: Override default temperature
            max_tokens: Maximum tokens in response

        Returns:
            str: LLM response text

        Raises:
            Exception: If API request fails
        """
        # Build the full prompt with system context
        full_prompt = prompt
        if system_prompt:
            full_prompt = f"{system_prompt}\n\nUser: {prompt}\n\nAssistant:"

        # Prepare request payload
        payload = {
            "model": self.model,
            "prompt": full_prompt,
            "stream": False,
            "options": {
                "temperature": temperature if temperature is not None else self.temperature,
                "num_predict": max_tokens
            }
        }

        try:
            logger.debug(f"Sending request to Ollama: {full_prompt[:100]}...")
            response = requests.post(
                self.api_endpoint,
                json=payload,
                timeout=self.timeout
            )
            response.raise_for_status()

            result = response.json()
            response_text = result.get("response", "").strip()

            logger.debug(f"Received response: {response_text[:100]}...")
            return response_text

        except requests.exceptions.Timeout:
            logger.error(f"Ollama request timed out after {self.timeout}s")
            raise Exception(
                f"LLM request timed out after {self.timeout} seconds. "
                f"The model '{self.model}' may be slow or not loaded. "
                f"Try running: ollama run {self.model}"
            )
        except requests.exceptions.ConnectionError:
            logger.error("Cannot connect to Ollama server")
            raise Exception(
                f"Cannot connect to Ollama at {self.base_url}. "
                f"Make sure Ollama is running: ollama serve"
            )
        except Exception as e:
            logger.error(f"Ollama API error: {e}")
            raise Exception(f"LLM API error: {str(e)}")

    def chat_with_history(
        self,
        messages: List[Dict[str, str]],
        system_prompt: Optional[str] = None,
        temperature: Optional[float] = None
    ) -> str:
        """
        Chat with conversation history.

        Args:
            messages: List of message dicts with 'role' and 'content'
                     Example: [{"role": "user", "content": "Hello"}]
            system_prompt: Optional system prompt
            temperature: Override default temperature

        Returns:
            str: LLM response
        """
        # Build conversation context
        conversation = ""
        if system_prompt:
            conversation = f"{system_prompt}\n\n"

        for msg in messages:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            if role == "user":
                conversation += f"User: {content}\n"
            elif role == "assistant":
                conversation += f"Assistant: {content}\n"

        conversation += "Assistant:"

        # Send to Ollama
        payload = {
            "model": self.model,
            "prompt": conversation,
            "stream": False,
            "options": {
                "temperature": temperature if temperature is not None else self.temperature
            }
        }

        try:
            response = requests.post(
                self.api_endpoint,
                json=payload,
                timeout=self.timeout
            )
            response.raise_for_status()

            result = response.json()
            return result.get("response", "").strip()

        except Exception as e:
            logger.error(f"Chat with history failed: {e}")
            raise Exception(f"LLM API error: {str(e)}")


# Singleton instance
_llm_service = None


def get_llm_service() -> OllamaLLMService:
    """
    Get or create the LLM service singleton.

    Returns:
        OllamaLLMService: The LLM service instance
    """
    global _llm_service
    if _llm_service is None:
        _llm_service = OllamaLLMService(
            base_url=settings.OLLAMA_BASE_URL,
            model=settings.OLLAMA_MODEL,
            temperature=settings.LLM_TEMPERATURE,
            timeout=settings.LLM_TIMEOUT
        )
    return _llm_service
