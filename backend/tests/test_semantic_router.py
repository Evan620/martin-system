import pytest
import numpy as np
from unittest.mock import patch, MagicMock

from app.services.semantic_router import SemanticRouter, get_semantic_router

@pytest.fixture
def mock_kb():
    with patch('app.services.semantic_router.get_knowledge_base') as mock_get_kb:
        mock_kb_instance = MagicMock()
        mock_get_kb.return_value = mock_kb_instance
        yield mock_kb_instance

def test_singleton_pattern(mock_kb):
    r1 = get_semantic_router()
    r2 = get_semantic_router()
    assert r1 is r2

def test_cosine_similarity(mock_kb):
    router = SemanticRouter()
    
    vec1 = np.array([1.0, 0.0, 0.0])
    vec2 = np.array([1.0, 0.0, 0.0])
    assert router._cosine_similarity(vec1, vec2) == 1.0
    
    vec3 = np.array([0.0, 1.0, 0.0])
    assert router._cosine_similarity(vec1, vec3) == 0.0
    
def test_semantic_routing_logic(mock_kb):
    # Mock the embedding generation
    # Assume: 
    # - Energy keywords generate vector A
    # - Agriculture keywords generate vector B
    # - Query "solar panels" generates vector A' (close to A)
    
    vec_energy = np.array([0.9, 0.1, 0.0])
    vec_agri = np.array([0.0, 0.9, 0.1])
    
    mock_kb.generate_embeddings.side_effect = [
        [vec_energy.tolist()], # Profile 1
        [vec_agri.tolist()],   # Profile 2
        [[0.0, 0.0, 0.0]],     # Profile 3
        [[0.0, 0.0, 0.0]],     # Profile 4
        [[0.0, 0.0, 0.0]],     # Profile 5
        
        # The actual query
        [[0.85, 0.15, 0.0]]    # "solar panels" query
    ]
    
    router = SemanticRouter()
    
    agents, status = router.route("I want to build solar panels")
    
    assert "energy" in agents
    assert status == "single"

def test_routing_fallback_on_failure():
    # Test fallback when KB is unavailable
    with patch('app.services.semantic_router.get_knowledge_base', side_effect=Exception("No DB")):
        router = SemanticRouter()
        
        agents, status = router.route("solar panels")
        
        assert agents == []
        assert status == "supervisor_only"
