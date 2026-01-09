"""
Quiz Service
Handles quiz generation and management
"""
import json
import random
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime

from backend.config import settings
from backend.core import Messages, ForbiddenException, NotFoundException, BadRequestException
from backend.utils import ensure_directory, generate_timestamp_id

logger = logging.getLogger(__name__)

# Try to import quiz extraction utility
try:
    import sys
    sys.path.append(str(settings.PROJECT_ROOT / "quiz-gen"))
    from utils import extract_questions_from_pdf
    QUIZ_GEN_AVAILABLE = True
except ImportError:
    extract_questions_from_pdf = None
    QUIZ_GEN_AVAILABLE = False


class QuizService:
    """Service for quiz generation and management"""
    
    def __init__(self):
        self.quiz_dir = settings.QUIZ_DIR
        self.data_dir = settings.DATA_DIR / "quiz"
        ensure_directory(self.quiz_dir)
        ensure_directory(self.data_dir)
    
    def extract_questions(self, pdf_path: str) -> List[Dict[str, Any]]:
        """Extract questions from a PDF file"""
        if not QUIZ_GEN_AVAILABLE:
            raise BadRequestException(Messages.QUIZ_GEN_NOT_INSTALLED)
        
        questions = extract_questions_from_pdf(pdf_path)
        if not questions:
            raise BadRequestException(Messages.NO_QUESTIONS_FOUND)
        
        return questions
    
    def generate_quiz(
        self,
        num_questions: int,
        source_pdf: Optional[str] = None
    ) -> Dict[str, Any]:
        """Generate a quiz from PDF questions"""
        if not QUIZ_GEN_AVAILABLE:
            raise BadRequestException(Messages.QUIZ_GEN_NOT_INSTALLED)
        
        # Find PDF file
        pdf_files = list(self.data_dir.glob("*.pdf"))
        if not pdf_files:
            raise NotFoundException("PDF file")
        
        pdf_file = pdf_files[0]
        
        # Extract and select questions
        questions = extract_questions_from_pdf(str(pdf_file))
        if not questions:
            raise BadRequestException(Messages.NO_QUESTIONS_FOUND)
        
        selected = random.sample(questions, min(num_questions, len(questions)))
        
        # Create quiz data
        quiz_id = generate_timestamp_id("quiz")
        quiz_data = {
            "id": quiz_id,
            "timestamp": datetime.now().isoformat(),
            "source_pdf": pdf_file.name,
            "questions": selected,
            "num_questions": len(selected)
        }
        
        # Save quiz JSON
        json_file = self.quiz_dir / f"{quiz_id}.json"
        with open(json_file, 'w', encoding='utf-8') as f:
            json.dump(quiz_data, f, ensure_ascii=False, indent=2)
        
        # Generate HTML
        html_file = self.quiz_dir / f"{quiz_id}.html"
        html_content = self._generate_html(quiz_id, selected)
        with open(html_file, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        logger.info(f"Quiz generated: {quiz_id} with {len(selected)} questions")
        
        return {
            "quiz_id": quiz_id,
            "num_questions": len(selected),
            "html_file": str(html_file),
            "file_url": f"/static/quizzes/{quiz_id}.html"
        }
    
    def list_quizzes(self, limit: int = 20) -> List[Dict[str, Any]]:
        """List all generated quizzes"""
        quiz_files = sorted(self.quiz_dir.glob("quiz_*.json"), reverse=True)
        
        quizzes = []
        for quiz_file in quiz_files[:limit]:
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
            except Exception as e:
                logger.warning(f"Failed to read quiz file {quiz_file}: {e}")
        
        return quizzes
    
    def get_quiz(self, quiz_id: str) -> Dict[str, Any]:
        """Get a specific quiz by ID"""
        quiz_file = self.quiz_dir / f"{quiz_id}.json"
        if not quiz_file.exists():
            raise NotFoundException("Quiz", quiz_id)
        
        with open(quiz_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    def delete_quiz(self, quiz_id: str) -> bool:
        """Delete a quiz by ID"""
        quiz_file = self.quiz_dir / f"{quiz_id}.json"
        html_file = self.quiz_dir / f"{quiz_id}.html"
        
        if not quiz_file.exists():
            raise NotFoundException("Quiz", quiz_id)
        
        # Delete JSON file
        quiz_file.unlink()
        
        # Delete HTML file if exists
        if html_file.exists():
            html_file.unlink()
        
        logger.info(f"Quiz deleted: {quiz_id}")
        return True
    
    def _generate_html(self, quiz_id: str, questions: List[Dict]) -> str:
        """Generate standalone HTML quiz file"""
        return f"""<!DOCTYPE html>
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
        .form-group label {{ display: block; font-weight: bold; margin-bottom: 8px; color: #333; }}
        .form-group input {{ width: 100%; padding: 14px; border: 2px solid #ddd; border-radius: 10px; font-size: 16px; }}
        .form-group input:focus {{ border-color: #667eea; outline: none; }}
        .question-card {{ background: #fff; border: 2px solid #e0e0e0; border-radius: 15px; 
                         padding: 30px; margin-bottom: 25px; box-shadow: 0 2px 8px rgba(0,0,0,0.1); }}
        .question-text {{ font-size: 18px; font-weight: bold; color: #333; margin-bottom: 20px; }}
        .option-label {{ display: block; padding: 15px 20px; margin-bottom: 12px; 
                        border: 2px solid #ddd; border-radius: 10px; cursor: pointer; transition: all 0.3s; }}
        .option-label:hover {{ background: #f0f0f0; border-color: #667eea; }}
        .option-label input {{ margin-right: 12px; }}
        .option-label.correct {{ background: #d4edda; border-color: #28a745; }}
        .option-label.incorrect {{ background: #f8d7da; border-color: #dc3545; }}
        .answer-explanation {{ margin-top: 15px; padding: 15px; background: #e7f3ff; 
                              border-left: 4px solid #2196F3; border-radius: 5px; display: none; }}
        .answer-explanation.show {{ display: block; }}
        .answer-explanation strong {{ color: #2196F3; }}
        .submit-btn {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
                      color: white; padding: 18px 50px; font-size: 20px; border: none; 
                      border-radius: 12px; cursor: pointer; display: block; margin: 40px auto; font-weight: bold; }}
        .submit-btn:hover {{ transform: scale(1.05); }}
        .submit-btn:disabled {{ opacity: 0.6; cursor: not-allowed; transform: none; }}
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
                {''.join(self._generate_question_html(i, q) for i, q in enumerate(questions, 1))}
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
            if (!name || !id || !email) {{ alert('Vui lòng điền đầy đủ thông tin!'); return; }}
            document.getElementById('studentForm').style.display = 'none';
            document.getElementById('quizContent').style.display = 'block';
        }}
        function submitQuiz() {{
            let correct = 0, answered = 0;
            for (let i = 1; i <= totalQuestions; i++) {{
                const radios = document.getElementsByName('q' + i);
                let selected = null, correctAns = null;
                for (let r of radios) {{
                    if (r.checked) selected = r.value;
                    correctAns = r.getAttribute('data-correct');
                }}
                if (selected !== null) {{ answered++; if (selected === correctAns) correct++; }}
            }}
            if (answered < totalQuestions && !confirm('Bạn mới trả lời ' + answered + '/' + totalQuestions + ' câu. Tiếp tục?')) return;
            
            // Show correct answers
            for (let i = 1; i <= totalQuestions; i++) {{
                const radios = document.getElementsByName('q' + i);
                let correctAns = null;
                for (let r of radios) {{
                    correctAns = r.getAttribute('data-correct');
                    r.disabled = true; // Disable all radios
                    const label = r.parentElement;
                    // Highlight correct answer
                    if (r.value === correctAns) {{
                        label.classList.add('correct');
                    }}
                    // Highlight user's incorrect answer
                    if (r.checked && r.value !== correctAns) {{
                        label.classList.add('incorrect');
                    }}
                }}
                // Show answer explanation
                const explanation = document.getElementById('answer-' + i);
                if (explanation) explanation.classList.add('show');
            }}
            
            const score = ((correct / totalQuestions) * 10).toFixed(1);
            document.getElementById('scoreText').textContent = score + ' điểm';
            document.getElementById('scoreDetail').textContent = 'Đúng ' + correct + '/' + totalQuestions + ' câu';
            document.getElementById('scorePanel').style.display = 'block';
            
            // Disable submit button
            const submitBtn = document.querySelector('button[onclick="submitQuiz()"]');
            if (submitBtn) {{
                submitBtn.disabled = true;
                submitBtn.textContent = 'Đã Nộp Bài';
            }}
            
            window.scrollTo({{ top: 0, behavior: 'smooth' }});
        }}
    </script>
</body>
</html>"""
    
    def _generate_question_html(self, num: int, question: Dict) -> str:
        """Generate HTML for a single question"""
        options_html = ""
        for letter, text in question['options'].items():
            options_html += f"""
                <label class="option-label">
                    <input type="radio" name="q{num}" value="{letter}" data-correct="{question['correct']['letter']}">
                    {letter}. {text}
                </label>"""
        
        # Get correct answer text
        correct_letter = question['correct']['letter']
        correct_text = question['options'].get(correct_letter, '')
        correct_explanation = question['correct'].get('explanation', '')
        
        answer_html = f"""
            <div class="answer-explanation" id="answer-{num}">
                <strong>✓ Đáp án đúng: {correct_letter}. {correct_text}</strong>
                {f'<br><br>{correct_explanation}' if correct_explanation else ''}
            </div>"""
        
        return f"""
            <div class="question-card">
                <div class="question-text">Câu {num}: {question['question']}</div>
                {options_html}
                {answer_html}
            </div>"""


# Singleton instance
quiz_service = QuizService()
