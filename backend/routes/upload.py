"""
Upload API routes - File Upload Handling
"""
import logging
from fastapi import APIRouter, UploadFile, File
from typing import List

from backend.schemas import UploadResponse
from backend.services import file_service
from backend.core import Messages

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/images", response_model=UploadResponse)
async def upload_exam_images(files: List[UploadFile] = File(...)):
    """Upload exam images for grading"""
    uploaded_files, count = await file_service.upload_images(files)
    
    return UploadResponse(
        success=count > 0,
        message=f"Đã upload {count} ảnh thành công",
        files=uploaded_files,
        count=count
    )


@router.post("/pdf", response_model=UploadResponse)
async def upload_exam_pdf(file: UploadFile = File(...)):
    """Upload exam PDF for quiz generation"""
    filename = await file_service.upload_pdf(
        file,
        target_name="Đề thi Xử lý ảnh kỳ 2 năm học 2022-2023 - UET.pdf"
    )
    
    return UploadResponse(
        success=True,
        message=Messages.PDF_UPLOAD_SUCCESS,
        files=[filename],
        count=1
    )


@router.get("/status")
async def get_upload_status():
    """Get current upload status"""
    return file_service.get_upload_status()


@router.delete("/images")
async def clear_uploaded_images():
    """Clear all uploaded images"""
    count = file_service.clear_images()
    return {
        "message": f"Đã xóa {count} ảnh",
        "success": True,
        "count": count
    }
