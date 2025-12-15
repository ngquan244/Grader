"""
Tools definition for LangGraph Agent
Định nghĩa các tools theo format của LangChain
"""
import json
import sys
import datetime
import random
from pathlib import Path
from typing import Optional, Type
from langchain.tools import BaseTool
from pydantic import BaseModel, Field
from .notebook_tool import get_notebook_tool
from .config import Config

# Import quiz-gen utilities
sys.path.append(str(Path(__file__).parent.parent / "quiz-gen"))
try:
    from utils import extract_questions_from_pdf
except ImportError:
    extract_questions_from_pdf = None


# Tool Input Schema for Calculator
class CalculatorInput(BaseModel):
    """Input schema for calculator tool"""
    expression: str = Field(description="Biểu thức toán học cần tính, ví dụ: '2 + 2' hoặc '10 * 5'")


class CalculatorTool(BaseTool):
    """Tool để tính toán các phép toán đơn giản"""
    
    name: str = "calculator"
    description: str = """
    Công cụ tính toán toán học.
    Sử dụng khi người dùng muốn tính toán số học.
    Input: biểu thức toán học (string)
    Ví dụ: '2 + 2', '10 * 5 + 3', '100 / 4'
    """
    args_schema: Type[BaseModel] = CalculatorInput
    
    def _run(self, expression: str) -> str:
        """Execute calculator"""
        try:
            # Chỉ cho phép các ký tự an toàn
            allowed_chars = set("0123456789+-*/().% ")
            if not all(c in allowed_chars for c in expression):
                return json.dumps({
                    "error": "Biểu thức chứa ký tự không hợp lệ",
                    "allowed": "Chỉ được dùng: 0-9, +, -, *, /, (, ), %, space"
                }, ensure_ascii=False)
            
            result = eval(expression)
            return json.dumps({
                "expression": expression,
                "result": result
            }, ensure_ascii=False)
        except Exception as e:
            return json.dumps({
                "error": str(e),
                "expression": expression
            }, ensure_ascii=False)
    
    async def _arun(self, expression: str) -> str:
        """Execute tool asynchronously"""
        return self._run(expression)


# Tool Input Schema for Quiz Generator
class QuizGeneratorInput(BaseModel):
    """Input schema for quiz generator tool"""
    num_questions: int = Field(
        default=10,
        description="Số lượng câu hỏi cần tạo cho quiz (mặc định 10)"
    )


