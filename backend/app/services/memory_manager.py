"""
Tiered Memory System for Agents.

Provides sliding window context and long-term semantic summarization
to replace hard history truncation. Summaries of old interactions
are stored and retrieved via Pinecone vector database.
"""

import logging
from typing import List, Tuple, Dict, Any, Optional
from datetime import datetime
import asyncio

from langchain_core.messages import BaseMessage, HumanMessage, AIMessage
from app.core.knowledge_base import get_knowledge_base
from app.services.llm_service import get_llm_service

logger = logging.getLogger(__name__)

class MemoryManager:
    """
    Tiered memory: 
    1. Short-term: Exact N recent messages (sliding window)
    2. Long-term: Semantic summaries of older messages stored in Pinecone
    """
    
    def __init__(self):
        self.kb = None
        self.llm = None
        try:
            self.kb = get_knowledge_base()
            self.llm = get_llm_service()
        except Exception as e:
            logger.warning(f"Failed to initialize memory dependencies: {e}")

    def get_context(
        self, 
        session_id: str, 
        agent_id: str, 
        messages: List[BaseMessage], 
        current_query: str,
        max_history: int = 15
    ) -> Tuple[List[BaseMessage], str]:
        """
        Get sliding window history and retrieved long-term semantic context.
        
        Args:
            session_id: unique thread/session id
            agent_id: agent identifier for scoping
            messages: the full list of messages from state
            current_query: the current user query to rank summaries
            max_history: size of short-term window (default 15)
            
        Returns:
            Tuple of (short_term_messages, long_term_summary_string)
        """
        # 1. Short-term sliding window
        short_term_messages = messages[-max_history:] if len(messages) > max_history else messages
        
        # 2. Long-term semantic retrieval
        long_term_summary = ""
        if self.kb and current_query:
            try:
                namespace = f"twg-{agent_id}" if agent_id != "supervisor" else "system"
                
                # Fetch only summaries for this exact session
                metadata_filter = {
                    "session_id": session_id,
                    "type": "conversation_summary",
                    "agent_id": agent_id
                }
                
                results = self.kb.search(
                    query=current_query,
                    namespace=namespace,
                    top_k=3,
                    filter=metadata_filter,
                    include_metadata=True
                )
                
                if results:
                    summaries = []
                    for res in results:
                        # Extract the text chunks if they were stored in text field (depends on implementation, fallback to metadata)
                        text = res.get('metadata', {}).get('text', '')
                        if text:
                            summaries.append(f"- {text}")
                            
                    if summaries:
                        long_term_summary = "PAST CONVERSATION RECALL:\n" + "\n".join(summaries)
                        logger.info(f"[{agent_id}] Retrieved {len(summaries)} past summaries for session {session_id}")
            except Exception as e:
                logger.error(f"Failed to retrieve long-term context: {e}")
                
        return short_term_messages, long_term_summary

    async def summarize_and_archive(
        self, 
        session_id: str, 
        agent_id: str, 
        messages_to_summarize: List[BaseMessage]
    ) -> bool:
        """
        Summarize a fallen-out chunk of messages and store in Pinecone.
        
        Args:
            session_id: unique thread/session id
            agent_id: agent identifier for scoping
            messages_to_summarize: messages that fell out of the sliding window
            
        Returns:
            True if successful, False otherwise.
        """
        if not self.kb or not self.llm or not messages_to_summarize:
            return False
            
        try:
            # 1. Format messages for summarization
            formatted_chat = []
            for m in messages_to_summarize:
                role = "User" if isinstance(m, HumanMessage) else "Assistant" if isinstance(m, AIMessage) else "System/Tool"
                content = str(m.content)
                if len(content) > 500:
                    content = content[:500] + "... [truncated]"
                formatted_chat.append(f"{role}: {content}")
                
            chat_text = "\n".join(formatted_chat)
            
            # 2. Generate summary using LLM
            prompt = (
                "Summarize the following conversation segment concisely. "
                "Focus on the main topics discussed, user goals, decisions made, "
                "and important facts shared. The summary will be used by an AI "
                "to recall past context. \n\n"
                f"Conversation:\n{chat_text}\n\nSummary:"
            )
            
            response = await asyncio.to_thread(
                self.llm.chat_with_history,
                messages=[{"role": "user", "content": prompt}],
                system_prompt="You are an expert at distilling conversations into dense factual summaries.",
                tools=[]
            )
            
            summary_text = str(response) if isinstance(response, str) else str(response.content)
            
            # 3. Store in Pinecone
            namespace = f"twg-{agent_id}" if agent_id != "supervisor" else "system"
            metadata = {
                "session_id": session_id,
                "agent_id": agent_id,
                "type": "conversation_summary",
                "timestamp": datetime.utcnow().isoformat(),
                "text": summary_text # Stored in metadata for easy retrieval
            }
            
            # kb.add_document upserts standard chunk with metadata
            await asyncio.to_thread(
                self.kb.add_document,
                content=summary_text,
                metadata=metadata,
                namespace=namespace
            )
            
            logger.info(f"[{agent_id}] Successfully archived summary of {len(messages_to_summarize)} messages for session {session_id}")
            return True
            
        except Exception as e:
            logger.error(f"[{agent_id}] Failed to summarize and archive messages: {e}")
            return False

# Singleton
_memory_manager_instance = None

def get_memory_manager() -> MemoryManager:
    global _memory_manager_instance
    if _memory_manager_instance is None:
        _memory_manager_instance = MemoryManager()
    return _memory_manager_instance
