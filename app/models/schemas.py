from pydantic import BaseModel
from datetime import datetime
from typing import List, Optional

class QuestionRequest(BaseModel):
    question: str

class DocumentChunk(BaseModel):
    content: str
    page: int
    similarity_score: float

class RAGResponse(BaseModel):
    question: str
    answer: str
    context_chunks: List[DocumentChunk]
    response_time: str
    timestamp: datetime

class QueryLogResponse(BaseModel):
    id: int
    question: str
    answer: str
    timestamp: datetime
    response_time: str
    
    class Config:
        from_attributes = True