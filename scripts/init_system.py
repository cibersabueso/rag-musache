# scripts/init_system.py
import os
import sys
import asyncio
from pathlib import Path

# Agregar el directorio raíz al path
sys.path.append(str(Path(__file__).parent.parent))

from app.services.rag_service import RAGService
from app.models.database import create_tables

async def initialize_system():
    """Inicializa el sistema RAG"""
    print("🚀 Inicializando sistema RAG...")
    
    # Crear tablas
    create_tables()
    print("✅ Base de datos inicializada")
    
    # Verificar documentos (PDF y TXT)
    documents_path = os.getenv("DOCUMENTS_PATH", "./documents")
    pdf_files = list(Path(documents_path).glob("*.pdf"))
    txt_files = list(Path(documents_path).glob("*.txt"))
    all_files = pdf_files + txt_files
    
    if not all_files:
        print("⚠️  No se encontraron archivos PDF o TXT en ./documents/")
        print("   Por favor, coloca un archivo PDF o TXT en el directorio documents/")
        return
    
    # Inicializar servicio RAG
    rag_service = RAGService()
    
    # Procesar documentos si no existe vector store
    if not rag_service.is_ready():
        print(f"📄 Procesando {len(all_files)} documentos...")
        for file in all_files:
            print(f"   Procesando: {file.name}")
            rag_service.process_new_document(str(file))
    
    print("✅ Sistema RAG listo para usar")
    print(f"📊 Total de chunks: {len(rag_service.document_processor.chunks)}")
    
    # Prueba rápida
    print("\n🧪 Realizando prueba rápida...")
    try:
        response = await rag_service.answer_question("¿De qué trata este documento?")
        print(f"   Respuesta: {response.answer[:100]}...")
        print("✅ Prueba exitosa")
    except Exception as e:
        print(f"❌ Error en prueba: {e}")

if __name__ == "__main__":
    asyncio.run(initialize_system())