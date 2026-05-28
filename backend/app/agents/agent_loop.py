"""
AgentLoop — tight async while loop replacing LangGraph agent state machine.
"""
from __future__ import annotations

import asyncio
import inspect
import json
from dataclasses import dataclass, field
from typing import Any, AsyncGenerator, Callable, Dict, List, Optional

from loguru import logger

from app.services.stream_events import emit as stream_emit


@dataclass
class AgentResponse:
    content: str
    agent_id: str
    citations: List[Dict] = field(default_factory=list)
    tool_calls_made: List[str] = field(default_factory=list)


class AgentLoop:
    _history: Dict[str, List[Dict]] = {}

    def __init__(
        self,
        agent_id: str,
        system_prompt: str,
        tools: List[Dict],
        tool_map: Dict[str, Callable],
        llm: Any,
        twg_id: Optional[str] = None,
        max_iterations: int = 10,
        max_history: int = 20,
    ):
        self.agent_id = agent_id
        self.system_prompt = system_prompt
        self.tools = tools
        self.tool_map = tool_map
        self.llm = llm
        self.twg_id = twg_id
        self.max_iterations = max_iterations
        self.max_history = max_history

    async def run(
        self,
        query: str,
        thread_id: str,
        user_timezone: Optional[str] = None,
        stream_callback: Optional[Callable] = None,
    ) -> AgentResponse:
        history = self._get_history(thread_id)
        history.append({"role": "user", "content": query})

        tool_calls_made: List[str] = []
        final_content = ""
        citations: List[Dict] = []

        for iteration in range(self.max_iterations):
            window = history[-self.max_history:]
            # Gemini requires the window to start at a user message (never a
            # tool result). If the trimmed window has no user message (can
            # happen when max_history < tool-call depth), search backwards
            # through the full history for the last real user message.
            for i, msg in enumerate(window):
                if msg["role"] == "user":
                    window = window[i:]
                    break
            else:
                for i in range(len(history) - 1, -1, -1):
                    if history[i]["role"] == "user":
                        window = history[i:]
                        break
                else:
                    window = history[-1:]

            try:
                if stream_callback:
                    result = await self.llm.stream_tokens(
                        messages=window,
                        system_prompt=self.system_prompt,
                        on_token=stream_callback,
                        tools=self.tools if self.tools else None,
                    )
                else:
                    result = await self.llm.complete(
                        messages=window,
                        tools=self.tools if self.tools else None,
                        system_prompt=self.system_prompt,
                    )
            except Exception as e:
                logger.error(f"[{self.agent_id}] LLM error on iteration {iteration}: {e}")
                final_content = f"I encountered an error: {str(e)}"
                break

            content = result.get("content", "") if isinstance(result, dict) else str(result)
            tool_calls = result.get("tool_calls") if isinstance(result, dict) else None

            assistant_msg: Dict[str, Any] = {"role": "assistant", "content": content}
            if tool_calls:
                assistant_msg["tool_calls"] = tool_calls
            history.append(assistant_msg)

            if not tool_calls:
                final_content = content
                break

            tool_results = await self._execute_tools(tool_calls, thread_id, user_timezone)
            for name, tc_id, result_str in tool_results:
                tool_calls_made.append(name)
                history.append({
                    "role": "tool",
                    "tool_call_id": tc_id,
                    "content": result_str,
                })

            # Short-circuit: if any tool emitted a confirmation_required envelope,
            # register the action in the pending-actions store (so /agents/execute
            # can resolve it on Confirm) and return that JSON directly so the
            # frontend renders the inline Confirm/Cancel card instead of letting
            # the LLM paraphrase the payload.
            _confirm_payload = None
            for _, _, result_str in tool_results:
                if '"status": "confirmation_required"' in result_str or '"status":"confirmation_required"' in result_str:
                    _confirm_payload = result_str
                    break
            if _confirm_payload is not None:
                try:
                    import json as _json
                    from app.tools._rbac import store_pending_action, get_user_for_thread
                    parsed = _json.loads(_confirm_payload)
                    _ctx = get_user_for_thread(thread_id)
                    _uid_for_store = _ctx[0] if _ctx else ""
                    store_pending_action(
                        action_id=parsed["action_id"],
                        user_id=_uid_for_store,
                        action_type=parsed["action_type"],
                        payload=parsed.get("payload", {}),
                    )
                    logger.info(f"[{self.agent_id}] stored pending action {parsed['action_id']} user={_uid_for_store} type={parsed['action_type']}")
                except Exception as _e:
                    logger.error(f"[{self.agent_id}] failed to register pending action: {_e}")
                final_content = _confirm_payload
                break

        else:
            final_content = final_content or "I reached my iteration limit. Please try a more specific question."

        self._save_history(thread_id, history)
        return AgentResponse(
            content=final_content,
            agent_id=self.agent_id,
            citations=citations,
            tool_calls_made=tool_calls_made,
        )

    async def stream(
        self,
        query: str,
        thread_id: str,
        user_timezone: Optional[str] = None,
    ) -> AsyncGenerator[Dict, None]:
        tokens: asyncio.Queue = asyncio.Queue()

        async def on_token(t: str):
            await tokens.put({"type": "token", "content": t})

        async def run_task():
            resp = await self.run(query, thread_id, user_timezone, stream_callback=on_token)
            await tokens.put({"type": "done", "response": resp})

        task = asyncio.create_task(run_task())
        while True:
            event = await tokens.get()
            yield event
            if event["type"] == "done":
                break
        await task

    def _get_history(self, thread_id: str) -> List[Dict]:
        if thread_id not in AgentLoop._history:
            AgentLoop._history[thread_id] = []
        return AgentLoop._history[thread_id]

    def _save_history(self, thread_id: str, history: List[Dict]) -> None:
        AgentLoop._history[thread_id] = history

    def clear_history(self, thread_id: str) -> None:
        AgentLoop._history.pop(thread_id, None)

    async def _execute_tools(
        self,
        tool_calls: List[Dict],
        thread_id: str,
        user_timezone: Optional[str],
    ) -> List[tuple]:
        async def execute_one(tc: Dict) -> tuple:
            name = tc["name"]
            args = dict(tc.get("args") or {})
            tc_id = tc["id"]

            if thread_id:
                await stream_emit(thread_id, {
                    "type": "tool_call",
                    "name": name,
                    "args": {k: (v[:80] + "…" if isinstance(v, str) and len(v) > 80 else v) for k, v in args.items()},
                })

            try:
                func = self.tool_map.get(name)
                if func is None:
                    try:
                        from app.tools.tool_registry import get_tool_registry
                        registry = get_tool_registry()
                        result_str = await registry.execute_tool(
                            tool_name=name,
                            tool_args=args,
                            agent_id=self.agent_id,
                            twg_id=self.twg_id,
                            user_timezone=user_timezone,
                        )
                    except Exception as reg_err:
                        result_str = json.dumps({"error": f"Tool '{name}' not found: {reg_err}"})
                else:
                    sig = inspect.signature(func)
                    if "twg_id" in sig.parameters and self.twg_id and "twg_id" not in args:
                        args["twg_id"] = self.twg_id
                    if "user_timezone" in sig.parameters and user_timezone and "user_timezone" not in args:
                        args["user_timezone"] = user_timezone
                    # Auto-inject user context (set by /chat endpoints) so role-
                    # gated write tools see who's calling. We resolve via the
                    # thread-id keyed fallback so it survives supervisor → TWG
                    # agent delegation hops where ContextVars get dropped.
                    if "user_id" in sig.parameters or "user_role" in sig.parameters:
                        from app.tools._rbac import get_user_for_thread
                        _ctx = get_user_for_thread(thread_id)
                        if _ctx is not None:
                            _uid, _urole = _ctx
                            if "user_id" in sig.parameters and "user_id" not in args:
                                args["user_id"] = _uid
                            if "user_role" in sig.parameters and "user_role" not in args:
                                args["user_role"] = _urole
                    if asyncio.iscoroutinefunction(func):
                        raw = await func(**args)
                    else:
                        raw = await asyncio.to_thread(func, **args)
                    result_str = json.dumps(raw, default=str) if isinstance(raw, (dict, list)) else str(raw)
            except Exception as e:
                logger.error(f"[{self.agent_id}] Tool '{name}' failed: {e}")
                result_str = json.dumps({"error": f"Tool '{name}' failed: {str(e)}"})

            # Cap tool results to avoid context overflow with Gemini
            if len(result_str) > 3000:
                result_str = result_str[:3000] + "…[truncated]"

            return name, tc_id, result_str

        return await asyncio.gather(*[execute_one(tc) for tc in tool_calls])
