import pytest
from fastapi.testclient import TestClient
from unittest.mock import Mock, AsyncMock, patch
from app.main import app
from app.models.schemas import RAGResponse, DocumentChunk
from datetime import datetime

client = TestClient(app)

class TestAPI:
    
    @patch('app.api.endpoints.rag_service')
    def test_health_check(self, mock_rag_service):
        """Test health check endpoint"""
        response = client.get("/api/v1/health")
        assert response.status_code == 200
        assert response.json()["status"] == "healthy"
    
    @patch('app.api.endpoints.rag_service')
    def test_system_status_ready(self, mock_rag_service):
        """Test status endpoint cuando sistema está listo"""
        mock_rag_service.is_ready.return_value = True
        mock_rag_service.document_processor.chunks = ["chunk1", "chunk2"]
        
        response = client.get("/api/v1/status")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ready"
        assert data["total_chunks"] == 2
    
    @patch('app.api.endpoints.rag_service')
    def test_system_status_not_ready(self, mock_rag_service):
        """Test status endpoint cuando sistema no está listo"""
        mock_rag_service.is_ready.return_value = False
        
        response = client.get("/api/v1/status")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "not_ready"
        assert data["total_chunks"] == 0
    
    @patch('app.api.endpoints.rag_service')
    def test_ask_question_success(self, mock_rag_service):
        """Test endpoint de pregunta exitoso"""
        # Mock respuesta
        mock_response = RAGResponse(
            question="¿Qué es Python?",
            answer="Python es un lenguaje de programación",
            context_chunks=[
                DocumentChunk(content="Python info", page=1, similarity_score=0.9)
            ],
            response_time="0.5s",
            timestamp=datetime.utcnow()
        )
        
        mock_rag_service.is_ready.return_value = True
        mock_rag_service.answer_question = AsyncMock(return_value=mock_response)
        
        response = client.post(
            "/api/v1/ask",
            json={"question": "¿Qué es Python?"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["question"] == "¿Qué es Python?"
        assert data["answer"] == "Python es un lenguaje de programación"
    
    @patch('app.api.endpoints.rag_service')
    def test_ask_question_system_not_ready(self, mock_rag_service):
        """Test endpoint cuando sistema no está listo"""
        mock_rag_service.is_ready.return_value = False
        
        response = client.post(
            "/api/v1/ask",
            json={"question": "¿Qué es Python?"}
        )
        
        assert response.status_code == 503
        assert "no listo" in response.json()["detail"]
    
    def test_upload_document_invalid_file(self):
        """Test upload con archivo inválido"""
        response = client.post(
            "/api/v1/upload-document",
            files={"file": ("test.txt", b"contenido", "text/plain")}
        )
        
        assert response.status_code == 400
        assert "Solo se aceptan archivos PDF" in response.json()["detail"]