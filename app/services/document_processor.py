import fitz  # PyMuPDF
import os
from typing import List, Tuple
import numpy as np
import pickle
from dotenv import load_dotenv
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

load_dotenv()

class DocumentProcessor:
    def __init__(self):
        print("✅ Usando TF-IDF + Búsqueda Coseno (100% compatible con macOS)")
        self.chunk_size = int(os.getenv("CHUNK_SIZE", 1000))
        self.chunk_overlap = int(os.getenv("CHUNK_OVERLAP", 200))
        self.vector_store_path = os.getenv("VECTOR_STORE_PATH", "./vector_store")
        self.documents_path = os.getenv("DOCUMENTS_PATH", "./documents")
        
        # Crear directorios si no existen
        os.makedirs(self.vector_store_path, exist_ok=True)
        os.makedirs(self.documents_path, exist_ok=True)
        
        self.chunks = []
        self.embeddings = None
        self.vectorizer = None
        
    def extract_text_from_pdf(self, pdf_path: str) -> List[Tuple[str, int]]:
        """Extrae texto de un PDF y devuelve chunks con número de página"""
        doc = fitz.open(pdf_path)
        text_chunks = []
        
        for page_num in range(doc.page_count):
            page = doc[page_num]
            text = page.get_text()
            
            # Dividir en chunks con overlap
            chunks = self._split_text_into_chunks(text)
            for chunk in chunks:
                if chunk.strip():  # Solo agregar chunks no vacíos
                    text_chunks.append((chunk, page_num + 1))
        
        doc.close()
        return text_chunks
    
    def extract_text_from_txt(self, txt_path: str) -> List[Tuple[str, int]]:
        """Extrae texto de un archivo TXT y devuelve chunks"""
        text_chunks = []
        
        with open(txt_path, 'r', encoding='utf-8') as file:
            content = file.read()
            
            # Dividir en chunks con overlap
            chunks = self._split_text_into_chunks(content)
            for i, chunk in enumerate(chunks):
                if chunk.strip():  # Solo agregar chunks no vacíos
                    text_chunks.append((chunk, i + 1))  # Simular páginas
        
        return text_chunks
    
    def extract_text_from_document(self, file_path: str) -> List[Tuple[str, int]]:
        """Extrae texto según el tipo de archivo"""
        file_extension = os.path.splitext(file_path)[1].lower()
        
        if file_extension == '.pdf':
            return self.extract_text_from_pdf(file_path)
        elif file_extension == '.txt':
            return self.extract_text_from_txt(file_path)
        else:
            raise ValueError(f"Formato de archivo no soportado: {file_extension}")
    
    def _split_text_into_chunks(self, text: str) -> List[str]:
        """Divide el texto en chunks con overlap"""
        chunks = []
        start = 0
        
        while start < len(text):
            end = min(start + self.chunk_size, len(text))
            chunk = text[start:end]
            chunks.append(chunk)
            
            if end == len(text):
                break
                
            start = end - self.chunk_overlap
        
        return chunks
    
    def create_embeddings(self, text_chunks: List[Tuple[str, int]]):
        """Crea embeddings TF-IDF para los chunks de texto"""
        self.chunks = text_chunks
        texts = [chunk[0] for chunk in text_chunks]
        
        print(f"Creando embeddings TF-IDF para {len(texts)} chunks...")
        
        # Usar TF-IDF
        self.vectorizer = TfidfVectorizer(
            max_features=1000, 
            stop_words='english',
            ngram_range=(1, 2),
            min_df=1
        )
        self.embeddings = self.vectorizer.fit_transform(texts)
        
        print(f"Embeddings creados: {self.embeddings.shape}")
    
    def save_vector_store(self):
        """Guarda el vector store en disco"""
        if self.embeddings is not None:
            # Guardar vectorizer
            with open(os.path.join(self.vector_store_path, "vectorizer.pkl"), "wb") as f:
                pickle.dump(self.vectorizer, f)
            
            # Guardar embeddings
            with open(os.path.join(self.vector_store_path, "embeddings.pkl"), "wb") as f:
                pickle.dump(self.embeddings, f)
            
            # Guardar chunks
            with open(os.path.join(self.vector_store_path, "chunks.pkl"), "wb") as f:
                pickle.dump(self.chunks, f)
            
            print("Vector store guardado exitosamente")
    
    def load_vector_store(self) -> bool:
        """Carga el vector store desde disco"""
        try:
            vectorizer_path = os.path.join(self.vector_store_path, "vectorizer.pkl")
            embeddings_path = os.path.join(self.vector_store_path, "embeddings.pkl")
            chunks_path = os.path.join(self.vector_store_path, "chunks.pkl")
            
            if all(os.path.exists(p) for p in [vectorizer_path, embeddings_path, chunks_path]):
                with open(vectorizer_path, "rb") as f:
                    self.vectorizer = pickle.load(f)
                
                with open(embeddings_path, "rb") as f:
                    self.embeddings = pickle.load(f)
                
                with open(chunks_path, "rb") as f:
                    self.chunks = pickle.load(f)
                
                print(f"Vector store cargado: {len(self.chunks)} chunks")
                return True
            return False
        except Exception as e:
            print(f"Error cargando vector store: {e}")
            return False
    
    def search_similar_chunks(self, query: str, top_k: int = 3) -> List[Tuple[str, int, float]]:
        """Busca chunks similares usando cosine similarity"""
        if self.embeddings is None or self.vectorizer is None:
            raise ValueError("Vector store no inicializado")
        
        # Vectorizar query
        query_vector = self.vectorizer.transform([query])
        
        # Calcular similitudes usando cosine similarity
        similarities = cosine_similarity(query_vector, self.embeddings).flatten()
        
        # Obtener top_k resultados
        top_indices = similarities.argsort()[-top_k:][::-1]
        
        results = []
        for idx in top_indices:
            if idx < len(self.chunks):
                chunk_text, page_num = self.chunks[idx]
                similarity_score = float(similarities[idx])
                results.append((chunk_text, page_num, similarity_score))
        
        return results
    
    def process_document(self, file_path: str):
        """Procesa un documento completo"""
        print(f"Procesando documento: {file_path}")
        
        # Extraer texto según el tipo de archivo
        text_chunks = self.extract_text_from_document(file_path)
        print(f"Extraídos {len(text_chunks)} chunks de texto")
        
        # Crear embeddings
        self.create_embeddings(text_chunks)
        
        # Guardar vector store
        self.save_vector_store()
        
        print("Documento procesado exitosamente")