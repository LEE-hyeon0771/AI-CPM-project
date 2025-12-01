"""
FAISS-based RAG store for reading pre-built indexes.
Read-only implementation - no embedding generation.
"""
import os
import json
import faiss
import numpy as np
from typing import List, Dict, Any, Optional
from sentence_transformers import SentenceTransformer
import openai
from ...config import get_settings


class IndexNotFoundError(Exception):
    """Custom exception for missing FAISS index files."""
    pass


class RagStoreFaiss:
    """FAISS-based RAG store for reading pre-built indexes."""
    
    def __init__(self, index_path: str, meta_path: str):
        self.index_path = index_path
        self.meta_path = meta_path
        self.settings = get_settings()
        self.index = None
        self.metadata = []
        self.embedding_model = None
        self._load_embedding_model()
    
    def _load_embedding_model(self):
        """Load embedding model for query encoding."""
        if self.settings.use_openai_embeddings and self.settings.openai_api_key:
            openai.api_key = self.settings.openai_api_key
            self.embedding_model = "openai"
        else:
            # Use sentence-transformers as fallback
            self.embedding_model = SentenceTransformer('all-MiniLM-L6-v2')
    
    def load(self) -> None:
        """Load FAISS index and metadata."""
        try:
            # Check if files exist
            if not os.path.exists(self.index_path):
                raise IndexNotFoundError(
                    f"FAISS index file not found: {self.index_path}\n"
                    "Please drop index.faiss and meta.jsonl into ./data/faiss "
                    "(another developer produces embeddings)."
                )
            
            if not os.path.exists(self.meta_path):
                raise IndexNotFoundError(
                    f"FAISS metadata file not found: {self.meta_path}\n"
                    "Please drop index.faiss and meta.jsonl into ./data/faiss "
                    "(another developer produces embeddings)."
                )
            
            # Load FAISS index
            self.index = faiss.read_index(self.index_path)
            
            # Load metadata
            with open(self.meta_path, 'r', encoding='utf-8') as f:
                self.metadata = [json.loads(line.strip()) for line in f if line.strip()]
            
            print(f"Loaded FAISS index with {self.index.ntotal} vectors and {len(self.metadata)} metadata entries")
            
        except Exception as e:
            if isinstance(e, IndexNotFoundError):
                raise
            raise IndexNotFoundError(f"Failed to load FAISS index: {str(e)}")
    
    def _encode_query(self, query: str) -> np.ndarray:
        """Encode query text to vector."""
        if self.embedding_model == "openai":
            # Use OpenAI embeddings
            response = openai.Embedding.create(
                input=query,
                model="text-embedding-ada-002"
            )
            return np.array(response['data'][0]['embedding'], dtype=np.float32)
        else:
            # Use sentence-transformers
            embedding = self.embedding_model.encode(query)
            return embedding.astype(np.float32)
    
    def search(self, query: str, k: int = 5) -> List[Dict[str, Any]]:
        """
        Search for similar documents.
        
        Args:
            query: Search query text
            k: Number of results to return
            
        Returns:
            List of search results with metadata
        """
        if self.index is None:
            self.load()
        
        # Encode query
        query_vector = self._encode_query(query)
        query_vector = query_vector.reshape(1, -1)
        
        # Search
        scores, indices = self.index.search(query_vector, k)
        
        # Format results
        results = []
        for i, (score, idx) in enumerate(zip(scores[0], indices[0])):
            if idx < len(self.metadata):
                result = self.metadata[idx].copy()
                result['score'] = float(score)
                result['rank'] = i + 1
                results.append(result)
        
        return results
    
    def search_by_work_type(self, work_type: str, k: int = 5) -> List[Dict[str, Any]]:
        """Search for documents related to specific work type."""
        query = f"{work_type} 작업 안전 기준 규정"
        return self.search(query, k)
    
    def get_stats(self) -> Dict[str, Any]:
        """Get store statistics."""
        if self.index is None:
            return {"loaded": False}
        
        return {
            "loaded": True,
            "vector_count": self.index.ntotal,
            "dimension": self.index.d,
            "metadata_count": len(self.metadata),
            "embedding_model": "openai" if self.embedding_model == "openai" else "sentence-transformers"
        }
