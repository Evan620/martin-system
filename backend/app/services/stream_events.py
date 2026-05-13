"""
Real-time streaming event bridge for SSE endpoints.

Allows agent internals (tool calls, routing) to push events into a per-thread
asyncio queue that the SSE generator drains live.
"""

import asyncio
from typing import Dict, Optional

_queues: Dict[str, asyncio.Queue] = {}


def register_queue(thread_id: str, queue: asyncio.Queue) -> None:
    _queues[thread_id] = queue


def unregister_queue(thread_id: str) -> None:
    _queues.pop(thread_id, None)


async def emit(thread_id: str, event: dict) -> None:
    q = _queues.get(thread_id)
    if q is not None:
        await q.put(event)
