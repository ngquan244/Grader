"""
RAG Service Module
==================
Main service class that coordinates all RAG operations.
This is the primary interface for the Document RAG feature.
"""

import os
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional

from langchain_core.documents import Document

from .config import rag_config
from .ingest import load_pdf_documents, get_file_metadata, compute_file_hash
from .chunking import chunk_documents
from .vectorstore import ChromaVectorStore
from .retriever import DocumentRetriever
from .rag_chain import RAGChain
from .quiz_generator import QuizGenerator

logger = logging.getLogger(__name__)


class RAGService:
    """
    Main service for Document RAG operations.
    
    Provides a simple API for:
    - Document ingestion (PDF upload and indexing)
    - Query execution (RAG-based Q&A)
    - Index management (stats, reset)
    
    Usage:
        rag = RAGService()
        
        # Ingest a document
        result = rag.ingest_document("path/to/doc.pdf")
        
        # Query the knowledge base
        answer = rag.query("What is the main topic?")
    """
    
    _instance: Optional["RAGService"] = None
    
    def __init__(
        self,
        persist_directory: Optional[str] = None,
        collection_name: Optional[str] = None,
        ollama_model: Optional[str] = None
    ):
        """
        Initialize RAG Service.
        
        Args:
            persist_directory: Directory for vector store persistence
            collection_name: Name of the vector collection
            ollama_model: Ollama model to use for generation
        """
        self.persist_directory = persist_directory or rag_config.PERSIST_DIRECTORY
        self.collection_name = collection_name or rag_config.COLLECTION_NAME
        self.ollama_model = ollama_model or rag_config.OLLAMA_MODEL
        
        logger.info("Initializing RAG Service...")
        logger.info(f"Persist directory: {self.persist_directory}")
        logger.info(f"Collection name: {self.collection_name}")
        logger.info(f"Ollama model: {self.ollama_model}")
        
        # Initialize components
        self._vector_store: Optional[ChromaVectorStore] = None
        self._retriever: Optional[DocumentRetriever] = None
        self._rag_chain: Optional[RAGChain] = None
        self._quiz_generator: Optional[QuizGenerator] = None
        
        # Lazy initialization flag
        self._initialized = False
    
    def _ensure_initialized(self):
        """Ensure all components are initialized."""
        if self._initialized:
            return
        
        logger.info("Initializing RAG components...")
        
        # Initialize vector store
        self._vector_store = ChromaVectorStore(
            persist_directory=self.persist_directory,
            collection_name=self.collection_name
        )
        
        # Initialize retriever
        self._retriever = DocumentRetriever(self._vector_store)
        
        # Initialize RAG chain
        self._rag_chain = RAGChain(
            retriever=self._retriever,
            model=self.ollama_model
        )
        
        # Initialize Quiz Generator
        self._quiz_generator = QuizGenerator(
            retriever=self._retriever,
            model=self.ollama_model
        )
        
        self._initialized = True
        logger.info("RAG Service initialized successfully")
    
    @classmethod
    def get_instance(cls) -> "RAGService":
        """Get singleton instance of RAG Service."""
        if cls._instance is None:
            cls._instance = RAGService()
        return cls._instance
    
    def ingest_document(
        self,
        file_path: str,
        skip_if_exists: bool = True
    ) -> Dict[str, Any]:
        """
        Ingest a PDF document into the vector store.
        
        Args:
            file_path: Path to PDF file
            skip_if_exists: Skip if document already indexed
            
        Returns:
            Dictionary with ingestion results
        """
        self._ensure_initialized()
        
        logger.info(f"Ingesting document: {file_path}")
        
        try:
            # Check if file exists
            if not os.path.exists(file_path):
                return {
                    "success": False,
                    "error": f"File not found: {file_path}",
                    "chunks_added": 0
                }
            
            # Get file metadata
            file_meta = get_file_metadata(file_path)
            
            # Check for duplicates
            if skip_if_exists and self._vector_store.is_document_indexed(file_meta["file_hash"]):
                logger.info(f"Document already indexed: {file_path}")
                return {
                    "success": True,
                    "message": "Document already indexed",
                    "file_hash": file_meta["file_hash"],
                    "filename": file_meta["filename"],
                    "chunks_added": 0,
                    "already_indexed": True
                }
            
            # Load PDF
            documents = load_pdf_documents(file_path)
            
            if not documents:
                return {
                    "success": False,
                    "error": "No content extracted from PDF",
                    "chunks_added": 0
                }
            
            # Chunk documents
            chunks = chunk_documents(documents)
            
            # Add to vector store
            added_count = self._vector_store.add_documents(chunks)
            
            logger.info(f"Successfully ingested {added_count} chunks from {file_path}")
            
            return {
                "success": True,
                "message": "Document indexed successfully",
                "file_hash": file_meta["file_hash"],
                "filename": file_meta["filename"],
                "pages_loaded": len(documents),
                "chunks_added": added_count,
                "already_indexed": False
            }
            
        except Exception as e:
            logger.error(f"Error ingesting document: {e}")
            return {
                "success": False,
                "error": str(e),
                "chunks_added": 0
            }
    
    def query(
        self,
        question: str,
        k: Optional[int] = None,
        return_context: bool = False
    ) -> Dict[str, Any]:
        """
        Query the document knowledge base.
        
        Args:
            question: User's question
            k: Number of documents to retrieve
            return_context: Include retrieved context in response
            
        Returns:
            Dictionary with:
            - answer: Generated answer
            - sources: List of source citations
            - context: (optional) Retrieved context
        """
        self._ensure_initialized()
        
        logger.info(f"Processing query: {question}")
        
        # Check if index has documents
        stats = self.get_index_stats()
        if stats["total_documents"] == 0:
            return {
                "success": False,
                "answer": "Chưa có tài liệu nào được index. Vui lòng upload và build index trước.",
                "sources": [],
                "error": "No documents indexed"
            }
        
        try:
            result = self._rag_chain.query(
                question=question,
                k=k,
                return_context=return_context
            )
            
            result["success"] = True
            return result
            
        except Exception as e:
            logger.error(f"Error processing query: {e}")
            return {
                "success": False,
                "answer": f"Lỗi khi xử lý câu hỏi: {str(e)}",
                "sources": [],
                "error": str(e)
            }
    
    def get_index_stats(self) -> Dict[str, Any]:
        """
        Get statistics about the document index.
        
        Returns:
            Dictionary with index statistics
        """
        self._ensure_initialized()
        
        return self._vector_store.get_collection_stats()
    
    def reset_index(self) -> Dict[str, Any]:
        """
        Reset the document index (delete all documents).
        
        Returns:
            Dictionary with reset status
        """
        self._ensure_initialized()
        
        logger.warning("Resetting document index")
        
        try:
            success = self._vector_store.reset_collection()
            
            if success:
                return {
                    "success": True,
                    "message": "Index reset successfully"
                }
            else:
                return {
                    "success": False,
                    "error": "Failed to reset index"
                }
        except Exception as e:
            logger.error(f"Error resetting index: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def check_ollama_status(self) -> Dict[str, Any]:
        """
        Check Ollama connection status.
        
        Returns:
            Dictionary with Ollama status
        """
        self._ensure_initialized()
        
        return self._rag_chain.check_ollama_connection()
    
    def get_config(self) -> Dict[str, Any]:
        """
        Get current RAG configuration.
        
        Returns:
            Dictionary with configuration values
        """
        return {
            "persist_directory": self.persist_directory,
            "collection_name": self.collection_name,
            "ollama_model": self.ollama_model,
            "ollama_base_url": rag_config.OLLAMA_BASE_URL,
            "chunk_size": rag_config.CHUNK_SIZE,
            "chunk_overlap": rag_config.CHUNK_OVERLAP,
            "embedding_model": rag_config.EMBEDDING_MODEL,
            "retriever_k": rag_config.RETRIEVER_K,
            "search_type": rag_config.SEARCH_TYPE
        }
    
    def generate_quiz(
        self,
        topic: str,
        num_questions: int = 5,
        difficulty: str = "medium",
        language: str = "vi",
        k: int = 10
    ) -> Dict[str, Any]:
        """
        Generate quiz questions from the document knowledge base.
        
        Args:
            topic: Topic or description of what to quiz about
            num_questions: Number of questions to generate (1-20)
            difficulty: Difficulty level - "easy", "medium", or "hard"
            language: "vi" for Vietnamese, "en" for English
            k: Number of documents to retrieve for context
            
        Returns:
            Dictionary with:
            - success: Whether generation succeeded
            - questions: List of quiz questions
            - error: Error message if any
        """
        self._ensure_initialized()
        
        logger.info(f"Generating quiz: topic='{topic}', num_questions={num_questions}, difficulty={difficulty}")
        
        # Validate num_questions
        num_questions = max(1, min(20, num_questions))
        
        # Check if index has documents
        stats = self.get_index_stats()
        if stats["total_documents"] == 0:
            return {
                "success": False,
                "questions": [],
                "error": "Chưa có tài liệu nào được index. Vui lòng upload và build index trước."
            }
        
        try:
            result = self._quiz_generator.generate_quiz(
                topic=topic,
                num_questions=num_questions,
                difficulty=difficulty,
                language=language,
                k=k
            )
            
            return result
            
        except Exception as e:
            logger.error(f"Error generating quiz: {e}")
            return {
                "success": False,
                "questions": [],
                "error": f"Lỗi khi tạo quiz: {str(e)}"
            }
