"""
Tests for FAISS store functionality.
"""
import pytest
import os
import tempfile
import json
from unittest.mock import patch, MagicMock
from backend.tools.rag.faiss_store import RagStoreFaiss, IndexNotFoundError


class TestRagStoreFaiss:
    """Test cases for RagStoreFaiss class."""
    
    def test_index_not_found_error(self):
        """Test IndexNotFoundError when index files are missing."""
        with tempfile.TemporaryDirectory() as temp_dir:
            index_path = os.path.join(temp_dir, "nonexistent_index.faiss")
            meta_path = os.path.join(temp_dir, "nonexistent_meta.jsonl")
            
            store = RagStoreFaiss(index_path, meta_path)
            
            with pytest.raises(IndexNotFoundError) as exc_info:
                store.load()
            
            assert "FAISS index file not found" in str(exc_info.value)
            assert "Please drop index.faiss and meta.jsonl" in str(exc_info.value)
    
    def test_metadata_not_found_error(self):
        """Test IndexNotFoundError when metadata file is missing."""
        with tempfile.TemporaryDirectory() as temp_dir:
            index_path = os.path.join(temp_dir, "index.faiss")
            meta_path = os.path.join(temp_dir, "nonexistent_meta.jsonl")
            
            # Create a dummy index file
            with open(index_path, 'w') as f:
                f.write("dummy")
            
            store = RagStoreFaiss(index_path, meta_path)
            
            with pytest.raises(IndexNotFoundError) as exc_info:
                store.load()
            
            assert "FAISS metadata file not found" in str(exc_info.value)
    
    @patch('backend.rag.faiss_store.faiss')
    def test_successful_load(self, mock_faiss):
        """Test successful loading of FAISS index and metadata."""
        with tempfile.TemporaryDirectory() as temp_dir:
            index_path = os.path.join(temp_dir, "index.faiss")
            meta_path = os.path.join(temp_dir, "meta.jsonl")
            
            # Create dummy index file
            with open(index_path, 'w') as f:
                f.write("dummy")
            
            # Create metadata file
            metadata = [
                {"doc_id": 0, "text": "Test document 1", "page": 1, "document": "doc1.pdf"},
                {"doc_id": 1, "text": "Test document 2", "page": 2, "document": "doc2.pdf"}
            ]
            
            with open(meta_path, 'w', encoding='utf-8') as f:
                for item in metadata:
                    f.write(json.dumps(item, ensure_ascii=False) + '\n')
            
            # Mock FAISS index
            mock_index = MagicMock()
            mock_index.ntotal = 2
            mock_faiss.read_index.return_value = mock_index
            
            store = RagStoreFaiss(index_path, meta_path)
            store.load()
            
            assert store.index == mock_index
            assert len(store.metadata) == 2
            assert store.metadata[0]["text"] == "Test document 1"
    
    @patch('backend.rag.faiss_store.faiss')
    def test_search_without_load(self, mock_faiss):
        """Test search method loads index if not already loaded."""
        with tempfile.TemporaryDirectory() as temp_dir:
            index_path = os.path.join(temp_dir, "index.faiss")
            meta_path = os.path.join(temp_dir, "meta.jsonl")
            
            # Create dummy files
            with open(index_path, 'w') as f:
                f.write("dummy")
            
            metadata = [{"doc_id": 0, "text": "Test document", "page": 1, "document": "test.pdf"}]
            with open(meta_path, 'w', encoding='utf-8') as f:
                for item in metadata:
                    f.write(json.dumps(item, ensure_ascii=False) + '\n')
            
            # Mock FAISS index and search
            mock_index = MagicMock()
            mock_index.ntotal = 1
            mock_index.search.return_value = ([[0.9]], [[0]])
            mock_faiss.read_index.return_value = mock_index
            
            store = RagStoreFaiss(index_path, meta_path)
            
            # Mock embedding model
            with patch.object(store, '_encode_query', return_value=[[0.1, 0.2, 0.3]]):
                results = store.search("test query", k=1)
            
            assert len(results) == 1
            assert results[0]["text"] == "Test document"
            assert results[0]["score"] == 0.9
    
    def test_get_stats(self):
        """Test get_stats method."""
        store = RagStoreFaiss("dummy_path", "dummy_meta")
        
        # Test when not loaded
        stats = store.get_stats()
        assert stats["loaded"] is False
        
        # Test when loaded
        store.index = MagicMock()
        store.index.ntotal = 10
        store.index.d = 384
        store.metadata = [{"doc_id": i} for i in range(10)]
        store.embedding_model = "sentence-transformers"
        
        stats = store.get_stats()
        assert stats["loaded"] is True
        assert stats["vector_count"] == 10
        assert stats["dimension"] == 384
        assert stats["metadata_count"] == 10
        assert stats["embedding_model"] == "sentence-transformers"
    
    @patch('backend.rag.faiss_store.openai')
    def test_openai_embedding(self, mock_openai):
        """Test OpenAI embedding when configured."""
        with patch('backend.config.get_settings') as mock_settings:
            mock_settings.return_value.use_openai_embeddings = True
            mock_settings.return_value.openai_api_key = "test-key"
            
            mock_openai.Embedding.create.return_value = {
                'data': [{'embedding': [0.1, 0.2, 0.3]}]
            }
            
            store = RagStoreFaiss("dummy_path", "dummy_meta")
            store.embedding_model = "openai"
            
            result = store._encode_query("test query")
            
            assert result.tolist() == [0.1, 0.2, 0.3]
            mock_openai.Embedding.create.assert_called_once()
    
    def test_sentence_transformers_embedding(self):
        """Test sentence-transformers embedding."""
        with patch('backend.rag.faiss_store.SentenceTransformer') as mock_st:
            mock_model = MagicMock()
            mock_model.encode.return_value = [0.1, 0.2, 0.3]
            mock_st.return_value = mock_model
            
            store = RagStoreFaiss("dummy_path", "dummy_meta")
            
            result = store._encode_query("test query")
            
            assert result.tolist() == [0.1, 0.2, 0.3]
            mock_model.encode.assert_called_once_with("test query")
