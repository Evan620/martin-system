"""
Semantic Router

Uses efficient embedding-based semantic routing to match user queries
to the appropriate Technical Working Group (TWG) Agent without relying
on slow and expensive LLM parsing for every routing decision.
"""

from typing import List, Dict, Any, Optional, Tuple
from loguru import logger
import numpy as np

from app.core.knowledge_base import get_knowledge_base

class SemanticRouter:
    """
    Embedding-based router for determining which TWG Agent should handle a query.
    """
    
    def __init__(self):
        try:
            self.kb = get_knowledge_base()
        except Exception as e:
            logger.warning(f"[SemanticRouter] Knowledge Base unavailable: {e}")
            self.kb = None
            
        # Hardcoded embedding profiles for cold-start semantic matching
        # In a fully dynamic system, these would be generated dynamically from Tools
        self.agent_profiles = {
            "energy": [
                "energy policy, power grid expansion, renewable energy, electricity access, solar power, wind",
                "petroleum resources, electrification, WAPP (West African Power Pool)",
                "infrastructure projects for power generation"
            ],
            "agriculture": [
                "food security, agriculture policy, farming, crop yield optimization",
                "irrigation, fertilizer distribution, livestock management, agribusiness",
                "food systems and rural development"
            ],
            "minerals": [
                "critical minerals, mining operations, industrialization, resource extraction",
                "cobalt, lithium, gold, bauxite, value chain development",
                "geological surveys and ore processing"
            ],
            "digital": [
                "digital transformation, technology policy, broadband infrastructure, internet access",
                "fintech, e-commerce, e-government, software development",
                "cybersecurity, artificial intelligence, online platforms"
            ],
            "resource_mobilization": [
                "finance, funding, investment, resource mobilization, capital allocation",
                "deal pipeline, investor matching, financial instruments",
                "budget approvals, grants, economic development funds"
            ]
        }
        
        # Cache of centroid embeddings for each agent
        self._agent_centroids: Dict[str, np.ndarray] = {}

    def _cosine_similarity(self, a: np.ndarray, b: np.ndarray) -> float:
        """Calculate cosine similarity between two vectors."""
        norm_a = np.linalg.norm(a)
        norm_b = np.linalg.norm(b)
        if norm_a == 0 or norm_b == 0:
            return 0.0
        return float(np.dot(a, b) / (norm_a * norm_b))

    def _ensure_centroids(self):
        """Lazy load and compute embeddings for each agent profile."""
        if not self.kb:
            return
            
        if self._agent_centroids:
            return
            
        try:
            logger.info("[SemanticRouter] Computing embedding centroids for TWG agents...")
            for agent_id, phrases in self.agent_profiles.items():
                embeddings = self.kb.generate_embeddings(phrases)
                
                # Average the embeddings to create a single 'centroid' profile per agent
                if embeddings:
                    # kb.generate_embeddings returns List[List[float]]
                    np_embeddings = np.array(embeddings)
                    centroid = np.mean(np_embeddings, axis=0)
                    self._agent_centroids[agent_id] = centroid
        except Exception as e:
            logger.error(f"[SemanticRouter] Failed to compute centroids: {e}")

    def get_routing_scores(self, query: str) -> Dict[str, float]:
        """
        Embed the query and return similarity scores for all agents.
        """
        if not self.kb:
            logger.warning("[SemanticRouter] Semantic routing unavailable, KB not loaded.")
            return {}
            
        self._ensure_centroids()
        
        try:
            query_embedding = self.kb.generate_embeddings([query])[0]
            query_vec = np.array(query_embedding)
            
            scores = {}
            for agent_id, centroid in self._agent_centroids.items():
                score = self._cosine_similarity(query_vec, centroid)
                scores[agent_id] = score
                
            return scores
        except Exception as e:
            logger.error(f"[SemanticRouter] Scoring failed: {e}")
            return {}

    def route(
        self,
        query: str,
        confidence_threshold: float = 0.45,
        multi_agent_threshold: float = 0.65
    ) -> Tuple[List[str], str]:
        """
        Determine relevant agents based on semantic similarity.

        Args:
            query: The user query
            confidence_threshold: Minimum cosine similarity to select an agent at all
            multi_agent_threshold: If multiple agents score above this, consult them all

        Returns:
            Tuple: (List of relevant agent IDs, Delegation Type 'single'|'multiple'|'supervisor_only')
        """
        # 1. Look for explicit routing overrides FIRST (fast-path)
        query_lower = query.lower().strip()
        if "[routing strictly to supervisor]" in query_lower:
            return [], "supervisor_only"

        # 2. Short-circuit for greetings, meta-questions, and low-information queries
        #    These have no domain relevance and should go straight to supervisor
        meta_phrases = [
            "what are your capabilities", "what can you do", "who are you",
            "how can you help", "what do you do", "tell me about yourself",
            "what are you", "how do you work", "what tools do you have",
            "what is martin", "help me", "capabilities",
        ]
        if any(phrase in query_lower for phrase in meta_phrases):
            logger.info(f"[SemanticRouter] Meta/about-me query -> supervisor_only")
            return [], "supervisor_only"

        if len(query_lower.split()) <= 3:
            greeting_words = {"hello", "hi", "hey", "hola", "good morning", "good afternoon",
                              "good evening", "thanks", "thank you", "bye", "goodbye",
                              "help", "who are you", "what can you do"}
            if query_lower in greeting_words or any(query_lower.startswith(g) for g in greeting_words):
                logger.info(f"[SemanticRouter] Short greeting/generic query -> supervisor_only")
                return [], "supervisor_only"

        # 3. Compute semantic similarity
        scores = self.get_routing_scores(query)

        if not scores:
            # Fallback to supervisor if scoring failed
            return [], "supervisor_only"

        logger.info(f"[SemanticRouter] Raw routing scores: {[(k, round(v, 3)) for k, v in scores.items()]}")

        # 4. Filter by threshold
        relevant_agents = []

        # Find the absolute best match
        best_agent = max(scores.items(), key=lambda x: x[1])

        # Check score spread — if all agents score similarly, query is generic → supervisor
        all_scores = list(scores.values())
        score_spread = max(all_scores) - min(all_scores)
        if score_spread < 0.05 and best_agent[1] < 0.60:
            logger.info(f"[SemanticRouter] Low spread ({score_spread:.3f}) + low peak ({best_agent[1]:.3f}) -> supervisor_only")
            return [], "supervisor_only"

        if best_agent[1] >= confidence_threshold:
            relevant_agents.append(best_agent[0])

            # Check for multiple strong matches (but cap at 2 to avoid slow fan-out)
            for agent_id, score in scores.items():
                if agent_id != best_agent[0] and score >= multi_agent_threshold:
                    relevant_agents.append(agent_id)
                    if len(relevant_agents) >= 3:
                        break

        # 5. Final Delegation Type determination
        if not relevant_agents:
            delegation_type = "supervisor_only"
        elif len(relevant_agents) == 1:
            delegation_type = "single"
        else:
            delegation_type = "multiple"

        return relevant_agents, delegation_type

# Singleton instance
_semantic_router_instance = None

def get_semantic_router() -> SemanticRouter:
    """Get the singleton instance of the Semantic Router."""
    global _semantic_router_instance
    if _semantic_router_instance is None:
        _semantic_router_instance = SemanticRouter()
    return _semantic_router_instance
