"""
Document RAG API Routes
=======================
FastAPI routes for the Document RAG feature.
Completely independent from existing chatbot routes.
"""

import os
import shutil
import logging
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, File, UploadFile, HTTPException, Form
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from backend.modules.document_rag import RAGService
from backend.config import settings

logger = logging.getLogger(__name__)

router = APIRouter()

# Upload directory for RAG documents
RAG_UPLOAD_DIR = settings.DATA_DIR / "rag_uploads"
RAG_UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


# ===== Request/Response Models =====

class QueryRequest(BaseModel):
    """Request model for RAG query"""
    question: str
    k: Optional[int] = None
    return_context: bool = False


class QueryResponse(BaseModel):
    """Response model for RAG query"""
    success: bool
    answer: str
    sources: list
    context: Optional[str] = None
    error: Optional[str] = None


class IndexStatsResponse(BaseModel):
    """Response model for index statistics"""
    success: bool
    stats: dict


class IngestResponse(BaseModel):
    """Response model for document ingestion"""
    success: bool
    message: str
    filename: Optional[str] = None
    file_hash: Optional[str] = None
    pages_loaded: Optional[int] = None
    chunks_added: Optional[int] = None
    already_indexed: bool = False
    error: Optional[str] = None


class GenerateQuizRequest(BaseModel):
    """Request model for quiz generation"""
    topic: str
    num_questions: int = 5
    difficulty: str = "medium"  # easy, medium, hard
    language: str = "vi"  # vi, en
    k: int = 10


class QuizQuestion(BaseModel):
    """Model for a single quiz question"""
    question_number: int
    question: str
    options: dict
    correct_answer: str
    explanation: Optional[str] = None


class GenerateQuizResponse(BaseModel):
    """Response model for quiz generation"""
    success: bool
    questions: list = []
    topic: str = ""
    num_questions_requested: Optional[int] = None
    num_questions_generated: Optional[int] = None
    context_used: Optional[str] = None
    raw_response: Optional[str] = None
    error: Optional[str] = None


# ===== Helper Functions =====

def get_rag_service() -> RAGService:
    """Get RAG service singleton instance"""
    return RAGService.get_instance()


# ===== API Endpoints =====

@router.post("/upload", response_model=IngestResponse)
async def upload_document(file: UploadFile = File(...)):
    """
    Upload a PDF document for RAG.
    
    This endpoint only saves the file. Use /build-index to index it.
    """
    logger.info(f"Uploading document: {file.filename}")
    
    # Validate file type
    if not file.filename.lower().endswith('.pdf'):
        raise HTTPException(status_code=400, detail="Only PDF files are supported")
    
    try:
        # Save uploaded file
        file_path = RAG_UPLOAD_DIR / file.filename
        
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        logger.info(f"File saved to: {file_path}")
        
        return IngestResponse(
            success=True,
            message=f"File uploaded successfully: {file.filename}",
            filename=file.filename
        )
        
    except Exception as e:
        logger.error(f"Error uploading file: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/build-index", response_model=IngestResponse)
async def build_index(filename: str = Form(...)):
    """
    Build/update the vector index for an uploaded document.
    
    Args:
        filename: Name of the uploaded file to index
    """
    logger.info(f"Building index for: {filename}")
    
    file_path = RAG_UPLOAD_DIR / filename
    
    if not file_path.exists():
        raise HTTPException(status_code=404, detail=f"File not found: {filename}")
    
    try:
        rag_service = get_rag_service()
        result = rag_service.ingest_document(str(file_path))
        
        return IngestResponse(
            success=result.get("success", False),
            message=result.get("message", ""),
            filename=result.get("filename"),
            file_hash=result.get("file_hash"),
            pages_loaded=result.get("pages_loaded"),
            chunks_added=result.get("chunks_added"),
            already_indexed=result.get("already_indexed", False),
            error=result.get("error")
        )
        
    except Exception as e:
        logger.error(f"Error building index: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/upload-and-index", response_model=IngestResponse)
async def upload_and_index(file: UploadFile = File(...)):
    """
    Upload and immediately index a PDF document.
    
    Combines upload and build-index in one operation.
    """
    logger.info(f"Upload and index: {file.filename}")
    
    # Validate file type
    if not file.filename.lower().endswith('.pdf'):
        raise HTTPException(status_code=400, detail="Only PDF files are supported")
    
    try:
        # Save uploaded file
        file_path = RAG_UPLOAD_DIR / file.filename
        
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        logger.info(f"File saved to: {file_path}")
        
        # Index the document
        rag_service = get_rag_service()
        result = rag_service.ingest_document(str(file_path))
        
        return IngestResponse(
            success=result.get("success", False),
            message=result.get("message", ""),
            filename=result.get("filename"),
            file_hash=result.get("file_hash"),
            pages_loaded=result.get("pages_loaded"),
            chunks_added=result.get("chunks_added"),
            already_indexed=result.get("already_indexed", False),
            error=result.get("error")
        )
        
    except Exception as e:
        logger.error(f"Error in upload-and-index: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/query", response_model=QueryResponse)
