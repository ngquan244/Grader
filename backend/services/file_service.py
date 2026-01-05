"""
File Service
Handles file upload and management
"""
import shutil
import logging
from pathlib import Path
from typing import List, Tuple, Optional
from fastapi import UploadFile

from backend.config import settings
from backend.core import BadRequestException, FileLimits
from backend.utils import (
    ensure_directory,
    clear_directory,
    is_valid_image,
    is_valid_pdf,
    safe_filename
)

logger = logging.getLogger(__name__)


class FileService:
    """Service for file upload and management"""
    
    def __init__(self):
        self.images_dir = settings.PROJECT_ROOT / "kaggle" / "Filled-temp"
        self.pdf_dir = settings.DATA_DIR / "quiz"
        ensure_directory(self.images_dir)
        ensure_directory(self.pdf_dir)
    
    async def upload_images(
        self,
        files: List[UploadFile],
        clear_existing: bool = True
    ) -> Tuple[List[str], int]:
        """Upload exam images"""
        if clear_existing:
            clear_directory(self.images_dir)
        
        uploaded = []
        for file in files:
            if not file.filename:
                continue
            
            if not is_valid_image(file.filename):
                logger.warning(f"Skipping invalid image: {file.filename}")
                continue
            
            # Check file size
            content = await file.read()
            if len(content) > FileLimits.MAX_IMAGE_SIZE:
                logger.warning(f"File too large: {file.filename}")
                continue
            
            # Save file
            filename = safe_filename(file.filename)
            dest_path = self.images_dir / filename
            
            with open(dest_path, "wb") as buffer:
                buffer.write(content)
            
            uploaded.append(filename)
            logger.info(f"Uploaded image: {filename}")
        
        return uploaded, len(uploaded)
    
    async def upload_pdf(
        self,
        file: UploadFile,
        target_name: Optional[str] = None
    ) -> str:
        """Upload a PDF file"""
        if not file.filename:
            raise BadRequestException("Filename is required")
        
        if not is_valid_pdf(file.filename):
            raise BadRequestException("File must be a PDF")
        
        content = await file.read()
        if len(content) > FileLimits.MAX_PDF_SIZE:
            raise BadRequestException("File size exceeds limit")
        
        # Use provided name or original filename
        filename = target_name or safe_filename(file.filename)
        if not filename.endswith(".pdf"):
            filename += ".pdf"
        
        dest_path = self.pdf_dir / filename
        
        with open(dest_path, "wb") as buffer:
            buffer.write(content)
        
        logger.info(f"Uploaded PDF: {filename}")
        return filename
    
    def get_upload_status(self) -> dict:
        """Get current upload status"""
        images = list(self.images_dir.glob("*")) if self.images_dir.exists() else []
        pdfs = list(self.pdf_dir.glob("*.pdf")) if self.pdf_dir.exists() else []
        
        return {
            "images": {
                "count": len([f for f in images if f.is_file()]),
                "files": [f.name for f in images if f.is_file()]
            },
            "pdfs": {
                "count": len(pdfs),
                "files": [f.name for f in pdfs]
            }
        }
    
    def clear_images(self) -> int:
        """Clear all uploaded images"""
        return clear_directory(self.images_dir)
    
    def clear_pdfs(self) -> int:
        """Clear all uploaded PDFs"""
        return clear_directory(self.pdf_dir, "*.pdf")


# Singleton instance
file_service = FileService()
