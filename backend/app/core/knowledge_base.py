"""
Pinecone Vector Database Integration

This module provides the core integration with Pinecone for knowledge base management,
including document ingestion, vector storage, and semantic search for RAG.
"""

from typing import List, Dict, Any, Optional, Tuple
import os
from datetime import datetime
import logging
from pinecone import Pinecone, ServerlessSpec
from tenacity import retry, stop_after_attempt, wait_exponential

logger = logging.getLogger(__name__)


class PineconeKnowledgeBase:
    """
    Manages Pinecone vector database operations for the knowledge base.
    
    Features:
    - Index initialization and health checks
    - Document embedding and indexing
    - Semantic search with metadata filtering
    - Batch operations for efficiency
    - TWG namespace isolation
    """
    
    def __init__(
        self,
        api_key: str,
        environment: str,
        index_name: str,
        embedding_model: str = "text-embedding-3-small",
        dimension: int = 1536,
        namespace_prefix: str = "twg"
    ):
        """
        Initialize Pinecone knowledge base.
        
        Args:
            api_key: Pinecone API key
            environment: Pinecone environment (e.g., 'us-east-1')
            index_name: Name of the Pinecone index
            embedding_model: OpenAI embedding model name
            dimension: Embedding dimension (1536 for text-embedding-3-small)
            namespace_prefix: Prefix for TWG namespaces
        """
        self.api_key = api_key
        self.environment = environment
        self.index_name = index_name
        self.embedding_model = embedding_model
        self.dimension = dimension
        self.namespace_prefix = namespace_prefix
        
        # Initialize Pinecone client
        self.pc = Pinecone(api_key=api_key)
        
        # Get or create index
        self.index = self._get_or_create_index()
        
        logger.info(f"Initialized PineconeKnowledgeBase with index: {index_name}")
    
    def _get_or_create_index(self):
        """Get existing index or create new one."""
        try:
            # Check if index exists
            existing_indexes = self.pc.list_indexes()
            index_names = [idx.name for idx in existing_indexes]
            
            if self.index_name not in index_names:
                logger.info(f"Creating new Pinecone index: {self.index_name}")
                
                # Create serverless index
                self.pc.create_index(
                    name=self.index_name,
                    dimension=self.dimension,
                    metric="cosine",
                    spec=ServerlessSpec(
                        cloud="aws",
                        region=self.environment
                    )
                )
                logger.info(f"Index {self.index_name} created successfully")
            
            # Connect to index
            return self.pc.Index(self.index_name)
            
        except Exception as e:
            logger.error(f"Error getting/creating index: {e}")
            raise
    
    def health_check(self) -> Dict[str, Any]:
        """
        Check Pinecone connection and index health.
        
        Returns:
            Dict with health status information
        """
        try:
            stats = self.index.describe_index_stats()
            return {
                "status": "healthy",
                "index_name": self.index_name,
                "total_vectors": stats.total_vector_count,
                "dimension": stats.dimension,
                "namespaces": stats.namespaces
            }
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return {
                "status": "unhealthy",
                "error": str(e)
            }
    
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=10))
    def generate_embeddings(self, texts: List[str]) -> List[List[float]]:
        """
        Generate embeddings for a list of texts using Ollama (nomic-embed-text).
        
        Args:
            texts: List of text strings to embed
            
        Returns:
            List of embedding vectors
        """
        try:
            import requests
            embeddings = []
            
            for text in texts:
                # Ensure text is not too long for Ollama (nomic-embed-text limit is ~2048 tokens)
                # Truncate to a safe length (~8000 chars) if needed
                safe_text = text[:8000]
                
                response = requests.post(
                    'http://localhost:11434/api/embeddings',
                    json={
                        'model': self.embedding_model,
                        'prompt': safe_text
                    }
                )
                
                if response.status_code == 200:
                    embedding = response.json()['embedding']
                    embeddings.append(embedding)
                else:
                    error_msg = response.json().get('error', response.text)
                    logger.error(f"Ollama error for model {self.embedding_model}: {error_msg}")
                    raise Exception(f"Ollama embedding failed: {error_msg}")
            
            logger.debug(f"Generated {len(embeddings)} embeddings using {self.embedding_model}")
            return embeddings
            
        except Exception as e:
            logger.error(f"Error generating embeddings: {e}")
            raise
    
    def upsert_documents(
        self,
        documents: List[Dict[str, Any]],
        namespace: Optional[str] = None,
        batch_size: int = 100
    ) -> Dict[str, int]:
        """
        Upsert documents into Pinecone index.
        
        Args:
            documents: List of dicts with 'id', 'text', and 'metadata'
            namespace: Optional namespace (e.g., 'twg-energy')
            batch_size: Number of vectors to upsert per batch
            
        Returns:
            Dict with upsert statistics
        """
        try:
            total_upserted = 0
            
            # Process in batches
            for i in range(0, len(documents), batch_size):
                batch = documents[i:i + batch_size]
                
                # Extract texts and generate embeddings
                texts = [doc['text'] for doc in batch]
                embeddings = self.generate_embeddings(texts)
                
                # Prepare vectors for upsert
                vectors = []
                for doc, embedding in zip(batch, embeddings):
                    vector = {
                        'id': doc['id'],
                        'values': embedding,
                        'metadata': doc.get('metadata', {})
                    }
                    vectors.append(vector)
                
                # Upsert to Pinecone
                self.index.upsert(vectors=vectors, namespace=namespace)
                total_upserted += len(vectors)
                
                logger.info(f"Upserted batch {i//batch_size + 1}: {len(vectors)} vectors")
            
            return {
                "total_upserted": total_upserted,
                "namespace": namespace,
                "batches": (len(documents) + batch_size - 1) // batch_size
            }
            
        except Exception as e:
            logger.error(f"Error upserting documents: {e}")
            raise
    
    def search(
        self,
        query: str,
        namespace: Optional[str] = None,
        top_k: int = 5,
        filter: Optional[Dict[str, Any]] = None,
        include_metadata: bool = True
    ) -> List[Dict[str, Any]]:
        """
        Semantic search in the knowledge base.
        
        Args:
            query: Search query text
            namespace: Optional namespace to search in
            top_k: Number of results to return
            filter: Metadata filter (e.g., {'twg': 'energy'})
            include_metadata: Whether to include metadata in results
            
        Returns:
            List of search results with scores and metadata
        """
        try:
            # Generate query embedding
            query_embedding = self.generate_embeddings([query])[0]
            
            # Search Pinecone
            results = self.index.query(
                vector=query_embedding,
                top_k=top_k,
                namespace=namespace,
                filter=filter,
                include_metadata=include_metadata
            )
            
            # Format results
            formatted_results = []
            for match in results.matches:
                result = {
                    'id': match.id,
                    'score': match.score,
                    'metadata': match.metadata if include_metadata else {}
                }
                formatted_results.append(result)
            
            logger.info(f"Search returned {len(formatted_results)} results")
            return formatted_results
            
        except Exception as e:
            logger.error(f"Error searching: {e}")
            raise
    
    def delete_documents(
        self,
        ids: List[str],
        namespace: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Delete documents from Pinecone index.
        
        Args:
            ids: List of document IDs to delete
            namespace: Optional namespace
            
        Returns:
            Dict with deletion status
        """
        try:
            self.index.delete(ids=ids, namespace=namespace)
            logger.info(f"Deleted {len(ids)} documents from namespace: {namespace}")
            
            return {
                "deleted_count": len(ids),
                "namespace": namespace,
                "status": "success"
            }
            
        except Exception as e:
            logger.error(f"Error deleting documents: {e}")
            raise
    
    def get_namespace_stats(self, namespace: str) -> Dict[str, Any]:
        """
        Get statistics for a specific namespace.
        
        Args:
            namespace: Namespace name
            
        Returns:
            Dict with namespace statistics
        """
        try:
            stats = self.index.describe_index_stats()
            namespace_stats = stats.namespaces.get(namespace, {})
            
            return {
                "namespace": namespace,
                "vector_count": namespace_stats.get('vector_count', 0)
            }
            
        except Exception as e:
            logger.error(f"Error getting namespace stats: {e}")
            return {"namespace": namespace, "vector_count": 0, "error": str(e)}
    
    def list_namespaces(self) -> List[str]:
        """
        List all namespaces in the index.
        
        Returns:
            List of namespace names
        """
        try:
            stats = self.index.describe_index_stats()
            return list(stats.namespaces.keys())
        except Exception as e:
            logger.error(f"Error listing namespaces: {e}")
            return []


# Singleton instance
_knowledge_base_instance: Optional[PineconeKnowledgeBase] = None


from backend.app.core.config import settings

def get_knowledge_base() -> PineconeKnowledgeBase:
    """
    Get singleton instance of PineconeKnowledgeBase.
    
    Returns:
        PineconeKnowledgeBase instance
    """
    global _knowledge_base_instance
    
    if _knowledge_base_instance is None:
        # Initialize from settings
        api_key = settings.PINECONE_API_KEY
        environment = settings.PINECONE_ENVIRONMENT
        index_name = settings.PINECONE_INDEX_NAME
        embedding_model = settings.EMBEDDING_MODEL
        dimension = settings.EMBEDDING_DIMENSION
        
        if not api_key:
            raise ValueError("PINECONE_API_KEY environment variable not set")
        
        _knowledge_base_instance = PineconeKnowledgeBase(
            api_key=api_key,
            environment=environment,
            index_name=index_name,
            embedding_model=embedding_model,
            dimension=dimension
        )
    
    return _knowledge_base_instance