async def query_documents(request: QueryRequest):
    """
    Query the document knowledge base.
    
    Args:
        request: Query request with question and options
        
    Returns:
        Answer with source citations
    """
    logger.info(f"RAG Query: {request.question}")
    
    if not request.question or not request.question.strip():
        raise HTTPException(status_code=400, detail="Question cannot be empty")
    
    try:
        rag_service = get_rag_service()
        result = rag_service.query(
            question=request.question,
            k=request.k,
            return_context=request.return_context
        )
        
        return QueryResponse(
            success=result.get("success", False),
            answer=result.get("answer", ""),
            sources=result.get("sources", []),
            context=result.get("context"),
            error=result.get("error")
        )
        
    except Exception as e:
        logger.error(f"Error processing query: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/stats", response_model=IndexStatsResponse)
async def get_index_stats():
    """
    Get statistics about the document index.
    """
    try:
        rag_service = get_rag_service()
        stats = rag_service.get_index_stats()
        
        return IndexStatsResponse(
            success=True,
            stats=stats
        )
        
    except Exception as e:
        logger.error(f"Error getting stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/reset")
async def reset_index():
    """
    Reset the document index (delete all indexed documents).
    
    WARNING: This will delete all indexed documents!
    """
    logger.warning("Resetting document index")
    
    try:
        rag_service = get_rag_service()
        result = rag_service.reset_index()
        
        return result
        
    except Exception as e:
        logger.error(f"Error resetting index: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/ollama-status")
async def check_ollama_status():
    """
    Check if Ollama is running and the model is available.
    """
    try:
        rag_service = get_rag_service()
        status = rag_service.check_ollama_status()
        
        return status
        
    except Exception as e:
        logger.error(f"Error checking Ollama status: {e}")
        return {
            "connected": False,
            "error": str(e),
            "message": f"Error checking Ollama: {str(e)}"
        }


@router.get("/config")
async def get_rag_config():
    """
    Get current RAG configuration.
    """
    try:
        rag_service = get_rag_service()
        config = rag_service.get_config()
        
        return {
            "success": True,
            "config": config
        }
        
    except Exception as e:
        logger.error(f"Error getting config: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/uploaded-files")
async def list_uploaded_files():
    """
    List all uploaded PDF files.
    """
    try:
        files = []
        for file_path in RAG_UPLOAD_DIR.glob("*.pdf"):
            stat = file_path.stat()
            files.append({
                "filename": file_path.name,
                "size": stat.st_size,
                "modified": stat.st_mtime
            })
        
        return {
            "success": True,
            "files": files,
            "count": len(files)
        }
        
    except Exception as e:
        logger.error(f"Error listing files: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/uploaded-files/{filename}")
async def delete_uploaded_file(filename: str):
    """
    Delete an uploaded file.
    
    Note: This does not remove it from the index.
    Use /reset to clear the index.
    """
    file_path = RAG_UPLOAD_DIR / filename
    
    if not file_path.exists():
        raise HTTPException(status_code=404, detail=f"File not found: {filename}")
    
    try:
        os.remove(file_path)
        
        return {
            "success": True,
            "message": f"File deleted: {filename}"
        }
        
    except Exception as e:
        logger.error(f"Error deleting file: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# QUIZ GENERATION ENDPOINTS
# ============================================================================

@router.post("/generate-quiz", response_model=GenerateQuizResponse)
async def generate_quiz_from_documents(request: GenerateQuizRequest):
    """
    Generate quiz questions from indexed documents using RAG.
    
    This endpoint:
    1. Retrieves relevant context from indexed documents based on the topic
    2. Uses LLM (Ollama) to generate multiple choice questions
    3. Returns formatted quiz with questions, options, and answers
    
    Args:
        request: Quiz generation request with topic and number of questions
        
    Returns:
        Generated quiz questions with answers
    """
    logger.info(f"Generate quiz request - Topic: {request.topic}, Num questions: {request.num_questions}")
    
    # Validate inputs
    if not request.topic or not request.topic.strip():
        raise HTTPException(status_code=400, detail="Topic cannot be empty")
    
    if request.num_questions < 1:
        raise HTTPException(status_code=400, detail="Number of questions must be at least 1")
    
    if request.num_questions > 20:
        raise HTTPException(status_code=400, detail="Maximum 20 questions per request")
    
    try:
        rag_service = get_rag_service()
        
        # Check if index has documents
        stats = rag_service.get_index_stats()
        if stats.get("total_documents", 0) == 0:
            raise HTTPException(
                status_code=400, 
                detail="No documents indexed. Please upload and index documents first."
            )
        
        # Generate quiz
        result = rag_service.generate_quiz(
            topic=request.topic.strip(),
            num_questions=request.num_questions,
            difficulty=request.difficulty,
            language=request.language
        )
        
        if not result.get("success"):
            return GenerateQuizResponse(
                success=False,
                error=result.get("error", "Failed to generate quiz"),
                questions=[],
                topic=request.topic,
                num_questions_requested=request.num_questions,
                num_questions_generated=0
            )
        
        # Convert questions to response model
        questions = []
        for q in result.get("questions", []):
            questions.append(QuizQuestion(
                question_number=q.get("question_number", 0),
                question=q.get("question", ""),
                options=q.get("options", {}),
                correct_answer=q.get("correct_answer", ""),
                explanation=q.get("explanation")
            ))
        
        return GenerateQuizResponse(
            success=True,
            questions=questions,
            topic=request.topic,
            num_questions_requested=request.num_questions,
            num_questions_generated=len(questions),
            context_used=result.get("context_used"),
            raw_response=result.get("raw_response") if request.language == "vi" else None
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error generating quiz: {e}")
        raise HTTPException(status_code=500, detail=str(e))
