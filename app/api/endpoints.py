from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, BackgroundTasks
from sqlalchemy.orm import Session
from typing import List
import os
import shutil
from ..models.database import get_db, QueryLog
from ..models.schemas import QuestionRequest, RAGResponse, QueryLogResponse
from ..services.rag_service import RAGService
import time

router = APIRouter()
rag_service = RAGService()

@router.post("/ask", response_model=RAGResponse)
async def ask_question(
    request: QuestionRequest,
    db: Session = Depends(get_db)
):
    """Endpoint principal para hacer preguntas al sistema RAG"""
    try:
        if not rag_service.is_ready():
            raise HTTPException(
                status_code=503, 
                detail="Sistema no listo. Necesita procesar documentos primero."
            )
        
        start_time = time.time()
        
        # Generar respuesta
        response = await rag_service.answer_question(request.question)
        
        # Guardar en base de datos
        query_log = QueryLog(
            question=request.question,
            answer=response.answer,
            context_used=str([chunk.content[:100] + "..." for chunk in response.context_chunks]),
            response_time=response.response_time
        )
        db.add(query_log)
        db.commit()
        
        return response
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/upload-document")
async def upload_document(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...)
):
    """Endpoint para subir y procesar documentos PDF"""
    try:
        # Validar tipo de archivo
        if not file.filename.endswith('.pdf'):
            raise HTTPException(
                status_code=400, 
                detail="Solo se aceptan archivos PDF"
            )
        
        # Guardar archivo
        documents_path = os.getenv("DOCUMENTS_PATH", "./documents")
        file_path = os.path.join(documents_path, file.filename)
        
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        # Procesar en background
        background_tasks.add_task(process_document_background, file_path)
        
        return {
            "message": f"Documento {file.filename} subido correctamente. Procesando en segundo plano.",
            "filename": file.filename,
            "status": "processing"
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

def process_document_background(file_path: str):
    """Procesa documento en segundo plano"""
    try:
        rag_service.process_new_document(file_path)
        print(f"Documento procesado exitosamente: {file_path}")
    except Exception as e:
        print(f"Error procesando documento {file_path}: {e}")

@router.get("/status")
async def get_system_status():
    """Verifica el estado del sistema"""
    return {
        "status": "ready" if rag_service.is_ready() else "not_ready",
        "total_chunks": len(rag_service.document_processor.chunks) if rag_service.is_ready() else 0,
        "message": "Sistema listo para responder preguntas" if rag_service.is_ready() else "Necesita procesar documentos"
    }

@router.get("/history", response_model=List[QueryLogResponse])
async def get_query_history(
    limit: int = 10,
    db: Session = Depends(get_db)
):
    """Obtiene el historial de preguntas y respuestas"""
    queries = db.query(QueryLog).order_by(QueryLog.timestamp.desc()).limit(limit).all()
    return queries

@router.get("/health")
async def health_check():
    """Health check para monitoring"""
    return {"status": "healthy", "service": "RAG API"}