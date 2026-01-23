"""
Document RAG Module
===================
A completely independent RAG (Retrieval-Augmented Generation) module for document Q&A.

This module is SEPARATE from the existing chatbot/agent logic and provides:
- PDF document ingestion and chunking
- Vector storage with ChromaDB (persistent)
- Retrieval using embeddings
- Generation using local Ollama LLM
- Quiz generation from documents

Usage:
    from backend.modules.document_rag import RAGService
    
    rag = RAGService()
    rag.ingest_document("path/to/document.pdf")
    result = rag.query("What is the main topic?")
    quiz = rag.generate_quiz("Topic", num_questions=5)
"""

from .rag_service import RAGService
from .ingest import load_pdf_documents
from .chunking import chunk_documents
from .vectorstore import ChromaVectorStore
from .retriever import DocumentRetriever
from .rag_chain import RAGChain
from .quiz_generator import QuizGenerator

__all__ = [
    "RAGService",
    "load_pdf_documents",
    "chunk_documents", 
    "ChromaVectorStore",
    "DocumentRetriever",
    "RAGChain",
    "QuizGenerator",
]
