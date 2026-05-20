import pytest
import asyncio
from unittest.mock import AsyncMock, patch, MagicMock
import json

def test_build_contents_user_message():
    from app.services.gemini_native import GeminiNativeService
    svc = GeminiNativeService(api_key="test", model="gemini-3.5-flash")
    msgs = [{"role": "user", "content": "Hello"}]
    contents, sys_inst = svc._build_contents(msgs)
    assert len(contents) == 1
    assert contents[0]["role"] == "user"
    assert contents[0]["parts"][0]["text"] == "Hello"
    assert sys_inst is None

def test_build_contents_system_prompt():
    from app.services.gemini_native import GeminiNativeService
    svc = GeminiNativeService(api_key="test", model="gemini-3.5-flash")
    msgs = [{"role": "system", "content": "You are helpful"}]
    contents, sys_inst = svc._build_contents(msgs)
    assert contents == []
    assert sys_inst == {"parts": [{"text": "You are helpful"}]}

def test_thought_signature_roundtrip():
    from app.services.gemini_native import GeminiNativeService
    svc = GeminiNativeService(api_key="test", model="gemini-3.5-flash")
    msgs = [
        {"role": "user", "content": "search something"},
        {
            "role": "assistant",
            "content": "",
            "tool_calls": [{
                "id": "tc1",
                "name": "search_documents",
                "args": {"query": "foo"},
                "_thought_sig": "sig-abc123",
            }],
        },
        {
            "role": "tool",
            "tool_call_id": "tc1",
            "content": "result here",
        },
    ]
    contents, _ = svc._build_contents(msgs)
    model_turn = next(c for c in contents if c["role"] == "model")
    fc_part = next(p for p in model_turn["parts"] if "functionCall" in p)
    assert fc_part.get("thoughtSignature") == "sig-abc123"

def test_build_tools():
    from app.services.gemini_native import GeminiNativeService
    svc = GeminiNativeService(api_key="test", model="gemini-3.5-flash")
    tools = [{
        "type": "function",
        "function": {
            "name": "search_documents",
            "description": "Search docs",
            "parameters": {
                "type": "object",
                "properties": {"query": {"type": "string"}},
                "required": ["query"],
            }
        }
    }]
    gemini_tools = svc._build_tools(tools)
    assert len(gemini_tools) == 1
    fd = gemini_tools[0]["functionDeclarations"][0]
    assert fd["name"] == "search_documents"
    assert "parameters" in fd

def test_parse_response_with_function_call():
    from app.services.gemini_native import GeminiNativeService
    svc = GeminiNativeService(api_key="test", model="gemini-3.5-flash")
    raw = {
        "candidates": [{
            "content": {
                "role": "model",
                "parts": [
                    {"thoughtSignature": "sig-xyz", "functionCall": {
                        "name": "search_documents",
                        "args": {"query": "agriculture"}
                    }}
                ]
            }
        }]
    }
    result = svc._parse_response(raw)
    assert result["content"] == ""
    assert len(result["tool_calls"]) == 1
    tc = result["tool_calls"][0]
    assert tc["name"] == "search_documents"
    assert tc["_thought_sig"] == "sig-xyz"