class QuizGeneratorTool(BaseTool):
    """Tool để tự động tạo quiz từ file PDF trong thư mục data/quiz/"""
    
    name: str = "quiz_generator"
    description: str = """
    Công cụ tạo bài kiểm tra trực tuyến (quiz) từ đề thi PDF có sẵn.
    
    Chức năng:
    - Tự động đọc file PDF đề thi từ thư mục data/quiz/
    - Trích xuất các câu hỏi trắc nghiệm
    - Tạo file HTML standalone cho sinh viên làm bài
    - Trả về đường dẫn file HTML để chia sẻ
    
    Input: số lượng câu hỏi muốn tạo (mặc định 10)
    
    Sử dụng khi người dùng yêu cầu:
    - "Tạo quiz", "Tạo đề thi trắc nghiệm"
    - "Tạo bài kiểm tra online"
    - "Gen quiz từ PDF"
    - "Tạo quiz 15 câu", "Tạo quiz 20 câu"
    """
    args_schema: Type[BaseModel] = QuizGeneratorInput
    
    def _run(self, num_questions: int = 10) -> str:
        """Execute quiz generator"""
        try:
            if extract_questions_from_pdf is None:
                return json.dumps({
                    "error": "Module quiz-gen chưa được cài đặt",
                    "status": "failed"
                }, ensure_ascii=False)
            
            # Find PDF file in data/quiz/
            quiz_folder = Config.PROJECT_ROOT / "data" / "quiz"
            if not quiz_folder.exists():
                return json.dumps({
                    "error": "Thư mục data/quiz/ không tồn tại",
                    "status": "failed"
                }, ensure_ascii=False)
            
            pdf_files = list(quiz_folder.glob("*.pdf"))
            if not pdf_files:
                return json.dumps({
                    "error": "Không tìm thấy file PDF trong data/quiz/",
                    "status": "failed"
                }, ensure_ascii=False)
            
            # Use the first PDF file found
            pdf_file = pdf_files[0]
            
            # Extract questions
            questions = extract_questions_from_pdf(str(pdf_file))
            if not questions:
                return json.dumps({
                    "error": "Không tìm thấy câu hỏi trong PDF",
                    "pdf_file": pdf_file.name,
                    "status": "failed"
                }, ensure_ascii=False)
            
            # Randomly select questions
            selected_questions = random.sample(questions, min(num_questions, len(questions)))
            
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
            output_folder = Config.PROJECT_ROOT / "quiz-gen" / "generated_quizzes"
            output_folder.mkdir(parents=True, exist_ok=True)
            
            quiz_json_file = output_folder / f"{quiz_id}.json"
            with open(quiz_json_file, 'w', encoding='utf-8') as f:
                json.dump(quiz_data, f, ensure_ascii=False, indent=2)
            
            # Generate HTML file
            html_file = output_folder / f"{quiz_id}.html"
            html_content = self._generate_html(quiz_id, selected_questions)
            
            with open(html_file, 'w', encoding='utf-8') as f:
                f.write(html_content)
            
            # Return success with file path
            file_url = f"file:///{str(html_file).replace(chr(92), '/')}"
            
            # Create a simple summary message
            summary = f"""
 ĐÃ TẠO QUIZ THÀNH CÔNG!

 Thông tin quiz:
   - Quiz ID: {quiz_id}
   - Nguồn: {pdf_file.name}
   - Số câu hỏi: {len(selected_questions)}/{len(questions)} câu

 File đã tạo:
   - HTML: {html_file.name}
   - JSON: {quiz_json_file.name}

 LINK QUIZ (Copy và dán vào trình duyệt):
   {file_url}

 Cách chia sẻ:
   1. Copy link trên và gửi cho sinh viên
   2. Hoặc gửi file: {html_file}
   3. Sinh viên mở bằng trình duyệt bất kỳ
   
 Lưu ý: File HTML hoạt động offline, không cần internet!
"""
            
            return json.dumps({
                "status": "success",
                "quiz_id": quiz_id,
                "source_pdf": pdf_file.name,
                "num_questions": len(selected_questions),
                "total_available": len(questions),
                "html_file": str(html_file),
                "file_url": file_url,
                "summary": summary,
                "message": summary
            }, ensure_ascii=False, indent=2)
            
        except Exception as e:
            return json.dumps({
                "error": str(e),
                "status": "failed"
            }, ensure_ascii=False)
    
    def _generate_html(self, quiz_id: str, questions: list) -> str:
        """Generate standalone HTML quiz file"""
        html = f"""<!DOCTYPE html>
<html lang="vi">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title> {quiz_id}</title>
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
        .form-group label {{ display: block; font-weight: bold; margin-bottom: 8px; 
                            color: #333; font-size: 16px; }}
        .form-group input {{ width: 100%; padding: 14px; border: 2px solid #ddd; 
                            border-radius: 10px; font-size: 16px; transition: all 0.3s; }}
        .form-group input:focus {{ border-color: #667eea; outline: none; box-shadow: 0 0 0 3px rgba(102,126,234,0.1); }}
        .question-card {{ background: #fff; border: 2px solid #e0e0e0; border-radius: 15px; 
                         padding: 30px; margin-bottom: 25px; box-shadow: 0 2px 8px rgba(0,0,0,0.1); }}
        .question-text {{ font-size: 20px; font-weight: bold; color: #333; margin-bottom: 20px; }}
        .option-label {{ display: block; padding: 15px 20px; margin-bottom: 12px; 
                        border: 2px solid #ddd; border-radius: 10px; cursor: pointer; 
                        transition: all 0.3s; font-size: 16px; }}
        .option-label:hover {{ background: #f0f0f0; border-color: #667eea; transform: translateX(5px); }}
        .option-label input {{ margin-right: 12px; cursor: pointer; }}
        .result {{ margin-top: 20px; padding: 15px; border-radius: 10px; font-weight: bold; 
                  font-size: 16px; display: none; }}
        .score-panel {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
                       color: white; padding: 30px; border-radius: 15px; text-align: center; 
                       margin: 30px 0; display: none; }}
        .score-panel h2 {{ font-size: 48px; margin: 20px 0; }}
        .submit-btn {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
                      color: white; padding: 18px 50px; font-size: 20px; border: none; 
                      border-radius: 12px; cursor: pointer; display: block; margin: 40px auto; 
                      font-weight: bold; transition: all 0.3s; box-shadow: 0 4px 15px rgba(102,126,234,0.4); }}
        .submit-btn:hover {{ transform: scale(1.05); box-shadow: 0 6px 20px rgba(102,126,234,0.6); }}
        .info-display {{ background: #e3f2fd; padding: 20px; border-radius: 10px; 
                        margin-bottom: 30px; display: none; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1> Bài Kiểm Tra Trực Tuyến</h1>
            <p style="font-size: 18px; margin-top: 10px;">Quiz ID: {quiz_id}</p>
        </div>
        <div class="content">
            <div class="student-form" id="studentForm">
                <h3 style="margin-bottom: 25px; color: #667eea; font-size: 24px;"> Thông Tin Sinh Viên</h3>
                <div class="form-group">
                    <label>Họ và Tên *</label>
                    <input type="text" id="studentName" placeholder="Nhập họ tên đầy đủ" required>
                </div>
                <div class="form-group">
                    <label>Mã Sinh Viên *</label>
                    <input type="text" id="studentId" placeholder="Nhập mã sinh viên" required>
                </div>
                <div class="form-group">
                    <label>Email *</label>
                    <input type="email" id="studentEmail" placeholder="example@email.com" required>
                </div>
                <button onclick="startQuiz()" class="submit-btn"> Bắt Đầu Làm Bài</button>
            </div>
            
            <div class="info-display" id="infoDisplay"></div>
            
            <div id="quizContent" style="display: none;">
                <h3 style="color: #667eea; margin-bottom: 30px; font-size: 24px;"> Câu Hỏi ({len(questions)} câu)</h3>
"""
        
        # Add questions
        for i, q in enumerate(questions, start=1):
            html += f"""
                <div class="question-card">
                    <div class="question-text">Câu {i}: {q['question']}</div>
"""
            for letter, text in q['options'].items():
                html += f"""
                    <label class="option-label">
                        <input type="radio" name="q{i}" value="{letter}" 
                               data-correct="{q['correct']['letter']}" 
                               onclick="checkAnswer(this, {i})">
                        {letter}. {text}
                    </label>
"""
            html += f"""
                    <div id="result{i}" class="result"></div>
                </div>
"""
        
        html += f"""
                <button onclick="submitQuiz()" class="submit-btn"> Nộp Bài</button>
                <div class="score-panel" id="scorePanel">
                    <h3> KẾT QUẢ</h3>
                    <h2 id="scoreText"></h2>
                    <p id="scoreDetail" style="font-size: 18px; margin-top: 10px;"></p>
                </div>
            </div>
        </div>
    </div>
    
    <script>
        let studentInfo = {{}};
        let answers = {{}};
        const totalQuestions = {len(questions)};
        
        function startQuiz() {{
            const name = document.getElementById('studentName').value.trim();
            const id = document.getElementById('studentId').value.trim();
            const email = document.getElementById('studentEmail').value.trim();
            
            if (!name || !id || !email) {{
                alert(' Vui lòng điền đầy đủ thông tin!');
                return;
            }}
            
            studentInfo = {{ name, id, email }};
            
            document.getElementById('studentForm').style.display = 'none';
            document.getElementById('infoDisplay').style.display = 'block';
            document.getElementById('infoDisplay').innerHTML = `
                <h4 style="margin-bottom: 15px; color: #667eea;">👤 Thông tin của bạn:</h4>
                <p><strong>Họ tên:</strong> ${{name}}</p>
                <p><strong>MSSV:</strong> ${{id}}</p>
                <p><strong>Email:</strong> ${{email}}</p>
            `;
            document.getElementById('quizContent').style.display = 'block';
            
            window.scrollTo({{ top: 0, behavior: 'smooth' }});
        }}
        
        function checkAnswer(radio, questionNum) {{
            const correct = radio.getAttribute('data-correct');
            const result = document.getElementById('result' + questionNum);
            const labels = radio.parentNode.parentNode.querySelectorAll('.option-label');
            labels.forEach(l => {{
                l.style.background = '';
                l.style.borderColor = '#ddd';
            }});
            // Không hiển thị kết quả đúng/sai cho học sinh
            result.style.display = 'none';
            if(radio.value === correct) {{
                radio.parentNode.style.background = '#d4edda';
                radio.parentNode.style.borderColor = '#28a745';
                answers[questionNum] = true;
            }} else {{
                radio.parentNode.style.background = '#f8d7da';
                radio.parentNode.style.borderColor = '#dc3545';
                answers[questionNum] = false;
            }}
        }}
        
        function submitQuiz() {{
            let correctCount = 0;
            let answeredCount = 0;
            // Duyệt qua tất cả các câu hỏi
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
                if (!confirm(`Bạn mới trả lời ${{answeredCount}}/${{totalQuestions}} câu. Bạn có chắc muốn nộp bài?`)) {{
                    return;
                }}
            }}
            // Tính điểm trên thang 10
            const score = ((correctCount / totalQuestions) * 10).toFixed(1);
            document.getElementById('scoreText').textContent = score + ' điểm';
            document.getElementById('scoreDetail').textContent = 
                `Đúng ${{correctCount}}/${{totalQuestions}} câu`;
            document.getElementById('scorePanel').style.display = 'block';
            window.scrollTo({{ top: document.getElementById('scorePanel').offsetTop - 100, behavior: 'smooth' }});
            console.log('Kết quả:', {{
                ...studentInfo,
                score: score,
                correct: correctCount,
                total: totalQuestions,
                quizId: '{quiz_id}'
            }});
        }}
    </script>
</body>
</html>"""
        
        return html
    
    async def _arun(self, num_questions: int = 10) -> str:
        """Execute tool asynchronously"""
        return self._run(num_questions)


# Registry of all available tools
def get_all_tools() -> list[BaseTool]:
    """Trả về danh sách tất cả các tools có sẵn"""
    return [
        get_notebook_tool(),
        CalculatorTool(),
        QuizGeneratorTool(),
    ]


def get_tool_by_name(tool_name: str) -> Optional[BaseTool]:
    """Lấy tool theo tên"""
    tools = get_all_tools()
    for tool in tools:
        if tool.name == tool_name:
            return tool
    return None
