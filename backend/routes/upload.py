"""
Upload API routes
Handles file uploads for exam images and PDFs
"""
import shutil
from pathlib import Path
from fastapi import APIRouter, UploadFile, File, HTTPException
from typing import List

from backend.schemas import UploadResponse
from backend.config import settings

router = APIRouter()


@router.post("/images", response_model=UploadResponse)
async def upload_exam_images(files: List[UploadFile] = File(...)):
    """
    Upload exam images for grading
    Images are saved to kaggle/Filled-temp/
    """
    try:
        # Create destination folder
        dest_folder = settings.PROJECT_ROOT / "kaggle" / "Filled-temp"
        dest_folder.mkdir(parents=True, exist_ok=True)
        
        # Clear existing images
        for existing_file in dest_folder.glob("*"):
            if existing_file.is_file():
                existing_file.unlink()
        
        uploaded_files = []
        
        for file in files:
            if file.filename:
                # Validate file type
                if not file.content_type or not file.content_type.startswith("image/"):
                    continue
                    
                dest_path = dest_folder / file.filename
                
                # Save file
                with open(dest_path, "wb") as buffer:
                    content = await file.read()
                    buffer.write(content)
                
                uploaded_files.append(file.filename)
        
        return UploadResponse(
            success=True,
            message=f"Đã upload {len(uploaded_files)} ảnh thành công",
            files=uploaded_files,
            count=len(uploaded_files)
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/pdf", response_model=UploadResponse)
async def upload_exam_pdf(file: UploadFile = File(...)):
    """
    Upload exam PDF for quiz generation
    PDF is saved to data/quiz/
    """
    try:
        if not file.filename or not file.filename.endswith(".pdf"):
            raise HTTPException(status_code=400, detail="File must be a PDF")
        
        # Create destination folder
        dest_folder = settings.DATA_DIR / "quiz"
        dest_folder.mkdir(parents=True, exist_ok=True)
        
        # Save with fixed name for processing
        dest_path = dest_folder / "Đề thi Xử lý ảnh kỳ 2 năm học 2022-2023 - UET.pdf"
        
        with open(dest_path, "wb") as buffer:
            content = await file.read()
            buffer.write(content)
        
        return UploadResponse(
            success=True,
            message="Đã upload PDF đề thi thành công",
            files=[file.filename],
            count=1
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/status")
async def get_upload_status():
    """
    Get current upload status
    """
    images_folder = settings.PROJECT_ROOT / "kaggle" / "Filled-temp"
    pdf_folder = settings.DATA_DIR / "quiz"
    
    images = list(images_folder.glob("*")) if images_folder.exists() else []
    pdfs = list(pdf_folder.glob("*.pdf")) if pdf_folder.exists() else []
    
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


@router.delete("/images")
async def clear_uploaded_images():
    """Clear all uploaded images"""
    try:
        dest_folder = settings.PROJECT_ROOT / "kaggle" / "Filled-temp"
        if dest_folder.exists():
            for file in dest_folder.glob("*"):
                if file.is_file():
                    file.unlink()
        
        return {"message": "Đã xóa tất cả ảnh", "success": True}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
