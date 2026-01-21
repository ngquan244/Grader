"""
Quiz API routes - Quiz Generation and Management
"""
import logging
from fastapi import APIRouter, UploadFile, File
from fastapi.responses import FileResponse

from backend.schemas import QuizGenerateRequest, QuizGenerateResponse, QuizListResponse
from backend.services import quiz_service, file_service
from backend.config import settings
from backend.core import NotFoundException

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/extract")
async def extract_questions_from_uploaded_pdf(file: UploadFile = File(...)):
    """Extract questions from uploaded PDF"""
    # Save uploaded file
    await file_service.upload_pdf(file, "temp_upload.pdf")
    temp_path = settings.DATA_DIR / "quiz" / "temp_upload.pdf"
    
    # Extract questions
    questions = quiz_service.extract_questions(str(temp_path))
    
    return {
        "success": True,
        "message": f"Đã trích xuất {len(questions)} câu hỏi",
        "questions": questions,
        "count": len(questions)
    }


@router.post("/generate", response_model=QuizGenerateResponse)
async def generate_quiz(request: QuizGenerateRequest):
    """Generate a quiz from extracted questions"""
    result = quiz_service.generate_quiz(
        num_questions=request.num_questions,
        source_pdf=request.source_pdf
    )
    
    return QuizGenerateResponse(
        success=True,
        quiz_id=result["quiz_id"],
        num_questions=result["num_questions"],
        html_file=result["html_file"],
        file_url=result["file_url"],
        message=f"Đã tạo quiz thành công với {result['num_questions']} câu hỏi"
    )


@router.get("/list", response_model=QuizListResponse)
async def list_quizzes():
    """List all generated quizzes"""
    quizzes = quiz_service.list_quizzes()
    return QuizListResponse(quizzes=quizzes, total=len(quizzes))


@router.get("/{quiz_id}")
async def get_quiz(quiz_id: str):
    """Get a specific quiz by ID"""
    quiz_data = quiz_service.get_quiz(quiz_id)
    return {
        "success": True,
        "quiz": quiz_data,
        "html_url": f"/static/quizzes/{quiz_id}.html"
    }


@router.delete("/{quiz_id}")
async def delete_quiz(quiz_id: str):
    """Delete a quiz by ID"""
    require_teacher()
    
    quiz_service.delete_quiz(quiz_id)
    return {
        "success": True,
        "message": f"Đã xóa quiz {quiz_id} thành công"
    }


@router.get("/{quiz_id}/download")
async def download_quiz_html(quiz_id: str):
    """Download quiz HTML file"""
    html_file = settings.QUIZ_DIR / f"{quiz_id}.html"
    if not html_file.exists():
        raise NotFoundException("Quiz HTML", quiz_id)
    
    return FileResponse(
        path=str(html_file),
        filename=f"{quiz_id}.html",
        media_type="text/html"
    )
