"""
LLM Service for AI Agent Integration

This service provides an interface to connect to either a local Ollama instance
or OpenAI-compatible APIs (OpenAI, GitHub Models, Custom vLLM).
"""

import requests
import json
from typing import List, Dict, Optional, Any
from loguru import logger
from app.core.config import settings

try:
    from openai import OpenAI
except ImportError:
    OpenAI = None


class LLMService:
    """Base interface for LLM services"""
    def chat(self, prompt: str, system_prompt: Optional[str] = None, **kwargs) -> Any:
        raise NotImplementedError

    def chat_with_history(self, messages: List[Dict[str, Any]], system_prompt: Optional[str] = None, **kwargs) -> Any:
        raise NotImplementedError

    def structured_output(self, messages: List[Dict[str, Any]], schema: dict, system_prompt: Optional[str] = None, **kwargs) -> dict:
        """
        Generate a guaranteed JSON structured output conforming to the provided JSON Schema.
        """
        raise NotImplementedError

    def transcribe_audio(self, file_path: str, **kwargs) -> str:
        raise NotImplementedError


class OllamaLLMService(LLMService):
    """Service for interacting with local Ollama LLM"""

    def __init__(
        self,
        base_url: str = "http://localhost:11434",
        model: str = "qwen2.5:0.5b",
        temperature: float = 0.7,
        timeout: int = 120
    ):
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.temperature = temperature
        self.timeout = timeout
        self.api_endpoint = f"{self.base_url}/api/generate"

        logger.info(f"Initialized Ollama LLM Service: {self.model} @ {self.base_url}")

    def chat(self, prompt: str, system_prompt: Optional[str] = None, temperature: Optional[float] = None, max_tokens: int = 1000, **kwargs) -> str:
        full_prompt = prompt
        if system_prompt:
            full_prompt = f"{system_prompt}\n\nUser: {prompt}\n\nAssistant:"

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
            response = requests.post(self.api_endpoint, json=payload, timeout=self.timeout)
            response.raise_for_status()
            return response.json().get("response", "").strip()
        except Exception as e:
            logger.error(f"Ollama API error: {e}")
            raise Exception(f"Ollama Error: {str(e)}")

    def chat_with_history(self, messages: List[Dict[str, Any]], system_prompt: Optional[str] = None, temperature: Optional[float] = None, **kwargs) -> str:
        conversation = ""
        if system_prompt:
            conversation = f"{system_prompt}\n\n"

        for msg in messages:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            conversation += f"{role.capitalize()}: {content}\n"

        conversation += "Assistant:"

        payload = {
            "model": self.model,
            "prompt": conversation,
            "stream": False,
            "options": {
                "temperature": temperature if temperature is not None else self.temperature
            }
        }

        try:
            response = requests.post(self.api_endpoint, json=payload, timeout=self.timeout)
            response.raise_for_status()
            return response.json().get("response", "").strip()
        except Exception as e:
            logger.error(f"Ollama History error: {e}")
            raise Exception(f"Ollama Error: {str(e)}")

    def structured_output(self, messages: List[Dict[str, Any]], schema: dict, system_prompt: Optional[str] = None, **kwargs) -> dict:
        """Fallback structured output (Ollama doesn't natively support OpenAI json_schema response_format yet)"""
        if system_prompt:
             system_prompt += f"\n\nYou MUST return only valid JSON matching this schema: {json.dumps(schema)}"
        else:
             system_prompt = f"You MUST return only valid JSON matching this schema: {json.dumps(schema)}"
        
        response_text = self.chat_with_history(messages, system_prompt=system_prompt)
        try:
            # Strip markdown if present
            clean_text = response_text.replace("```json", "").replace("```", "").strip()
            return json.loads(clean_text)
        except Exception as e:
            logger.error(f"Failed to parse Ollama structured output: {e}\nResponse: {response_text}")
            raise Exception("Failed to generate valid structured output")


