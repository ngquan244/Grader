import gradio as gr
import json
from pathlib import Path
from typing import Dict, List


def load_quiz_data(quiz_id: str) -> Dict:
    """Load quiz data from JSON file"""
    quiz_folder = Path(__file__).parent.parent / "quiz-gen" / "generated_quizzes"
    quiz_file = quiz_folder / f"{quiz_id}.json"
    
    if not quiz_file.exists():
        return None
    
    with open(quiz_file, 'r', encoding='utf-8') as f:
        return json.load(f)


def create_quiz_viewer():
    """Create a standalone quiz viewer interface"""
    
    def load_available_quizzes():
        """Get list of available quizzes"""
        quiz_folder = Path(__file__).parent.parent / "quiz-gen" / "generated_quizzes"
        if not quiz_folder.exists():
            return []
        
        quiz_files = sorted(quiz_folder.glob("quiz_*.json"), reverse=True)
        return [f.stem for f in quiz_files]
    
    def render_quiz(quiz_id, student_name, student_id, student_email):
        """Render quiz HTML based on quiz ID"""
        if not quiz_id:
            return "<div style='padding:20px; color:red;'> Vui lòng chọn quiz</div>", ""
        
        quiz_data = load_quiz_data(quiz_id)
        if not quiz_data:
            return "<div style='padding:20px; color:red;'> Không tìm thấy quiz</div>", ""
        
        questions = quiz_data['questions']
        
        # Generate HTML
        html = f"""
        <div style='font-family: Arial, sans-serif; max-width: 900px; margin: auto;'>
            <div style='background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
                        color: white; padding: 30px; border-radius: 15px; margin-bottom: 30px; text-align: center;'>
                <h1 style='margin: 0; font-size: 32px;'> Bài Kiểm Tra Trực Tuyến</h1>
                <p style='margin-top: 10px; font-size: 18px;'>Quiz ID: {quiz_id}</p>
            </div>
            
            <div style='background: #f8f9fa; padding: 25px; border-radius: 15px; margin-bottom: 30px;'>
                <h3 style='color: #667eea; margin-bottom: 15px;'> Thông Tin Sinh Viên</h3>
                <p style='margin: 5px 0;'><strong>Họ tên:</strong> {student_name or 'Chưa điền'}</p>
                <p style='margin: 5px 0;'><strong>MSSV:</strong> {student_id or 'Chưa điền'}</p>
                <p style='margin: 5px 0;'><strong>Email:</strong> {student_email or 'Chưa điền'}</p>
            </div>
            
            <h3 style='color: #667eea; margin-bottom: 20px;'> Các Câu Hỏi ({len(questions)} câu)</h3>
        """
        
        for i, q in enumerate(questions, start=1):
            html += f"""
            <div style='background: #fff; border: 2px solid #e0e0e0; border-radius: 15px; 
                        padding: 25px; margin-bottom: 25px; box-shadow: 0 2px 8px rgba(0,0,0,0.1);'>
                <div style='font-size: 18px; font-weight: bold; color: #333; margin-bottom: 15px;'>
                    Câu {i}: {q['question']}
                </div>
            """
            
            for letter, text in q['options'].items():
                html += f"""
                <label style='display: block; padding: 12px 15px; margin-bottom: 10px; 
                              border: 2px solid #ddd; border-radius: 10px; cursor: pointer;
                              transition: all 0.3s;' 
                       onmouseover='this.style.background="#f0f0f0"; this.style.borderColor="#667eea"'
                       onmouseout='this.style.background=""; this.style.borderColor="#ddd"'>
                    <input type='radio' name='q{i}' value='{letter}' 
                           data-correct='{q["correct"]["letter"]}' 
                           onclick='checkAnswer(this, {i})' 
                           style='margin-right: 10px;'>
                    {letter}. {text}
                </label>
                """
            
            html += f"""
                <div id='result{i}' style='margin-top: 15px; padding: 10px; border-radius: 8px; 
                                          font-weight: bold; display: none;'></div>
            </div>
            """
        
        html += """
        </div>
        
        <script>
        let answers = {};
        
        function checkAnswer(radio, questionNum) {
            const correct = radio.getAttribute('data-correct');
            const result = document.getElementById('result' + questionNum);
            const labels = radio.parentNode.parentNode.querySelectorAll('label');
            
            labels.forEach(l => {
                l.style.background = '';
                l.style.borderColor = '#ddd';
            });
            
            result.style.display = 'block';
            
            if(radio.value === correct) {
                radio.parentNode.style.background = '#d4edda';
                radio.parentNode.style.borderColor = '#28a745';
                result.innerHTML = '<span style="color:green;"> Đúng</span>';
                result.style.background = '#d4edda';
                answers[questionNum] = true;
            } else {
                radio.parentNode.style.background = '#f8d7da';
                radio.parentNode.style.borderColor = '#dc3545';
                result.innerHTML = '<span style="color:red;"> Sai. Đáp án đúng: ' + correct + '</span>';
                result.style.background = '#f8d7da';
                answers[questionNum] = false;
            }
        }
        </script>
        """
        
        # Calculate score info
        score_info = f"Quiz có {len(questions)} câu hỏi. Vui lòng làm bài và nhấn 'Nộp Bài' khi hoàn thành."
        return html, score_info
    
    def submit_quiz_result(quiz_id, student_name, student_id, student_email):
        """Submit quiz results"""
        if not student_name or not student_id or not student_email:
            return " Vui lòng điền đầy đủ thông tin sinh viên!"
        
        if not quiz_id:
            return " Không có quiz để nộp!"
        
        # Save result
        result_folder = Path(__file__).parent.parent / "quiz-gen" / "quiz_results"
        result_folder.mkdir(parents=True, exist_ok=True)
        
        import datetime
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        
        result_data = {
            "quiz_id": quiz_id,
            "student_name": student_name,
            "student_id": student_id,
            "student_email": student_email,
            "timestamp": timestamp,
            "submitted_at": datetime.datetime.now().isoformat()
        }
        
        result_file = result_folder / f"result_{student_id}_{timestamp}.json"
        with open(result_file, 'w', encoding='utf-8') as f:
            json.dump(result_data, f, ensure_ascii=False, indent=2)
        
        return f" Đã nộp bài thành công!\n\nThông tin:\n- Họ tên: {student_name}\n- MSSV: {student_id}\n- Email: {student_email}\n\nKết quả đã được lưu!"
    
    with gr.Blocks(title=" Quiz Trực Tuyến") as viewer:
        gr.Markdown("""
        #  Hệ Thống Làm Bài Kiểm Tra Trực Tuyến
        ### Vui lòng chọn quiz và điền đầy đủ thông tin trước khi làm bài
        """)
        
        with gr.Row():
            with gr.Column(scale=1):
                gr.Markdown("###  Chọn Quiz")
                quiz_selector = gr.Dropdown(
                    choices=load_available_quizzes(),
                    label="Chọn bài kiểm tra",
                    info="Chọn quiz mà giáo viên đã gửi cho bạn"
                )
                
                gr.Markdown("###  Thông Tin Sinh Viên")
                student_name = gr.Textbox(
                    label="Họ và Tên",
                    placeholder="Nhập họ tên đầy đủ"
                )
                student_id = gr.Textbox(
                    label="Mã Sinh Viên",
                    placeholder="Nhập MSSV"
                )
                student_email = gr.Textbox(
                    label="Email",
                    placeholder="email@example.com"
                )
                
                load_btn = gr.Button(" Tải Quiz", variant="primary", size="lg")
                submit_btn = gr.Button(" Nộp Bài", variant="secondary", size="lg")
                
                result_status = gr.Textbox(
                    label="Trạng thái",
                    interactive=False,
                    lines=6
                )
            
            with gr.Column(scale=2):
                quiz_display = gr.HTML(
                    value="<div style='padding: 40px; text-align: center; color: #999;'>Chọn quiz và nhấn 'Tải Quiz' để bắt đầu</div>"
                )
        
        # Event handlers
        load_btn.click(
            render_quiz,
            [quiz_selector, student_name, student_id, student_email],
            [quiz_display, result_status]
        )
        
        submit_btn.click(
            submit_quiz_result,
            [quiz_selector, student_name, student_id, student_email],
            [result_status]
        )
    
    return viewer


if __name__ == "__main__":
    demo = create_quiz_viewer()
    # Let Gradio automatically find an available port (starting from 7863 to avoid conflicts)
    import socket
    
    def find_free_port(start_port=7863):
        """Find next available port"""
        port = start_port
        while port < 8000:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                try:
                    s.bind(("127.0.0.1", port))
                    return port
                except OSError:
                    port += 1
        return None
    
    port = find_free_port()
    if port:
        demo.launch(share=True, server_name="0.0.0.0", server_port=port, show_error=True)
    else:
        print(" Không tìm thấy port khả dụng!")
        demo.launch(share=True, server_name="0.0.0.0", show_error=True)
