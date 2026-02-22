"""
Tests for the Tiered Memory System (MemoryManager).

Verifies:
1. Short-term sliding window extraction
2. Long-term semantic summary retrieval (mocked Pinecone)
3. Background summarization and archiving logic (mocked LLM + Pinecone)
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from langchain_core.messages import HumanMessage, AIMessage

from app.services.memory_manager import MemoryManager

@pytest.fixture
def mock_kb():
    kb = MagicMock()
    # Mock search to return empty by default
    kb.search.return_value = []
    return kb

@pytest.fixture
def mock_llm():
    llm = MagicMock()
    # Create an async mock for chat_with_history since to_thread is used
    # Wait, the method itself is sync, but we use asyncio.to_thread around it
    llm.chat_with_history.return_value = "Mocked summary of the conversation."
    return llm

@pytest.fixture
def memory_manager(mock_kb, mock_llm):
    # Patch the getters to return our mocks
    with patch("app.services.memory_manager.get_knowledge_base", return_value=mock_kb), \
         patch("app.services.memory_manager.get_llm_service", return_value=mock_llm):
        mm = MemoryManager()
        return mm

class TestTieredMemory:

    def test_get_context_sliding_window_exact(self, memory_manager):
        """Should return exactly max_history messages if the list is larger."""
        messages = [HumanMessage(content=f"Msg {i}") for i in range(20)]
        
        recent, summary = memory_manager.get_context(
            session_id="session-123",
            agent_id="energy",
            messages=messages,
            current_query="Msg 19",
            max_history=5
        )
        
        assert len(recent) == 5
        assert recent[0].content == "Msg 15"
        assert recent[-1].content == "Msg 19"
        assert summary == "" # No mocked results

    def test_get_context_sliding_window_under_limit(self, memory_manager):
        """Should return all messages if under max_history limit."""
        messages = [HumanMessage(content=f"Msg {i}") for i in range(3)]
        
        recent, summary = memory_manager.get_context(
            session_id="session-123",
            agent_id="energy",
            messages=messages,
            current_query="Msg 2",
            max_history=5
        )
        
        assert len(recent) == 3

    def test_get_context_retrieves_summaries(self, memory_manager, mock_kb):
        """Should query Pinecone and format the long-term summary block."""
        messages = [HumanMessage(content="Current question")]
        
        # Mock Pinecone returning 2 past summaries
        mock_kb.search.return_value = [
            {"id": "doc1", "score": 0.9, "metadata": {"text": "Discussed energy policies."}},
            {"id": "doc2", "score": 0.85, "metadata": {"text": "Decided on grid expansion."}}
        ]
        
        recent, summary = memory_manager.get_context(
            session_id="session-123",
            agent_id="energy",
            messages=messages,
            current_query="Current question",
            max_history=5
        )
        
        assert "PAST CONVERSATION RECALL" in summary
        assert "- Discussed energy policies." in summary
        assert "- Decided on grid expansion." in summary
        
        # Verify metadata filter was correct
        mock_kb.search.assert_called_once()
        call_kwargs = mock_kb.search.call_args[1]
        assert call_kwargs["namespace"] == "twg-energy"
        assert call_kwargs["filter"]["session_id"] == "session-123"

    @pytest.mark.asyncio
    async def test_summarize_and_archive(self, memory_manager, mock_llm, mock_kb):
        """Should format messages, call LLM to summarize, and upsert to Pinecone."""
        messages = [
            HumanMessage(content="Hello"),
            AIMessage(content="Hi there!"),
            HumanMessage(content="Let's build a grid.")
        ]
        
        success = await memory_manager.summarize_and_archive(
            session_id="session-456",
            agent_id="supervisor",
            messages_to_summarize=messages
        )
        
        assert success is True
        
        # Verify LLM was called with the formatted chat
        mock_llm.chat_with_history.assert_called_once()
        llm_messages = mock_llm.chat_with_history.call_args[1]["messages"]
        prompt_content = llm_messages[0]["content"]
        assert "User: Hello" in prompt_content
        assert "Assistant: Hi there!" in prompt_content
        assert "User: Let's build a grid." in prompt_content
        
        # Verify it was added to Pinecone
        mock_kb.add_document.assert_called_once()
        kb_kwargs = mock_kb.add_document.call_args[1]
        assert kb_kwargs["content"] == "Mocked summary of the conversation."
        assert kb_kwargs["namespace"] == "system"
        assert kb_kwargs["metadata"]["session_id"] == "session-456"
        assert kb_kwargs["metadata"]["type"] == "conversation_summary"
