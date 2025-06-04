import pytest
from unittest.mock import Mock, AsyncMock
from app.services.rag_service import RAGService
from app.models.schemas import DocumentChunk

class TestRAGService:
    def setup_method(self):
        """Setup para cada test"""
        self.rag_service = RAGService()
        
        # Mock del document processor
        self.rag_service.document_processor = Mock()
        self.rag_service.document_processor.search_similar_chunks.return_value = [
            ("Contenido de prueba", 1, 0.8),
            ("Otro contenido", 2, 0.7)
        ]
        
        # Mock del claude client
        self.rag_service.claude_client = Mock()
        self.rag_service.claude_client.generate_response = AsyncMock(
            return_value="Respuesta de prueba"
        )
    
    @pytest.mark.asyncio
    async def test_answer_question(self):
        """Test respuesta a pregunta"""
        response = await self.rag_service.answer_question("¿Qué es Python?")
        
        assert response.question == "¿Qué es Python?"
        assert response.answer == "Respuesta de prueba"
        assert len(response.context_chunks) == 2
        assert isinstance(response.context_chunks[0], DocumentChunk)
    
    @pytest.mark.asyncio
    async def test_answer_question_no_chunks(self):
        """Test cuando no hay chunks relevantes"""
        self.rag_service.document_processor.search_similar_chunks.return_value = []
        
        with pytest.raises(Exception) as exc_info:
            await self.rag_service.answer_question("Pregunta sin contexto")
        
        assert "No se encontraron chunks relevantes" in str(exc_info.value)
    
    def test_is_ready(self):
        """Test verificación de estado"""
        # Mock sistema listo
        self.rag_service.document_processor.index = Mock()
        self.rag_service.document_processor.chunks = ["chunk1", "chunk2"]
        
        assert self.rag_service.is_ready() == True
        
        # Mock sistema no listo
        self.rag_service.document_processor.index = None
        assert self.rag_service.is_ready() == False