class OpenAILLMService(LLMService):
    """Service for interacting with OpenAI-compatible APIs"""

    def __init__(self, api_key: str, model: str = "gpt-4-turbo-preview", temperature: float = 0.7, base_url: Optional[str] = None):
        if not OpenAI:
            raise ImportError("openai package not installed. Run 'pip install openai'")
        
        self.client = OpenAI(api_key=api_key, base_url=base_url)
        self.model = model
        self.temperature = temperature
        logger.info(f"Initialized OpenAILLMService: {self.model} (Base URL: {base_url or 'Default'})")

    def chat(self, prompt: str, system_prompt: Optional[str] = None, temperature: Optional[float] = None, max_tokens: int = 2000, tools: Optional[List[Dict]] = None, model: Optional[str] = None, response_format: Optional[Dict] = None, tool_choice: Optional[Any] = None, **kwargs) -> Any:
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        # Diagnostic log
        logger.info(f"[OpenAILLMService] Connecting to: {self.client.base_url} (Model: {self.model})")
        
        create_kwargs: Dict[str, Any] = {
            "model": model or self.model,
            "messages": messages,
            "temperature": temperature if temperature is not None else self.temperature,
            "max_tokens": max_tokens
        }
        
        if tools:
            create_kwargs["tools"] = tools
        if response_format:
            create_kwargs["response_format"] = response_format
        if tool_choice:
            create_kwargs["tool_choice"] = tool_choice

        try:
            response = self.client.chat.completions.create(**create_kwargs)
            message = response.choices[0].message
            
            if message.tool_calls:
                 return message
            
            return (message.content or "").strip()
        except Exception as e:
            logger.error(f"OpenAI API error: {e}")
            raise Exception(f"OpenAI Error: {str(e)}")

    def chat_with_history(self, messages: List[Dict[str, Any]], system_prompt: Optional[str] = None, temperature: Optional[float] = None, tools: Optional[List[Dict]] = None, model: Optional[str] = None, response_format: Optional[Dict] = None, tool_choice: Optional[Any] = None, **kwargs) -> Any:
        full_messages = []
        if system_prompt:
            full_messages.append({"role": "system", "content": system_prompt})

        # Diagnostic log
        logger.info(f"[OpenAILLMService:History] Connecting to: {self.client.base_url} (Model: {self.model})")
        
        for m in messages:
            role = m.get("role", "user")
            if role not in ["system", "user", "assistant", "tool", "function"]:
                 if role == "model": role = "assistant"
                 else: role = "user"
            
            msg_obj: Dict[str, Any] = {"role": role, "content": m.get("content", "")}
            
            if "tool_calls" in m and m["tool_calls"]:
                msg_obj["tool_calls"] = m["tool_calls"]
            if "tool_call_id" in m:
                msg_obj["tool_call_id"] = m["tool_call_id"]
            if "name" in m:
                 msg_obj["name"] = m["name"]
                 
            full_messages.append(msg_obj)

        create_kwargs: Dict[str, Any] = {
            "model": model or self.model,
            "messages": full_messages,
            "temperature": temperature if temperature is not None else self.temperature
        }
        
        if tools:
            create_kwargs["tools"] = tools
        if response_format:
            create_kwargs["response_format"] = response_format
        if tool_choice:
            create_kwargs["tool_choice"] = tool_choice

        try:
            response = self.client.chat.completions.create(**create_kwargs)
            message = response.choices[0].message
            
            if message.tool_calls:
                 return message
                 
            return (message.content or "").strip()
        except Exception as e:
            logger.error(f"OpenAI History error: {e}")
            raise Exception(f"OpenAI Error: {str(e)}")

    def structured_output(self, messages: List[Dict[str, Any]], schema: dict, system_prompt: Optional[str] = None, **kwargs) -> dict:
        """
        Use OpenAI's response_format: {"type": "json_schema"} for structured data.
        """
        response_format = {
            "type": "json_schema",
            "json_schema": {
                "name": "structured_response",
                "schema": schema,
                "strict": True
            }
        }
        
        raw_response = self.chat_with_history(
            messages=messages,
            system_prompt=system_prompt,
            response_format=response_format,
            **kwargs
        )
        
        try:
            return json.loads(raw_response)
        except Exception as e:
            logger.error(f"Failed to parse structured output payload: {e}")
            raise Exception("Invalid structured output returned by logic model.")

    def transcribe_audio(self, file_path: str, model: str = "whisper-1", **kwargs) -> str:
        """
        Transcribe audio file using OpenAI Whisper.
        """
        try:
            with open(file_path, "rb") as file:
                transcription = self.client.audio.transcriptions.create(
                    file=file,
                    model=model,
                    response_format="text",
                    temperature=0.0
                )
            logger.info("Transcribed audio using OPENAI Whisper")
            return transcription
        except Exception as e:
            logger.error(f"OpenAI Transcription error: {e}")
            raise Exception(f"OpenAI Transcription Error: {str(e)}")


# Singleton instance
_llm_service: Optional[LLMService] = None


def get_llm_service() -> LLMService:
    """
    Get or create the LLM service singleton based on configuration.
    """
    global _llm_service
    if _llm_service is None:
        provider = getattr(settings, "LLM_PROVIDER", "ollama").lower()
        logger.info(f"Selecting LLM Provider: {provider}")
        
        if provider == "openai" and getattr(settings, "OPENAI_API_KEY", None):
            _llm_service = OpenAILLMService(
                api_key=settings.OPENAI_API_KEY,
                model=getattr(settings, "OPENAI_MODEL", "gpt-4-turbo-preview"),
                temperature=settings.LLM_TEMPERATURE
            )
        elif provider == "custom" and getattr(settings, "CUSTOM_LLM_BASE_URL", None):
             logger.info(f"[CUSTOM] Connecting to vLLM at: {settings.CUSTOM_LLM_BASE_URL} (Model: {settings.CUSTOM_LLM_MODEL})")
             _llm_service = OpenAILLMService(
                api_key=settings.CUSTOM_LLM_API_KEY,
                model=settings.CUSTOM_LLM_MODEL,
                temperature=settings.LLM_TEMPERATURE,
                base_url=settings.CUSTOM_LLM_BASE_URL
            )
        elif provider == "github" and getattr(settings, "GITHUB_TOKEN", None):
             _llm_service = OpenAILLMService(
                api_key=settings.GITHUB_TOKEN,
                model=getattr(settings, "GITHUB_MODEL", "gpt-4o-mini").replace("openai/", ""),
                temperature=settings.LLM_TEMPERATURE,
                base_url=settings.GITHUB_BASE_URL
            )
        elif provider == "gemini" and getattr(settings, "GEMINI_API_KEY", None):
             _llm_service = OpenAILLMService(
                api_key=settings.GEMINI_API_KEY,
                model=getattr(settings, "GEMINI_MODEL", "gemini-1.5-pro"),
                temperature=settings.LLM_TEMPERATURE,
                base_url="https://generativelanguage.googleapis.com/v1beta/openai/"
            )
        else:
            if provider != "ollama":
                logger.warning(f"Provider '{provider}' selected but not configured or unsupported. Falling back to Ollama.")
            
            _llm_service = OllamaLLMService(
                base_url=settings.OLLAMA_BASE_URL,
                model=settings.OLLAMA_MODEL,
                temperature=settings.LLM_TEMPERATURE,
                timeout=settings.LLM_TIMEOUT
            )
    return _llm_service


# Create singleton instance for import
llm_service = get_llm_service()
