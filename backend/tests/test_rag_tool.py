import pytest
from unittest.mock import AsyncMock, MagicMock, patch


@pytest.mark.asyncio
async def test_search_documents_returns_formatted_results():
    from app.tools.rag_tool import search_documents
    mock_kb = MagicMock()
    mock_kb.search = MagicMock(return_value=[
        {"score": 0.9, "metadata": {"file_name": "report.pdf", "text": "West Africa farming data"}},
    ])
    with patch("app.tools.rag_tool.get_knowledge_base", return_value=mock_kb):
        result = await search_documents(query="farming", twg_id="uuid-123")
    assert "report.pdf" in result
    assert "West Africa" in result


@pytest.mark.asyncio
async def test_search_documents_no_results():
    from app.tools.rag_tool import search_documents
    mock_kb = MagicMock()
    mock_kb.search = MagicMock(return_value=[])
    with patch("app.tools.rag_tool.get_knowledge_base", return_value=mock_kb):
        result = await search_documents(query="xyz", twg_id="uuid-123")
    assert "No relevant documents" in result


@pytest.mark.asyncio
async def test_search_documents_truncates_long_text():
    from app.tools.rag_tool import search_documents
    long_text = "x" * 5000
    mock_kb = MagicMock()
    mock_kb.search = MagicMock(return_value=[
        {"score": 0.8, "metadata": {"file_name": "big.pdf", "text": long_text}},
    ])
    with patch("app.tools.rag_tool.get_knowledge_base", return_value=mock_kb):
        result = await search_documents(query="test", twg_id="uuid-abc")
    assert len(result) < 5000
