"""
On-demand RAG tool — replaces the mandatory _process_query_node Pinecone search.
Registered in ToolRegistry; twg_id is injected automatically by the registry.
"""
from __future__ import annotations

import asyncio
from typing import Optional

from loguru import logger

from app.core.knowledge_base import get_knowledge_base


async def search_documents(query: str, twg_id: Optional[str] = None) -> str:
    """
    Search the TWG knowledge base for documents relevant to the query.
    Call this when you need factual context from uploaded documents, reports,
    or meeting notes. Do NOT call for simple conversational replies.

    Args:
        query: Search terms describing what information you need
        twg_id: TWG identifier (injected automatically — do not pass manually)

    Returns:
        Formatted excerpts with source file names, or "No relevant documents found."
    """
    kb = get_knowledge_base()
    if kb is None:
        return "Knowledge base unavailable."

    try:
        if twg_id:
            twg_ns = f"twg-{twg_id}"
            twg_results, global_results = await asyncio.gather(
                asyncio.to_thread(kb.search, query=query, namespace=twg_ns, top_k=3),
                asyncio.to_thread(kb.search, query=query, namespace="twg-general", top_k=2),
            )
            results = twg_results + global_results
        else:
            results = await asyncio.to_thread(
                kb.search, query=query, namespace="twg-general", top_k=5
            )
    except Exception as e:
        logger.error(f"[rag_tool] Pinecone search failed: {e}")
        return f"Document search failed: {str(e)}"

    results.sort(key=lambda x: x["score"], reverse=True)
    results = results[:3]

    if not results:
        return "No relevant documents found."

    parts = []
    for r in results:
        name = r["metadata"].get("file_name", "Unknown")
        text = (r["metadata"].get("text") or "")[:2000]
        parts.append(f"[{name}]\n{text}")
    return "\n\n".join(parts)
