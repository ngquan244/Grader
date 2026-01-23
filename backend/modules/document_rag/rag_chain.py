"""
RAG Chain Module
================
Build and execute the RAG chain using local Ollama LLM.
NO API KEYS required - runs completely locally.
"""

import logging
from typing import List, Dict, Any, Optional

from langchain_core.documents import Document
from langchain_core.prompts import ChatPromptTemplate
from langchain_ollama import ChatOllama

from .config import rag_config
from .retriever import DocumentRetriever

logger = logging.getLogger(__name__)


# RAG Prompt Template
RAG_PROMPT_TEMPLATE = """Bạn là một trợ lý AI chuyên trả lời câu hỏi dựa trên tài liệu được cung cấp.

NGUYÊN TẮC QUAN TRỌNG:
1. CHỈ trả lời dựa trên thông tin trong phần Context bên dưới
2. Nếu Context không chứa đủ thông tin để trả lời, hãy nói rõ: "Không tìm thấy thông tin liên quan trong tài liệu"
3. KHÔNG bịa đặt hoặc sử dụng kiến thức bên ngoài
4. Trả lời ngắn gọn, rõ ràng và chính xác
5. Nếu có thể, trích dẫn nguồn (trang, phần) khi trả lời

CONTEXT TỪ TÀI LIỆU:
{context}

CÂU HỎI: {question}

TRẢ LỜI:"""


class RAGChain:
    """
    RAG Chain for question answering using local Ollama LLM.
    
    Features:
    - Uses Ollama for local inference (no API keys)
    - Returns answers with source citations
    - Configurable model and parameters
    """
    
    def __init__(
        self,
        retriever: DocumentRetriever,
        model: Optional[str] = None,
        temperature: Optional[float] = None,
        base_url: Optional[str] = None
    ):
        """
        Initialize RAG chain.
        
        Args:
            retriever: DocumentRetriever instance
            model: Ollama model name (default: llama3)
            temperature: Generation temperature
            base_url: Ollama API base URL
        """
        self.retriever = retriever
        self.model = model or rag_config.OLLAMA_MODEL
        self.temperature = temperature or rag_config.OLLAMA_TEMPERATURE
        self.base_url = base_url or rag_config.OLLAMA_BASE_URL
        
        # Initialize LLM
        self._init_llm()
        
        # Initialize prompt
        self.prompt = ChatPromptTemplate.from_template(RAG_PROMPT_TEMPLATE)
    
    def _init_llm(self):
        """Initialize Ollama LLM."""
        logger.info(f"Initializing Ollama LLM: {self.model}")
        logger.info(f"Ollama base URL: {self.base_url}")
        
        self.llm = ChatOllama(
            model=self.model,
            temperature=self.temperature,
            base_url=self.base_url,
            num_ctx=rag_config.OLLAMA_NUM_CTX,
        )
        
        logger.info("Ollama LLM initialized")
    
    def query(
        self,
        question: str,
        k: Optional[int] = None,
        return_context: bool = False
    ) -> Dict[str, Any]:
        """
        Execute RAG query.
        
        Args:
            question: User's question
            k: Number of documents to retrieve
            return_context: Whether to include retrieved context in response
            
        Returns:
            Dictionary with:
            - answer: Generated answer
            - sources: List of source citations
            - context: (optional) Retrieved context text
        """
        logger.info(f"RAG Query: {question}")
        
        # Step 1: Retrieve relevant documents
        documents = self.retriever.retrieve(question, k=k)
        
        if not documents:
            return {
                "answer": "Không tìm thấy thông tin liên quan trong tài liệu.",
                "sources": [],
                "context": "" if return_context else None
            }
        
        # Step 2: Format context
        context = self.retriever.format_context(documents)
        
        # Step 3: Build and run chain
        chain = self.prompt | self.llm
        
        try:
            logger.info("Generating answer with Ollama...")
            
            response = chain.invoke({
                "context": context,
                "question": question
            })
            
            answer = response.content if hasattr(response, 'content') else str(response)
            
            logger.info("Answer generated successfully")
            
        except Exception as e:
            logger.error(f"Error generating answer: {e}")
            return {
                "answer": f"Lỗi khi tạo câu trả lời: {str(e)}",
                "sources": [],
                "context": context if return_context else None,
                "error": str(e)
            }
        
        # Step 4: Extract citations
        sources = self.retriever.extract_citations(documents)
        
        # Build response
        result = {
            "answer": answer,
            "sources": sources
        }
        
        if return_context:
            result["context"] = context
        
        return result
    
    def query_with_custom_prompt(
        self,
        question: str,
        prompt_template: str,
        k: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Execute RAG query with a custom prompt template.
        
        Args:
            question: User's question
            prompt_template: Custom prompt template (must have {context} and {question})
            k: Number of documents to retrieve
            
        Returns:
            Dictionary with answer and sources
        """
        # Retrieve documents
        documents = self.retriever.retrieve(question, k=k)
        
        if not documents:
            return {
                "answer": "Không tìm thấy thông tin liên quan trong tài liệu.",
                "sources": []
            }
        
        # Format context
        context = self.retriever.format_context(documents)
        
        # Use custom prompt
        custom_prompt = ChatPromptTemplate.from_template(prompt_template)
        chain = custom_prompt | self.llm
        
        try:
            response = chain.invoke({
                "context": context,
                "question": question
            })
            answer = response.content if hasattr(response, 'content') else str(response)
        except Exception as e:
            logger.error(f"Error with custom prompt: {e}")
            return {
                "answer": f"Lỗi: {str(e)}",
                "sources": [],
                "error": str(e)
            }
        
        sources = self.retriever.extract_citations(documents)
        
        return {
            "answer": answer,
            "sources": sources
        }
    
    def check_ollama_connection(self) -> Dict[str, Any]:
        """
        Check if Ollama is running and model is available.
        
        Returns:
            Dictionary with connection status
        """
        try:
            # Try a simple generation
            response = self.llm.invoke("Say 'OK' if you can read this.")
            
            return {
                "connected": True,
                "model": self.model,
                "base_url": self.base_url,
                "message": "Ollama connection successful"
            }
        except Exception as e:
            logger.error(f"Ollama connection check failed: {e}")
            return {
                "connected": False,
                "model": self.model,
                "base_url": self.base_url,
                "error": str(e),
                "message": f"Không thể kết nối Ollama: {str(e)}"
            }
