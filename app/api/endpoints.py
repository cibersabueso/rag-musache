from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, BackgroundTasks
from sqlalchemy.orm import Session
from typing import List
import os
import shutil
import traceback
from ..models.database import get_db, QueryLog
from ..models.schemas import QuestionRequest, RAGResponse, QueryLogResponse
from ..services.rag_service import RAGService
import time

router = APIRouter()

# Inicialización lazy del servicio RAG
_rag_service = None

def get_rag_service():
    """Obtiene o inicializa el servicio RAG de forma lazy"""
    global _rag_service
    if _rag_service is None:
        try:
            _rag_service = RAGService()
            print("✅ RAG Service inicializado correctamente")
        except Exception as e:
            print(f"❌ Error inicializando RAG Service: {e}")
            print(f"Traceback: {traceback.format_exc()}")
            _rag_service = None
    return _rag_service

@router.post("/upload-document")
async def upload_document(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...)
):
    """Endpoint para subir y procesar documentos PDF y TXT"""
    try:
        print(f"📄 Iniciando upload de: {file.filename}")
        
        # Verificar servicio RAG
        rag_service = get_rag_service()
        if not rag_service:
            print("❌ RAG Service no disponible")
            raise HTTPException(
                status_code=503, 
                detail="Servicio RAG no disponible. Error de configuración."
            )
        
        # Validar archivo
        if not file.filename:
            raise HTTPException(status_code=400, detail="No se proporcionó nombre de archivo")
        
        print(f"📋 Archivo recibido: {file.filename}")
        
        # Validar extensión
        if not (file.filename.endswith('.pdf') or file.filename.endswith('.txt')):
            print(f"❌ Extensión no válida: {file.filename}")
            raise HTTPException(
                status_code=400, 
                detail="Solo se aceptan archivos PDF y TXT"
            )
        
        # Preparar directorio
        documents_path = os.getenv("DOCUMENTS_PATH", "./documents")
        print(f"📁 Directorio de documentos: {documents_path}")
        
        try:
            os.makedirs(documents_path, exist_ok=True)
            print(f"✅ Directorio creado/verificado: {documents_path}")
        except Exception as e:
            print(f"❌ Error creando directorio: {e}")
            raise HTTPException(status_code=500, detail=f"Error creando directorio: {str(e)}")
        
        # Guardar archivo
        file_path = os.path.join(documents_path, file.filename)
        print(f"💾 Guardando en: {file_path}")
        
        try:
            with open(file_path, "wb") as buffer:
                content = await file.read()
                buffer.write(content)
            print(f"✅ Archivo guardado: {len(content)} bytes")
        except Exception as e:
            print(f"❌ Error guardando archivo: {e}")
            raise HTTPException(status_code=500, detail=f"Error guardando archivo: {str(e)}")
        
        # Verificar que el archivo se guardó
        if not os.path.exists(file_path):
            print(f"❌ Archivo no encontrado después de guardar: {file_path}")
            raise HTTPException(status_code=500, detail="Error: archivo no se guardó correctamente")
        
        file_size = os.path.getsize(file_path)
        print(f"✅ Archivo verificado: {file_size} bytes en {file_path}")
        
        # Procesar en background
        print("🔄 Iniciando procesamiento en background...")
        background_tasks.add_task(process_document_background, file_path)
        
        response = {
            "message": f"Documento {file.filename} subido correctamente. Procesando en segundo plano.",
            "filename": file.filename,
            "status": "processing",
            "file_size": file_size,
            "file_path": file_path
        }
        
        print(f"✅ Upload exitoso: {response}")
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        error_msg = f"Error inesperado en upload: {str(e)}"
        print(f"❌ {error_msg}")
        print(f"Traceback completo: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=error_msg)

def process_document_background(file_path: str):
    """Procesa documento en segundo plano"""
    try:
        print(f"🔄 Iniciando procesamiento de: {file_path}")
        
        # Verificar que el archivo existe
        if not os.path.exists(file_path):
            print(f"❌ Archivo no encontrado para procesamiento: {file_path}")
            return
        
        rag_service = get_rag_service()
        if not rag_service:
            print("❌ RAG Service no disponible para procesamiento")
            return
        
        # Procesar documento
        rag_service.process_new_document(file_path)
        print(f"✅ Documento procesado exitosamente: {file_path}")
        
        # Verificar estado
        if rag_service.is_ready():
            chunks_count = len(rag_service.document_processor.chunks)
            print(f"✅ Sistema listo con {chunks_count} chunks")
        
    except Exception as e:
        print(f"❌ Error procesando documento {file_path}: {e}")
        print(f"Traceback: {traceback.format_exc()}")

@router.post("/ask", response_model=RAGResponse)
async def ask_question(
    request: QuestionRequest,
    db: Session = Depends(get_db)
):
    """Endpoint principal para hacer preguntas al sistema RAG"""
    try:
        rag_service = get_rag_service()
        
        if not rag_service:
            raise HTTPException(
                status_code=503, 
                detail="Servicio RAG no disponible. Error de configuración."
            )
        
        if not rag_service.is_ready():
            raise HTTPException(
                status_code=503, 
                detail="Sistema no listo. Necesita procesar documentos primero."
            )
        
        start_time = time.time()
        
        # Generar respuesta
        response = await rag_service.answer_question(request.question)
        
        # Guardar en base de datos solo si la respuesta es exitosa
        if not response.answer.startswith("Error"):
            try:
                query_log = QueryLog(
                    question=request.question,
                    answer=response.answer,
                    context_used=str([chunk.content[:100] + "..." for chunk in response.context_chunks]),
                    response_time=response.response_time
                )
                db.add(query_log)
                db.commit()
            except Exception as db_error:
                print(f"Error guardando en DB: {db_error}")
        
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/status")
async def get_system_status():
    """Verifica el estado del sistema"""
    rag_service = get_rag_service()
    
    if not rag_service:
        return {
            "status": "error",
            "total_chunks": 0,
            "message": "Servicio RAG no disponible"
        }
    
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
    try:
        queries = db.query(QueryLog).order_by(QueryLog.timestamp.desc()).limit(limit).all()
        return queries
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error accediendo al historial: {str(e)}")

@router.get("/health")
async def health_check():
    """Health check para monitoring"""
    rag_service = get_rag_service()
    return {
        "status": "healthy", 
        "service": "RAG API",
        "rag_service_available": rag_service is not None
    }

@router.get("/debug")
async def debug_info():
    """Debug endpoint para diagnosticar problemas"""
    try:
        import anthropic
        import sklearn
        
        documents_path = os.getenv("DOCUMENTS_PATH", "./documents")
        
        return {
            "anthropic_version": anthropic.__version__,
            "sklearn_available": True,
            "documents_path": documents_path,
            "documents_path_exists": os.path.exists(documents_path),
            "documents_path_writable": os.access(documents_path, os.W_OK) if os.path.exists(documents_path) else False,
            "env_vars": {
                "ANTHROPIC_API_KEY": "✅ Configurada" if os.getenv("ANTHROPIC_API_KEY") else "❌ No encontrada",
                "DATABASE_URL": os.getenv("DATABASE_URL", "No configurada"),
                "DOCUMENTS_PATH": documents_path
            },
            "rag_service_status": get_rag_service() is not None
        }
    except Exception as e:
        return {"error": str(e), "traceback": traceback.format_exc()}