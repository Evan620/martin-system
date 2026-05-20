"""
Native Gemini generateContent adapter.

Calls Google's generateContent API directly instead of the OpenAI-compat endpoint.
This preserves thoughtSignature on functionCall parts, which is required for
Gemini 2.5+/3.5+ thinking models to accept tool results without 400 errors.
"""
from __future__ import annotations

import json
import uuid
from typing import Any, Callable, Dict, List, Optional, Awaitable

import httpx
from loguru import logger

from app.core.config import settings


_BASE_URL = "https://generativelanguage.googleapis.com/v1beta"


class GeminiNativeService:
    def __init__(self, api_key: str, model: str):
        self.api_key = api_key
        self.model = model

    async def complete(
        self,
        messages: List[Dict[str, Any]],
        tools: Optional[List[Dict]] = None,
        system_prompt: Optional[str] = None,
    ) -> Dict[str, Any]:
        contents, sys_inst = self._build_contents(messages)
        if system_prompt and sys_inst is None:
            sys_inst = {"parts": [{"text": system_prompt}]}

        payload: Dict[str, Any] = {
            "contents": contents,
            "generationConfig": {"maxOutputTokens": settings.LLM_MAX_TOKENS},
        }
        if sys_inst:
            payload["systemInstruction"] = sys_inst
        if tools:
            payload["tools"] = self._build_tools(tools)

        raw = await self._post(payload)
        return self._parse_response(raw)

    async def stream_tokens(
        self,
        messages: List[Dict[str, Any]],
        system_prompt: Optional[str] = None,
        on_token: Optional[Callable] = None,
        tools: Optional[List[Dict]] = None,
        **kwargs,
    ) -> Dict[str, Any]:
        contents, sys_inst = self._build_contents(messages)
        if system_prompt and sys_inst is None:
            sys_inst = {"parts": [{"text": system_prompt}]}

        payload: Dict[str, Any] = {
            "contents": contents,
            "generationConfig": {"maxOutputTokens": settings.LLM_MAX_TOKENS},
        }
        if sys_inst:
            payload["systemInstruction"] = sys_inst
        if tools:
            payload["tools"] = self._build_tools(tools)

        url = f"{_BASE_URL}/models/{self.model}:streamGenerateContent"
        full_text = ""
        tool_calls: List[Dict] = []

        async with httpx.AsyncClient(timeout=120) as client:
            async with client.stream(
                "POST",
                url,
                params={"key": self.api_key, "alt": "sse"},
                json=payload,
                headers={"Content-Type": "application/json"},
            ) as resp:
                resp.raise_for_status()
                async for line in resp.aiter_lines():
                    if not line.startswith("data:"):
                        continue
                    chunk_raw = line[5:].strip()
                    if not chunk_raw or chunk_raw == "[DONE]":
                        continue
                    try:
                        chunk = json.loads(chunk_raw)
                    except json.JSONDecodeError:
                        continue
                    parsed = self._parse_response(chunk)
                    if parsed["content"]:
                        full_text += parsed["content"]
                        if on_token:
                            import asyncio
                            if asyncio.iscoroutinefunction(on_token):
                                await on_token(parsed["content"])
                            else:
                                on_token(parsed["content"])
                    if parsed["tool_calls"]:
                        tool_calls.extend(parsed["tool_calls"])

        return {"content": full_text, "tool_calls": tool_calls or None}

    def _build_contents(
        self, messages: List[Dict[str, Any]]
    ) -> tuple:
        contents: List[Dict] = []
        system_parts: List[str] = []

        tc_name_by_id: Dict[str, str] = {}
        for m in messages:
            for tc in m.get("tool_calls") or []:
                tc_name_by_id[tc["id"]] = tc["name"]

        for msg in messages:
            role = msg.get("role", "user")
            content = msg.get("content") or ""
            tool_calls = msg.get("tool_calls") or []

            if role == "system":
                system_parts.append(content)
                continue

            if role == "assistant":
                parts: List[Dict] = []
                if content:
                    parts.append({"text": content})
                for tc in tool_calls:
                    fc_part: Dict[str, Any] = {
                        "functionCall": {
                            "name": tc["name"],
                            "args": tc.get("args") or {},
                        }
                    }
                    if tc.get("_thought_sig"):
                        fc_part["thoughtSignature"] = tc["_thought_sig"]
                    parts.append(fc_part)
                if parts:
                    contents.append({"role": "model", "parts": parts})
                continue

            if role == "tool":
                tool_call_id = msg.get("tool_call_id", "")
                fn_name = tc_name_by_id.get(tool_call_id, tool_call_id)
                contents.append({
                    "role": "user",
                    "parts": [{
                        "functionResponse": {
                            "name": fn_name,
                            "response": {"result": content},
                        }
                    }]
                })
                continue

            parts_list: List[Dict] = []
            if content:
                parts_list.append({"text": content})
            if parts_list:
                contents.append({"role": "user", "parts": parts_list})

        sys_inst = {"parts": [{"text": "\n".join(system_parts)}]} if system_parts else None
        return contents, sys_inst

    def _build_tools(self, tools: List[Dict]) -> List[Dict]:
        declarations = []
        for t in tools:
            fn = t.get("function") or t
            params = fn.get("parameters", {})
            params = {k: v for k, v in params.items() if k not in ("default",)}
            declarations.append({
                "name": fn["name"],
                "description": fn.get("description", ""),
                "parameters": params,
            })
        return [{"functionDeclarations": declarations}]

    def _parse_response(self, raw: Dict) -> Dict[str, Any]:
        candidates = raw.get("candidates") or []
        if not candidates:
            error = raw.get("error", {})
            msg = error.get("message", str(raw))
            raise RuntimeError(f"Gemini API error: {msg}")

        parts = candidates[0].get("content", {}).get("parts") or []
        text_parts: List[str] = []
        tool_calls: List[Dict] = []

        for part in parts:
            if "text" in part:
                text_parts.append(part["text"])
            elif "functionCall" in part:
                fc = part["functionCall"]
                tool_calls.append({
                    "id": str(uuid.uuid4()),
                    "name": fc.get("name", ""),
                    "args": fc.get("args") or {},
                    "_thought_sig": part.get("thoughtSignature"),
                })

        return {
            "content": "".join(text_parts),
            "tool_calls": tool_calls if tool_calls else None,
        }

    async def _post(self, payload: Dict) -> Dict:
        url = f"{_BASE_URL}/models/{self.model}:generateContent"
        async with httpx.AsyncClient(timeout=120) as client:
            resp = await client.post(
                url,
                params={"key": self.api_key},
                json=payload,
                headers={"Content-Type": "application/json"},
            )
            if resp.status_code == 429:
                raise RuntimeError(f"Gemini rate limit (429): {resp.text[:200]}")
            resp.raise_for_status()
            return resp.json()
