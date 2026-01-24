"""
Topic Storage Module
====================
Stores extracted topics per document for quick retrieval.
"""

import json
import logging
from pathlib import Path
from typing import Dict, List, Any, Optional
from datetime import datetime

from .config import rag_config

logger = logging.getLogger(__name__)


class TopicStorage:
    """
    Persistent storage for document topics.
    Topics are extracted once during indexing and stored for quick retrieval.
    """
    
    def __init__(self, storage_dir: Optional[str] = None):
        """
        Initialize topic storage.
        
        Args:
            storage_dir: Directory to store topic data
        """
        self.storage_dir = Path(storage_dir or rag_config.PERSIST_DIRECTORY)
        self.storage_file = self.storage_dir / "document_topics.json"
        self._topics: Dict[str, Dict[str, Any]] = {}
        
        # Ensure directory exists
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        
        # Load existing topics
        self._load()
    
    def _load(self):
        """Load topics from disk."""
        try:
            if self.storage_file.exists():
                with open(self.storage_file, 'r', encoding='utf-8') as f:
                    self._topics = json.load(f)
                logger.info(f"Loaded topics for {len(self._topics)} documents")
        except Exception as e:
            logger.warning(f"Could not load topics: {e}")
            self._topics = {}
    
    def _save(self):
        """Save topics to disk."""
        try:
            with open(self.storage_file, 'w', encoding='utf-8') as f:
                json.dump(self._topics, f, ensure_ascii=False, indent=2)
            logger.info(f"Saved topics for {len(self._topics)} documents")
        except Exception as e:
            logger.error(f"Could not save topics: {e}")
    
    def save_topics(
        self,
        file_hash: str,
        filename: str,
        topics: List[Dict[str, str]]
    ):
        """
        Save topics for a document.
        
        Args:
            file_hash: MD5 hash of the document
            filename: Original filename
            topics: List of topic dictionaries with 'name' and 'description'
        """
        self._topics[file_hash] = {
            "filename": filename,
            "topics": topics,
            "extracted_at": datetime.now().isoformat()
        }
        self._save()
        logger.info(f"Saved {len(topics)} topics for {filename}")
    
    def get_topics(self, file_hash: str) -> Optional[List[Dict[str, str]]]:
        """
        Get topics for a document.
        
        Args:
            file_hash: MD5 hash of the document
            
        Returns:
            List of topics or None if not found
        """
        if file_hash in self._topics:
            return self._topics[file_hash].get("topics", [])
        return None
    
    def get_topics_by_filename(self, filename: str) -> Optional[List[Dict[str, str]]]:
        """
        Get topics by filename.
        
        Args:
            filename: Document filename
            
        Returns:
            List of topics or None if not found
        """
        for file_hash, data in self._topics.items():
            if data.get("filename") == filename:
                return data.get("topics", [])
        return None
    
    def has_topics(self, file_hash: str) -> bool:
        """Check if topics exist for a document."""
        return file_hash in self._topics
    
    def get_all_documents(self) -> List[Dict[str, Any]]:
        """
        Get list of all documents with topics.
        
        Returns:
            List of document info dictionaries
        """
        documents = []
        for file_hash, data in self._topics.items():
            documents.append({
                "file_hash": file_hash,
                "filename": data.get("filename", "unknown"),
                "topic_count": len(data.get("topics", [])),
                "extracted_at": data.get("extracted_at")
            })
        return documents
    
    def remove_document(self, file_hash: str) -> bool:
        """
        Remove topics for a document.
        
        Args:
            file_hash: MD5 hash of the document
            
        Returns:
            True if removed, False if not found
        """
        if file_hash in self._topics:
            del self._topics[file_hash]
            self._save()
            return True
        return False
    
    def clear(self):
        """Clear all stored topics."""
        self._topics = {}
        self._save()
        logger.info("Cleared all stored topics")


# Global instance
topic_storage = TopicStorage()
