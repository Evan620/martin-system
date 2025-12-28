"""
Knowledge Tools for AI Agents

This module provides tools for AI agents to interact with the knowledge base,
including semantic search, context retrieval, and document discovery.
"""

from typing import List, Dict, Any, Optional
import logging
from backend.app.core.knowledge_base import get_knowledge_base

logger = logging.getLogger(__name__)


def search_knowledge_base(
    query: str,
    twg: Optional[str] = None,
    top_k: int = 5,
    min_score: float = 0.7
) -> List[Dict[str, Any]]:
    """
    Search the knowledge base for relevant information.
    
    Args:
        query: Search query
        twg: Optional TWG filter (e.g., 'energy', 'agriculture')
        top_k: Number of results to return
        min_score: Minimum similarity score threshold
        
    Returns:
        List of relevant documents with scores
    """
    try:
        kb = get_knowledge_base()
        
        # Build namespace if TWG specified
        namespace = f"twg-{twg}" if twg else None
        
        # Build metadata filter
        filter_dict = {}
        if twg:
            filter_dict['twg'] = twg
        
        # Search
        results = kb.search(
            query=query,
            namespace=namespace,
            top_k=top_k,
            filter=filter_dict if filter_dict else None
        )
        
        # Filter by minimum score
        filtered_results = [
            r for r in results 
            if r['score'] >= min_score
        ]
        
        logger.info(f"Knowledge search for '{query}': {len(filtered_results)} results")
        return filtered_results
        
    except Exception as e:
        logger.error(f"Error searching knowledge base: {e}")
        return []


def get_relevant_context(
    query: str,
    twg: Optional[str] = None,
    max_tokens: int = 2000
) -> str:
    """
    Get relevant context for an agent query.
    
    This function retrieves and formats context from the knowledge base
    to be used in agent prompts.
    
    Args:
        query: Agent query
        twg: Optional TWG filter
        max_tokens: Maximum tokens for context
        
    Returns:
        Formatted context string
    """
    try:
        # Search knowledge base
        results = search_knowledge_base(query, twg=twg, top_k=5)
        
        if not results:
            return "No relevant context found in knowledge base."
        
        # Format context
        context_parts = []
        total_length = 0
        
        for i, result in enumerate(results, 1):
            metadata = result.get('metadata', {})
            text = metadata.get('text', '')
            source = metadata.get('filename', 'Unknown')
            score = result.get('score', 0)
            
            # Estimate token count (rough: 1 token ≈ 4 chars)
            text_tokens = len(text) // 4
            
            if total_length + text_tokens > max_tokens:
                break
            
            context_part = f"""
[Source {i}: {source} (Relevance: {score:.2f})]
{text}
"""
            context_parts.append(context_part)
            total_length += text_tokens
        
        context = "\n---\n".join(context_parts)
        
        logger.info(f"Retrieved context: {len(context_parts)} sources, ~{total_length} tokens")
        return context
        
    except Exception as e:
        logger.error(f"Error getting relevant context: {e}")
        return f"Error retrieving context: {str(e)}"


def find_similar_documents(
    document_id: str,
    twg: Optional[str] = None,
    top_k: int = 5
) -> List[Dict[str, Any]]:
    """
    Find documents similar to a given document.
    
    Args:
        document_id: ID of the reference document
        twg: Optional TWG filter
        top_k: Number of similar documents to return
        
    Returns:
        List of similar documents
    """
    try:
        kb = get_knowledge_base()
        
        # First, fetch the document to get its embedding
        # (This would require storing document embeddings or re-embedding)
        # For now, we'll use a placeholder
        
        logger.info(f"Finding documents similar to: {document_id}")
        
        # This is a simplified version - in production, you'd:
        # 1. Retrieve the document's embedding
        # 2. Use it to query for similar vectors
        # 3. Return the results
        
        return []
        
    except Exception as e:
        logger.error(f"Error finding similar documents: {e}")
        return []


def filter_by_twg(twg: str, top_k: int = 10) -> List[Dict[str, Any]]:
    """
    Get recent documents for a specific TWG.
    
    Args:
        twg: TWG identifier (e.g., 'energy')
        top_k: Number of documents to return
        
    Returns:
        List of TWG documents
    """
    try:
        kb = get_knowledge_base()
        namespace = f"twg-{twg}"
        
        # Get namespace stats
        stats = kb.get_namespace_stats(namespace)
        
        logger.info(f"TWG {twg} has {stats.get('vector_count', 0)} documents")
        
        # For now, return stats
        # In production, you'd implement pagination or date-based filtering
        return [stats]
        
    except Exception as e:
        logger.error(f"Error filtering by TWG: {e}")
        return []


def get_knowledge_base_stats() -> Dict[str, Any]:
    """
    Get overall knowledge base statistics.
    
    Returns:
        Dict with statistics
    """
    try:
        kb = get_knowledge_base()
        health = kb.health_check()
        namespaces = kb.list_namespaces()
        
        stats = {
            "status": health.get("status"),
            "total_vectors": health.get("total_vectors", 0),
            "namespaces": namespaces,
            "namespace_count": len(namespaces)
        }
        
        logger.info(f"Knowledge base stats: {stats}")
        return stats
        
    except Exception as e:
        logger.error(f"Error getting knowledge base stats: {e}")
        return {"status": "error", "error": str(e)}


# Tool definitions for LangChain integration
KNOWLEDGE_TOOLS = [
    {
        "name": "search_knowledge_base",
        "description": "Search the knowledge base for relevant information about ECOWAS Summit topics, policies, and documents.",
        "parameters": {
            "query": "The search query",
            "twg": "Optional TWG filter (energy, agriculture, minerals, digital, protocol, resource_mobilization)",
            "top_k": "Number of results (default: 5)"
        },
        "function": search_knowledge_base
    },
    {
        "name": "get_relevant_context",
        "description": "Get relevant context from the knowledge base to answer a question or complete a task.",
        "parameters": {
            "query": "The question or task",
            "twg": "Optional TWG filter",
            "max_tokens": "Maximum context length (default: 2000)"
        },
        "function": get_relevant_context
    },
    {
        "name": "get_knowledge_base_stats",
        "description": "Get statistics about the knowledge base, including total documents and TWG coverage.",
        "parameters": {},
        "function": get_knowledge_base_stats
    }
]
