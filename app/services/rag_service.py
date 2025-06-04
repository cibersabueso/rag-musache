import os
import time
from typing import List, Dict, Any
from .document_processor import DocumentProcessor
from .claude_client import ClaudeClient
from ..models.schemas import DocumentChunk, RAGResponse
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

class RAGService:
    def __init__(self):
        self.document_processor = DocumentProcessor()
        self.claude_client = ClaudeClient()
        self.top_k = int(os.getenv("TOP_K_RESULTS", 3))
        
        # Cargar vector store si existe
        if not self.document_processor.load_vector_store():
            print("No se encontró vector store existente. Necesita procesar documentos primero.")
    
    async def answer_question(self, question: str) -> RAGResponse:
        """Responde una pregunta usando RAG"""
        start_time = time.time()
        
        try:
            # Buscar chunks relevantes
            similar_chunks = self.document_processor.search_similar_chunks(
                question, top_k=self.top_k
            )
            
            if not similar_chunks:
                raise ValueError("No se encontraron chunks relevantes para la pregunta")
            
            # Preparar contexto
            context = "\n\n".join([
                f"[Página {page}] {chunk}" 
                for chunk, page, score in similar_chunks
            ])
            
            # Generar respuesta con Claude
            answer = await self.claude_client.generate_response(context, question)
            
            # Preparar chunks para respuesta
            context_chunks = [
                DocumentChunk(
                    content=chunk,
                    page=page,
                    similarity_score=score
                )
                for chunk, page, score in similar_chunks
            ]
            
            response_time = f"{time.time() - start_time:.2f}s"
            
            return RAGResponse(
                question=question,
                answer=answer,
                context_chunks=context_chunks,
                response_time=response_time,
                timestamp=datetime.utcnow()
            )
            
        except Exception as e:
            raise Exception(f"Error en RAG Service: {str(e)}")
    
    def process_new_document(self, file_path: str):
        """Procesa un nuevo documento"""
        return self.document_processor.process_document(file_path)
    
    def is_ready(self) -> bool:
        """Verifica si el servicio está listo para responder preguntas"""
        return (self.document_processor.embeddings is not None and 
                len(self.document_processor.chunks) > 0)