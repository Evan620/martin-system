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

try:
    import anthropic as anthropic_sdk
except ImportError:
    anthropic_sdk = None


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


# ---------------------------------------------------------------------------
# Anthropic (Claude) adapter wrappers
# ---------------------------------------------------------------------------
# The LangGraph agent at langgraph_base_agent.py:552-567 expects OpenAI
# message shape: response_obj.tool_calls[i].function.name / .arguments / .id
# and response_obj.content.  Anthropic returns tool_use content blocks, so
# we bridge with thin adapter objects.

class _ToolFunction:
    """Adapter to match OpenAI's tool_call.function shape."""
    def __init__(self, name: str, arguments: str):
        self.name = name
        self.arguments = arguments  # JSON string

class _ToolCall:
    """Adapter to match OpenAI's tool_call shape."""
    def __init__(self, id: str, function: _ToolFunction):
        self.id = id
        self.function = function

class _AnthropicResponseWrapper:
    """Wraps an Anthropic response to match OpenAI message shape expected by langgraph_base_agent."""
    def __init__(self, content: str, tool_calls: list):
        self.content = content
        self.tool_calls = tool_calls if tool_calls else None


class AnthropicLLMService(LLMService):
    """Service for interacting with Anthropic Claude API (native SDK)."""

    def __init__(
        self,
        api_key: str,
        model: str = "claude-sonnet-4-6",
        temperature: float = 0.7,
        max_tokens: int = 4000,
    ):
        if not anthropic_sdk:
            raise ImportError("anthropic package not installed. Run 'pip install anthropic'")

        self.client = anthropic_sdk.Anthropic(api_key=api_key)
        self.model = model
        self.temperature = temperature
        self.max_tokens = max_tokens
        logger.info(f"Initialized AnthropicLLMService: {self.model}")

    # ---- helpers ----------------------------------------------------------

    @staticmethod
    def _convert_tools_openai_to_anthropic(tools: List[Dict]) -> List[Dict]:
        """Convert OpenAI-format tool definitions to Anthropic format.

        OpenAI:  {"type": "function", "function": {"name": ..., "description": ..., "parameters": {...}}}
        Anthropic: {"name": ..., "description": ..., "input_schema": {...}}

        Also sanitizes JSON Schema features Anthropic doesn't support (anyOf, oneOf).
        """
        def _sanitize_property(prop: Dict, prop_name: str = "", tool_name: str = "") -> Dict:
            """Replace anyOf/oneOf and strip 'default' for Anthropic compatibility."""
            sanitized = False

            if "anyOf" in prop:
                for option in prop["anyOf"]:
                    if option.get("type") != "null":
                        result = {**option}
                        if "description" in prop:
                            result["description"] = prop["description"]
                        result.pop("default", None)
                        logger.debug(f"[Anthropic] Sanitized anyOf in {tool_name}.{prop_name}")
                        return result
                return {"type": "string", "description": prop.get("description", "")}

            if "oneOf" in prop:
                for option in prop["oneOf"]:
                    if option.get("type") != "null":
                        result = {**option}
                        if "description" in prop:
                            result["description"] = prop["description"]
                        result.pop("default", None)
                        logger.debug(f"[Anthropic] Sanitized oneOf in {tool_name}.{prop_name}")
                        return result
                return {"type": "string", "description": prop.get("description", "")}

            # Strip 'default' — Anthropic doesn't support it in tool schemas
            if "default" in prop:
                result = {k: v for k, v in prop.items() if k != "default"}
                logger.debug(f"[Anthropic] Stripped 'default' from {tool_name}.{prop_name}")
                return result

            return prop

        def _sanitize_schema(schema: Dict, tool_name: str = "") -> Dict:
            """Sanitize entire input_schema for Anthropic."""
            result = {**schema}
            if "properties" in result:
                result["properties"] = {
                    k: _sanitize_property(v, prop_name=k, tool_name=tool_name)
                    for k, v in result["properties"].items()
                }
            return result

        converted = []
        for t in tools:
            func = t.get("function", t)  # handle both wrapped and unwrapped
            tool_name = func.get("name", "unknown")
            raw_schema = func.get("parameters", func.get("input_schema", {"type": "object", "properties": {}}))
            converted.append({
                "name": tool_name,
                "description": func.get("description", ""),
                "input_schema": _sanitize_schema(raw_schema, tool_name=tool_name),
            })
        return converted

    @staticmethod
    def _wrap_response(response) -> Any:
        """Wrap an Anthropic Message into the OpenAI shape the agent expects."""
        text_parts = []
        tool_calls = []

        for block in response.content:
            if block.type == "text":
                text_parts.append(block.text)
            elif block.type == "tool_use":
                tool_calls.append(
                    _ToolCall(
                        id=block.id,
                        function=_ToolFunction(
                            name=block.name,
                            arguments=json.dumps(block.input),
                        ),
                    )
                )

        content = "\n".join(text_parts) if text_parts else ""
        return _AnthropicResponseWrapper(content=content, tool_calls=tool_calls)

    # ---- interface --------------------------------------------------------

    def chat(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: int = 2000,
        tools: Optional[List[Dict]] = None,
        **kwargs,
    ) -> Any:
        messages = [{"role": "user", "content": prompt}]

        create_kwargs: Dict[str, Any] = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature if temperature is not None else self.temperature,
            "max_tokens": max_tokens,
        }
        if system_prompt:
            create_kwargs["system"] = system_prompt
        if tools:
            create_kwargs["tools"] = self._convert_tools_openai_to_anthropic(tools)

        try:
            response = self.client.messages.create(**create_kwargs)
            wrapped = self._wrap_response(response)

            if wrapped.tool_calls:
                return wrapped

            return (wrapped.content or "").strip()
        except Exception as e:
            logger.error(f"Anthropic API error: {e}")
            raise Exception(f"Anthropic Error: {str(e)}")

    def chat_with_history(
        self,
        messages: List[Dict[str, Any]],
        system_prompt: Optional[str] = None,
        temperature: Optional[float] = None,
        tools: Optional[List[Dict]] = None,
        **kwargs,
    ) -> Any:
        anthropic_messages: List[Dict[str, Any]] = []
        system_text = system_prompt or ""

        for m in messages:
            role = m.get("role", "user")
            content = m.get("content", "")

            # --- system messages → collect into system param ---------------
            if role == "system":
                system_text = f"{system_text}\n{content}" if system_text else content
                continue

            # --- tool result messages → Anthropic user message with tool_result block
            if role == "tool":
                anthropic_messages.append({
                    "role": "user",
                    "content": [
                        {
                            "type": "tool_result",
                            "tool_use_id": m.get("tool_call_id", ""),
                            "content": content if content else "",
                        }
                    ],
                })
                continue

            # --- assistant messages (may contain tool_calls) ---------------
            if role == "assistant":
                if "tool_calls" in m and m["tool_calls"]:
                    # Build content blocks: optional text + tool_use blocks
                    blocks: List[Dict[str, Any]] = []
                    if content:
                        blocks.append({"type": "text", "text": content})
                    for tc in m["tool_calls"]:
                        func = tc.get("function", {})
                        args_raw = func.get("arguments", "{}")
                        try:
                            args_parsed = json.loads(args_raw) if isinstance(args_raw, str) else args_raw
                        except json.JSONDecodeError:
                            args_parsed = {}
                        blocks.append({
                            "type": "tool_use",
                            "id": tc.get("id", ""),
                            "name": func.get("name", ""),
                            "input": args_parsed,
                        })
                    anthropic_messages.append({"role": "assistant", "content": blocks})
                else:
                    anthropic_messages.append({"role": "assistant", "content": content or ""})
                continue

            # --- user / other → user message --------------------------------
            anthropic_messages.append({"role": "user", "content": content or ""})

        # Anthropic requires messages to alternate user/assistant.
        # Merge consecutive same-role messages when needed.
        merged: List[Dict[str, Any]] = []
        for msg in anthropic_messages:
            if merged and merged[-1]["role"] == msg["role"]:
                prev_content = merged[-1]["content"]
                cur_content = msg["content"]

                # Normalise both to list-of-blocks for merging
                if isinstance(prev_content, str):
                    prev_content = [{"type": "text", "text": prev_content}] if prev_content else []
                if isinstance(cur_content, str):
                    cur_content = [{"type": "text", "text": cur_content}] if cur_content else []

                merged[-1]["content"] = prev_content + cur_content
            else:
                merged.append(msg)

        anthropic_messages = merged

        create_kwargs: Dict[str, Any] = {
            "model": self.model,
            "messages": anthropic_messages,
            "temperature": temperature if temperature is not None else self.temperature,
            "max_tokens": self.max_tokens,
        }
        if system_text:
            create_kwargs["system"] = system_text.strip()
        if tools:
            create_kwargs["tools"] = self._convert_tools_openai_to_anthropic(tools)

        try:
            response = self.client.messages.create(**create_kwargs)
            wrapped = self._wrap_response(response)

            if wrapped.tool_calls:
                return wrapped

            return (wrapped.content or "").strip()
        except Exception as e:
            logger.error(f"Anthropic History error: {e}")
            raise Exception(f"Anthropic Error: {str(e)}")

    def structured_output(
        self,
        messages: List[Dict[str, Any]],
        schema: dict,
        system_prompt: Optional[str] = None,
        **kwargs,
    ) -> dict:
        """Generate structured JSON output by injecting schema into system prompt."""
        schema_instruction = f"\n\nYou MUST return ONLY valid JSON matching this schema (no markdown, no explanation):\n{json.dumps(schema)}"
        augmented_system = (system_prompt or "") + schema_instruction

        response_text = self.chat_with_history(
            messages=messages, system_prompt=augmented_system, **kwargs
        )
        try:
            clean = response_text.replace("```json", "").replace("```", "").strip()
            return json.loads(clean)
        except Exception as e:
            logger.error(f"Failed to parse Anthropic structured output: {e}\nResponse: {response_text}")
            raise Exception("Failed to generate valid structured output")

    def transcribe_audio(self, file_path: str, **kwargs) -> str:
        raise NotImplementedError("Anthropic does not provide audio transcription. Use OpenAI Whisper instead.")


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
                model=getattr(settings, "GEMINI_MODEL", "gemini-2.5-pro"),
                temperature=settings.LLM_TEMPERATURE,
                base_url="https://generativelanguage.googleapis.com/v1beta/openai/"
            )
        elif provider == "anthropic" and getattr(settings, "ANTHROPIC_API_KEY", None):
             _llm_service = AnthropicLLMService(
                api_key=settings.ANTHROPIC_API_KEY,
                model=getattr(settings, "ANTHROPIC_MODEL", "claude-sonnet-4-6"),
                temperature=settings.LLM_TEMPERATURE,
                max_tokens=settings.LLM_MAX_TOKENS,
            )
        elif provider == "groq" and getattr(settings, "GROQ_API_KEY", None):
             _llm_service = OpenAILLMService(
                api_key=settings.GROQ_API_KEY,
                model=getattr(settings, "GROQ_MODEL", "llama-3.3-70b-versatile"),
                temperature=settings.LLM_TEMPERATURE,
                base_url="https://api.groq.com/openai/v1"
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
