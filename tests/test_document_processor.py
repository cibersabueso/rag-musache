import pytest
import os
import tempfile
from app.services.document_processor import DocumentProcessor

class TestDocumentProcessor:
    def setup_method(self):
        """Setup para cada test"""
        self.processor = DocumentProcessor()
    
    def test_split_text_into_chunks(self):
        """Test división de texto en chunks"""
        text = "A" * 2500  # Texto largo
        chunks = self.processor._split_text_into_chunks(text)
        
        assert len(chunks) > 1
        assert all(len(chunk) <= self.processor.chunk_size for chunk in chunks)
    
    def test_create_embeddings(self):
        """Test creación de embeddings"""
        text_chunks = [("Texto de prueba 1", 1), ("Texto de prueba 2", 2)]
        self.processor.create_embeddings(text_chunks)
        
        assert self.processor.embeddings is not None
        assert self.processor.index is not None
        assert len(self.processor.chunks) == 2
    
    def test_search_similar_chunks(self):
        """Test búsqueda de chunks similares"""
        text_chunks = [
            ("Python es un lenguaje de programación", 1),
            ("Machine learning es una rama de la IA", 2),
            ("FastAPI es un framework web", 3)
        ]
        
        self.processor.create_embeddings(text_chunks)
        results = self.processor.search_similar_chunks("programación Python", top_k=2)
        
        assert len(results) <= 2
        assert all(len(result) == 3 for result in results)  # (texto, pagina, score)
        assert all(isinstance(result[2], float) for result in results)  # score es float