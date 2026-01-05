"""
Grading API routes - Exam Grading and Results
"""
import json
import logging
from fastapi import APIRouter

from backend.schemas import GradingRequest, GradingResponse, GradingResult, GradingSummary
from backend.services import grading_service
from backend.config import settings
from backend.core import ForbiddenException, Role
from src.config import Config

logger = logging.getLogger(__name__)
router = APIRouter()


def require_teacher():
    """Require teacher role for protected operations"""
    role = Config.get_role()
    if (role or "").upper() != Role.TEACHER.value:
        raise ForbiddenException(Role.TEACHER.value.lower(), role)


@router.post("/execute")
async def execute_grading():
    """Execute the grading notebook to process uploaded exam images"""
    from src.notebook_tool import get_notebook_tool
    
    notebook_tool = get_notebook_tool()
    result = notebook_tool._run()
    
    return {
        "success": True,
        "result": json.loads(result) if isinstance(result, str) else result
    }


@router.post("/summary", response_model=GradingResponse)
async def summarize_exam_results(request: GradingRequest):
    """Summarize exam results by exam code"""
    require_teacher()
    
    # Get results from database
    data = grading_service.get_results_by_exam_code(request.exam_code)
    
    # Export to Excel
    excel_file = grading_service.export_to_excel(
        exam_code=request.exam_code,
        summary=data["summary"],
        results=data["results"]
    )
    
    # Send email notification
    if excel_file:
        grading_service.send_email(
            to_email=settings.EMAIL_RECEIVER,
            subject=f"Kết quả tổng hợp mã đề {request.exam_code}",
            body=f"Đính kèm file Excel tổng hợp kết quả bài thi mã đề {request.exam_code}.",
            attachment=excel_file
        )
    
    # Convert to response model
    summary = GradingSummary(**data["summary"])
    results = [GradingResult(**r) for r in data["results"]]
    
    return GradingResponse(
        success=True,
        exam_code=request.exam_code,
        summary=summary,
        overall_assessment=data["overall_assessment"],
        results=results,
        excel_file=excel_file
    )


@router.get("/results")
async def get_all_results():
    """Get all grading results from JSON file"""
    results = grading_service.get_results_from_json()
    
    if not results:
        return {
            "success": False,
            "results": [],
            "message": "Chưa có kết quả chấm điểm"
        }
    
    return {"success": True, "results": results}
