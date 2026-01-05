"""
Quiz API routes
Handles quiz generation and management
"""
import json
import random
import datetime
import sys
from pathlib import Path
from fastapi import APIRouter, HTTPException, UploadFile, File
from fastapi.responses import FileResponse
from typing import List, Optional

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from backend.schemas import (
    QuizGenerateRequest, QuizGenerateResponse, 
    QuizListResponse, QuizData, QuizQuestion
)
from backend.config import settings
from src.config import Config

# Try to import quiz extraction utility
try:
    sys.path.append(str(settings.PROJECT_ROOT / "quiz-gen"))
    from utils import extract_questions_from_pdf
except ImportError:
    extract_questions_from_pdf = None

router = APIRouter()


def check_role(role_required: str) -> bool:
    """Check if current role matches required role"""
    actual_role = Config.get_role()
    return (actual_role or "").lower() == role_required.lower()


@router.post("/extract")
async def extract_questions_from_uploaded_pdf(file: UploadFile = File(...)):
    """
    Extract questions from uploaded PDF
    """
    if extract_questions_from_pdf is None:
        raise HTTPException(status_code=500, detail="Module quiz-gen chưa được cài đặt")
    
    try:
        # Save uploaded file temporarily
        temp_path = settings.DATA_DIR / "quiz" / "temp_upload.pdf"
        temp_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(temp_path, "wb") as buffer:
            content = await file.read()
            buffer.write(content)
        
        # Extract questions
        questions = extract_questions_from_pdf(str(temp_path))
        
        if not questions:
            return {
                "success": False,
                "message": "Không tìm thấy câu hỏi trong PDF",
                "questions": [],
                "count": 0
            }
        
        return {
            "success": True,
            "message": f"Đã trích xuất {len(questions)} câu hỏi",
            "questions": questions,
            "count": len(questions)
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/generate", response_model=QuizGenerateResponse)
async def generate_quiz(request: QuizGenerateRequest):
    """
    Generate a quiz from extracted questions
    """
    if not check_role("teacher"):
        raise HTTPException(
            status_code=403, 
            detail="Chỉ giáo viên mới có quyền tạo quiz"
        )
    
    if extract_questions_from_pdf is None:
        raise HTTPException(status_code=500, detail="Module quiz-gen chưa được cài đặt")
    
    try:
        # Find PDF file
        quiz_folder = settings.DATA_DIR / "quiz"
        if not quiz_folder.exists():
            raise HTTPException(status_code=404, detail="Thư mục data/quiz/ không tồn tại")
        
        pdf_files = list(quiz_folder.glob("*.pdf"))
        if not pdf_files:
            raise HTTPException(status_code=404, detail="Không tìm thấy file PDF trong data/quiz/")
        
        pdf_file = pdf_files[0]
        
        # Extract questions
        questions = extract_questions_from_pdf(str(pdf_file))
        if not questions:
            raise HTTPException(status_code=400, detail="Không tìm thấy câu hỏi trong PDF")
        
        # Randomly select questions
        selected_questions = random.sample(questions, min(request.num_questions, len(questions)))
        
        # Create quiz data
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        quiz_id = f"quiz_{timestamp}"
        
        quiz_data = {
            "id": quiz_id,
            "timestamp": timestamp,
            "source_pdf": pdf_file.name,
            "questions": selected_questions,
            "num_questions": len(selected_questions)
        }
        
        # Save quiz JSON
        output_folder = settings.QUIZ_DIR
        output_folder.mkdir(parents=True, exist_ok=True)
        
        quiz_json_file = output_folder / f"{quiz_id}.json"
        with open(quiz_json_file, 'w', encoding='utf-8') as f:
            json.dump(quiz_data, f, ensure_ascii=False, indent=2)
        
        # Generate HTML file
        html_file = output_folder / f"{quiz_id}.html"
        html_content = generate_quiz_html(quiz_id, selected_questions)
        
        with open(html_file, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        file_url = f"/static/quizzes/{quiz_id}.html"
        
        return QuizGenerateResponse(
            success=True,
            quiz_id=quiz_id,
            num_questions=len(selected_questions),
            html_file=str(html_file),
            file_url=file_url,
            message=f"Đã tạo quiz thành công với {len(selected_questions)} câu hỏi"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/list", response_model=QuizListResponse)
async def list_quizzes():
    """
    List all generated quizzes
    """
    try:
        quiz_folder = settings.QUIZ_DIR
        if not quiz_folder.exists():
            return QuizListResponse(quizzes=[], total=0)
        
        quiz_files = sorted(quiz_folder.glob("quiz_*.json"), reverse=True)
        
        quizzes = []
        for quiz_file in quiz_files[:20]:  # Limit to 20 recent quizzes
            try:
                with open(quiz_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    quizzes.append({
                        "id": data.get("id", quiz_file.stem),
                        "timestamp": data.get("timestamp", ""),
                        "num_questions": data.get("num_questions", 0),
                        "source_pdf": data.get("source_pdf", ""),
                        "html_url": f"/static/quizzes/{quiz_file.stem}.html"
                    })
            except:
                continue
        
        return QuizListResponse(quizzes=quizzes, total=len(quizzes))
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{quiz_id}")
async def get_quiz(quiz_id: str):
    """
    Get a specific quiz by ID
    """
    try:
        quiz_file = settings.QUIZ_DIR / f"{quiz_id}.json"
        if not quiz_file.exists():
            raise HTTPException(status_code=404, detail="Quiz không tồn tại")
        
        with open(quiz_file, 'r', encoding='utf-8') as f:
            quiz_data = json.load(f)
        
        return {
            "success": True,
            "quiz": quiz_data,
            "html_url": f"/static/quizzes/{quiz_id}.html"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{quiz_id}/download")
async def download_quiz_html(quiz_id: str):
    """
    Download quiz HTML file
    """
    html_file = settings.QUIZ_DIR / f"{quiz_id}.html"
    if not html_file.exists():
        raise HTTPException(status_code=404, detail="Quiz HTML không tồn tại")
    
    return FileResponse(
        path=str(html_file),
        filename=f"{quiz_id}.html",
        media_type="text/html"
    )


def generate_quiz_html(quiz_id: str, questions: list) -> str:
    """Generate standalone HTML quiz file"""
    html = f"""<!DOCTYPE html>
<html lang="vi">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Quiz {quiz_id}</title>
    <style>
        * {{ box-sizing: border-box; margin: 0; padding: 0; }}
        body {{ font-family: 'Segoe UI', Arial, sans-serif; 
               background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
               padding: 20px; min-height: 100vh; }}
        .container {{ max-width: 900px; margin: 0 auto; background: white; 
                     border-radius: 20px; box-shadow: 0 20px 60px rgba(0,0,0,0.3); }}
        .header {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
                  color: white; padding: 40px; text-align: center; border-radius: 20px 20px 0 0; }}
        .header h1 {{ font-size: 36px; margin-bottom: 10px; }}
        .content {{ padding: 40px; }}
        .student-form {{ background: #f8f9fa; padding: 30px; border-radius: 15px; margin-bottom: 30px; }}
        .form-group {{ margin-bottom: 20px; }}
        .form-group label {{ display: block; font-weight: bold; margin-bottom: 8px; color: #333; font-size: 16px; }}
        .form-group input {{ width: 100%; padding: 14px; border: 2px solid #ddd; border-radius: 10px; font-size: 16px; }}
        .form-group input:focus {{ border-color: #667eea; outline: none; }}
        .question-card {{ background: #fff; border: 2px solid #e0e0e0; border-radius: 15px; 
                         padding: 30px; margin-bottom: 25px; box-shadow: 0 2px 8px rgba(0,0,0,0.1); }}
        .question-text {{ font-size: 20px; font-weight: bold; color: #333; margin-bottom: 20px; }}
        .option-label {{ display: block; padding: 15px 20px; margin-bottom: 12px; 
                        border: 2px solid #ddd; border-radius: 10px; cursor: pointer; transition: all 0.3s; }}
        .option-label:hover {{ background: #f0f0f0; border-color: #667eea; }}
        .option-label input {{ margin-right: 12px; }}
        .submit-btn {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
                      color: white; padding: 18px 50px; font-size: 20px; border: none; 
                      border-radius: 12px; cursor: pointer; display: block; margin: 40px auto; font-weight: bold; }}
        .submit-btn:hover {{ transform: scale(1.05); }}
        .score-panel {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
                       color: white; padding: 30px; border-radius: 15px; text-align: center; 
                       margin: 30px 0; display: none; }}
        .score-panel h2 {{ font-size: 48px; margin: 20px 0; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>Bài Kiểm Tra Trực Tuyến</h1>
            <p style="font-size: 18px;">Quiz ID: {quiz_id}</p>
        </div>
        <div class="content">
            <div class="student-form" id="studentForm">
                <h3 style="margin-bottom: 25px; color: #667eea;">Thông Tin Sinh Viên</h3>
                <div class="form-group">
                    <label>Họ và Tên *</label>
                    <input type="text" id="studentName" placeholder="Nhập họ tên" required>
                </div>
                <div class="form-group">
                    <label>Mã Sinh Viên *</label>
                    <input type="text" id="studentId" placeholder="Nhập mã sinh viên" required>
                </div>
                <div class="form-group">
                    <label>Email *</label>
                    <input type="email" id="studentEmail" placeholder="example@email.com" required>
                </div>
                <button onclick="startQuiz()" class="submit-btn">Bắt Đầu Làm Bài</button>
            </div>
            
            <div id="quizContent" style="display: none;">
                <h3 style="color: #667eea; margin-bottom: 30px;">Câu Hỏi ({len(questions)} câu)</h3>
"""
    
    for i, q in enumerate(questions, start=1):
        html += f"""
                <div class="question-card">
                    <div class="question-text">Câu {i}: {q['question']}</div>
"""
        for letter, text in q['options'].items():
            html += f"""
                    <label class="option-label">
                        <input type="radio" name="q{i}" value="{letter}" data-correct="{q['correct']['letter']}">
                        {letter}. {text}
                    </label>
"""
        html += """
                </div>
"""
    
    html += f"""
                <button onclick="submitQuiz()" class="submit-btn">Nộp Bài</button>
                <div class="score-panel" id="scorePanel">
                    <h3>KẾT QUẢ</h3>
                    <h2 id="scoreText"></h2>
                    <p id="scoreDetail" style="font-size: 18px;"></p>
                </div>
            </div>
        </div>
    </div>
    
    <script>
        const totalQuestions = {len(questions)};
        
        function startQuiz() {{
            const name = document.getElementById('studentName').value.trim();
            const id = document.getElementById('studentId').value.trim();
            const email = document.getElementById('studentEmail').value.trim();
            
            if (!name || !id || !email) {{
                alert('Vui lòng điền đầy đủ thông tin!');
                return;
            }}
            
            document.getElementById('studentForm').style.display = 'none';
            document.getElementById('quizContent').style.display = 'block';
        }}
        
        function submitQuiz() {{
            let correctCount = 0;
            let answeredCount = 0;
            
            for (let i = 1; i <= totalQuestions; i++) {{
                const radios = document.getElementsByName('q' + i);
                let selected = null;
                let correct = null;
                
                for (let r of radios) {{
                    if (r.checked) selected = r.value;
                    correct = r.getAttribute('data-correct');
                }}
                
                if (selected !== null) {{
                    answeredCount++;
                    if (selected === correct) correctCount++;
                }}
            }}
            
            if (answeredCount < totalQuestions) {{
                if (!confirm('Bạn mới trả lời ' + answeredCount + '/' + totalQuestions + ' câu. Tiếp tục nộp bài?')) {{
                    return;
                }}
            }}
            
            const score = ((correctCount / totalQuestions) * 10).toFixed(1);
            document.getElementById('scoreText').textContent = score + ' điểm';
            document.getElementById('scoreDetail').textContent = 'Đúng ' + correctCount + '/' + totalQuestions + ' câu';
            document.getElementById('scorePanel').style.display = 'block';
            window.scrollTo({{ top: document.getElementById('scorePanel').offsetTop - 100, behavior: 'smooth' }});
        }}
    </script>
</body>
</html>"""
    
    return html
