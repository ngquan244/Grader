import gradio as gr
import json
import shutil
import random
import sys
import datetime
from pathlib import Path
from typing import List, Dict
from .agent_graph import create_agent
from .config import Config
from .logger import ui_logger

# Import quiz-gen utilities
sys.path.append(str(Path(__file__).parent.parent / "quiz-gen"))
try:
    from utils import extract_questions_from_pdf
except ImportError:
    extract_questions_from_pdf = None


# GRADIO UI với LangGraph Agent
def create_ui():
    # Initialize agent
    agent = None
    
    def get_or_create_agent(model: str, max_iterations: int):
        """Lazy initialization of agent"""
        nonlocal agent
        if agent is None or agent.model_name != model or agent.max_iterations != max_iterations:
            agent = create_agent(model=model, max_iterations=max_iterations)
        return agent

    # Custom CSS - Monochrome Black Theme
    custom_css = """
    /* Global theme */
    .gradio-container {
        font-family: 'Inter', 'Segoe UI', system-ui, sans-serif !important;
        background: linear-gradient(135deg, #1a1a1a 0%, #0a0a0a 100%) !important;
    }
    
    /* Header styling */
    .header-box {
        background: linear-gradient(135deg, #2d2d2d 0%, #1a1a1a 100%);
        border: 1px solid #404040;
        border-radius: 12px;
        padding: 24px;
        margin-bottom: 20px;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.3);
    }
    
    h1 {
        color: #ffffff !important;
        font-weight: 700 !important;
        margin-bottom: 8px !important;
    }
    
    /* Button styling */
    .primary-btn {
        background: linear-gradient(135deg, #333333 0%, #1a1a1a 100%) !important;
        border: 1px solid #505050 !important;
        color: #ffffff !important;
        font-weight: 600 !important;
        transition: all 0.3s ease !important;
    }
    
    .primary-btn:hover {
        background: linear-gradient(135deg, #404040 0%, #2d2d2d 100%) !important;
        border-color: #606060 !important;
        transform: translateY(-1px);
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.4);
    }
    
    /* Chat styling */
    .chatbot {
        border: 1px solid #404040 !important;
        border-radius: 12px !important;
        background: #1a1a1a !important;
        box-shadow: 0 2px 8px rgba(0, 0, 0, 0.3) !important;
    }
    
    /* Input styling */
    textarea, input {
        background: #2d2d2d !important;
        border: 1px solid #404040 !important;
        color: #ffffff !important;
        border-radius: 8px !important;
    }
    
    textarea:focus, input:focus {
        border-color: #606060 !important;
        box-shadow: 0 0 0 2px rgba(96, 96, 96, 0.2) !important;
    }
    
    /* Label styling */
    label {
        color: #cccccc !important;
        font-weight: 600 !important;
        font-size: 0.9rem !important;
    }
    
    /* Card styling */
    .upload-card {
        background: #2d2d2d;
        border: 1px solid #404040;
        border-radius: 12px;
        padding: 16px;
        margin-bottom: 16px;
    }
    
    /* Status display */
    .status-display {
        background: #1a1a1a;
        border: 1px solid #333333;
        border-radius: 8px;
        padding: 12px;
        color: #cccccc;
        font-family: 'Monaco', 'Courier New', monospace;
        font-size: 0.85rem;
    }
    
    /* Dropdown styling */
    select {
        background: #2d2d2d !important;
        border: 1px solid #404040 !important;
        color: #ffffff !important;
        border-radius: 8px !important;
    }
    """
    
    with gr.Blocks(title="Teaching Assistant") as demo:
        # States
        chat_history = gr.State([])
        questions_cache = gr.State([])
        
        with gr.Row(elem_classes="header-box"):
            gr.Markdown("""
            # Teaching Assistant Grader
            
            Tự động chấm điểm bài thi trắc nghiệm với công nghệ Computer Vision & AI Agent
            """)

        # Configuration Row
        with gr.Row():
            with gr.Column(scale=2):
                model_selector = gr.Dropdown(
                    Config.AVAILABLE_MODELS,
                    value=Config.DEFAULT_MODEL,
                    label="AI Model",
                    info="Chọn model LLM để sử dụng"
                )
            with gr.Column(scale=1):
                max_iterations = gr.Slider(
                    minimum=5, maximum=20, value=Config.MAX_ITERATIONS, step=1,
                    label="Max Iterations",
                    info="Số bước suy luận tối đa"
                )
        
        # Tabs for different functions
        with gr.Tabs():
            # Tab 1: Grading System
            with gr.Tab("Chấm Điểm Tự Động"):
                # Main content: Chat bên trái, Upload bên phải
                with gr.Row():
                    # Chat Section - bên trái (nhỏ hơn)
                    with gr.Column(scale=3):
                        chatbox = gr.Chatbot(
                            height=400,
                            label="Hội Thoại",
                            avatar_images=(None, "🤖"),
                            show_label=True,
                            elem_classes="chatbot"
                        )
                    
                    # Image Upload Section - bên phải
                    with gr.Column(scale=2):
                        with gr.Group(elem_classes="upload-card"):
                            gr.Markdown("###  Upload Ảnh Bài Thi")
                            image_upload = gr.File(
                                label="Chọn ảnh bài thi (có thể chọn nhiều ảnh)",
                                file_count="multiple",
                                file_types=["image"],
                                type="filepath"
                            )
                            upload_status = gr.Textbox(
                                label="Trạng thái",
                                value=" Chưa upload ảnh nào",
                                interactive=False,
                                elem_classes="status-display"
                            )
                
                # Message Input Section
                with gr.Row():
                    msg = gr.Textbox(
                        placeholder=" Nhập câu hỏi hoặc yêu cầu... (VD: 'Chấm điểm bài thi')",
                        label="Tin nhắn",
                        scale=9,
                        show_label=False
                    )
                    with gr.Column(scale=1):
                        submit_btn = gr.Button(" Gửi", variant="primary", elem_classes="primary-btn")
                        clear_btn = gr.Button(" Xóa", elem_classes="primary-btn")

                # Stats Display
                with gr.Row():
                    iterations_display = gr.Textbox(
                        label=" Số bước thực thi",
                        value="0",
                        interactive=False,
                        scale=1,
                        elem_classes="status-display"
                    )
                    tools_display = gr.Textbox(
                        label=" Công cụ đã sử dụng",
                        value="Chưa có",
                        interactive=False,
                        scale=2,
                        elem_classes="status-display"
                    )

                # Instructions
                with gr.Accordion(" Hướng Dẫn Sử Dụng", open=False):
                    gr.Markdown("""
                    ### Quy trình chấm điểm:
                    
                    **Bước 1:** Upload ảnh bài thi
                    - Click vào khu vực upload và chọn ảnh (JPG, PNG)
                    - Có thể chọn nhiều ảnh cùng lúc
                    - Đợi thông báo " Đã upload thành công"
                    
                    **Bước 2:** Yêu cầu chấm điểm
                    - Nhập: "chấm điểm", "chấm bài thi", "cho tôi kết quả"
                    - Agent sẽ tự động xử lý và trả về kết quả
                    
                    ### Yêu cầu về ảnh:
                     Chụp rõ nét, không bị mờ
                     Ánh sáng đủ, không bị lóa
                     Không nghiêng quá 15 độ
                     Timing marks (chấm đen ở viền) phải rõ ràng
                    
                    ### Lỗi thường gặp:
                     **Timing marks không đủ**: Ảnh mờ hoặc ánh sáng kém
                     **Không warp được**: Ảnh nghiêng quá nhiều
                     **Cells không đủ**: Chất lượng ảnh không đạt
                    
                    → **Giải pháp**: Chụp lại ảnh với điều kiện tốt hơn
                    """)
            
            # Tab 2: Quiz Generator
            with gr.Tab(" Tạo Đề Thi Quiz"):
                gr.Markdown("""
                ###  Auto Quiz Generator
                Upload file PDF đề thi → Hệ thống tự động trích xuất câu hỏi → Tạo quiz trực tuyến
                """)
                
                with gr.Row():
                    # Left column: PDF Upload
                    with gr.Column(scale=2):
                        gr.Markdown("####  Upload PDF Đề Thi")
                        pdf_input = gr.File(
                            label="Chọn file PDF chứa đề thi",
                            file_types=[".pdf"],
                            type="filepath"
                        )
                        btn_extract = gr.Button(" Trích Xuất Câu Hỏi", variant="primary", size="lg")
                        pdf_status = gr.Markdown(" Chưa upload PDF")
                        total_questions_display = gr.Number(
                            label=" Tổng số câu đã trích xuất",
                            value=0,
                            interactive=False
                        )
                        
                        with gr.Accordion(" Hướng Dẫn Định Dạng PDF", open=False):
                            gr.Markdown("""
                            **Định dạng yêu cầu:**
                            ```
                            Câu Hỏi 1 Đúng/Sai
                            Nội dung câu hỏi...
                            a. Đáp án A
                            b. Đáp án B
                            c. Đáp án C
                            d. Đáp án D
                            Câu trả lời đúng là: [Nội dung đáp án đúng]
                            ```
                            
                            **Lưu ý:**
                            - PDF phải có cấu trúc rõ ràng
                            - Mỗi câu hỏi phải có đủ 4 đáp án (a, b, c, d)
                            - Câu trả lời đúng phải được ghi rõ
                            """)
                    
                    # Right column: Quiz Display
                    with gr.Column(scale=3):
                        gr.Markdown("####  Tạo Quiz Ngẫu Nhiên")
                        num_questions_slider = gr.Slider(
                            minimum=5,
                            maximum=30,
                            value=10,
                            step=1,
                            label=" Số câu hỏi trong quiz",
                            info="Chọn số lượng câu hỏi muốn tạo"
                        )
                        btn_generate_quiz = gr.Button("✨ Tạo Quiz & Tạo Link", variant="primary", size="lg")
                        
                        quiz_file_path = gr.Textbox(
                            label="📎 Đường dẫn file Quiz",
                            placeholder="File quiz sẽ được tạo sau khi bạn nhấn nút trên",
                            interactive=False
                        )
                        
                        quiz_output = gr.HTML(
                            label=" Xem Trước Quiz",
                            value="<div style='padding:40px; text-align:center; color:#666;'>Chưa có quiz. Hãy upload PDF và tạo quiz.</div>"
                        )
                        
                        gr.Markdown("---")
                        gr.Markdown("###  Quiz Online - URL Live")
                        
                        quiz_link_display = gr.HTML(
                            value="<div style='padding: 20px; background: #f0f0f0; border-radius: 10px; text-align: center; color: #666;'>Link sẽ hiển thị sau khi tạo quiz...</div>",
                            label=" Link Quiz Online"
                        )
                        
                        with gr.Row():
                            btn_start_quiz_server = gr.Button(" Tạo File Quiz HTML", variant="primary", size="lg")
                        
                        quiz_server_status = gr.Textbox(
                            label=" Trạng thái",
                            value="Chưa tạo",
                            interactive=False,
                            lines=4
                        )
                        
                        gr.Markdown("""
                        <div style='background:#d4edda; padding:20px; border-radius:10px; border-left:5px solid #28a745;'>
                            <h4 style='margin-top:0; color:#155724;'> Cách Sử Dụng:</h4>
                            <ol style='color:#155724;'>
                                <li><strong>Tạo quiz</strong> từ PDF (như bình thường)</li>
                                <li>Nhấn <strong>" Tạo File Quiz HTML"</strong></li>
                                <li><strong>Copy đường dẫn</strong> file HTML từ ô "Link Quiz Online"</li>
                                <li>Dán vào trình duyệt hoặc <strong>gửi file cho sinh viên</strong></li>
                                <li>Sinh viên mở file HTML → Điền thông tin → Làm bài</li>
                                <li>Kết quả tự động lưu vào <code>quiz-gen/quiz_results/</code></li>
                            </ol>
                            <p style='color:#155724; margin-top:15px; font-weight:bold;'>
                                 Link có hiệu lực 72 giờ |  Mỗi quiz có link riêng biệt
                            </p>
                        </div>
                        """)

        # Instructions (moved outside tabs, applies to both)

        def handle_image_upload(files):
            """Handle image upload and save to kaggle/Filled-temp/"""
            if not files:
                return "Chưa upload ảnh nào"
            
            try:
                # Create destination folder
                dest_folder = Config.PROJECT_ROOT / "kaggle" / "Filled-temp"
                dest_folder.mkdir(parents=True, exist_ok=True)
                
                # Clear existing images
                for existing_file in dest_folder.glob("*"):
                    if existing_file.is_file():
                        existing_file.unlink()
                
                # Copy uploaded images
                uploaded_count = 0
                uploaded_files = []
                
                for file_path in files:
                    if file_path:
                        file_name = Path(file_path).name
                        dest_path = dest_folder / file_name
                        shutil.copy2(file_path, dest_path)
                        uploaded_count += 1
                        uploaded_files.append(file_name)
                        ui_logger.info(f"Uploaded: {file_name}")
                
                status_msg = f" Đã upload {uploaded_count} ảnh:\n" + "\n".join(f"  - {f}" for f in uploaded_files)
                ui_logger.info(f"Upload completed: {uploaded_count} images")
                return status_msg
                
            except Exception as e:
                error_msg = f" Lỗi upload: {str(e)}"
                ui_logger.error(error_msg)
                return error_msg
        
        def user_submit(user_message: str, history: List, model: str, max_iter: int):
            """Handle user message submission"""
            if not user_message.strip():
                return "", history, history, "0", "None"

            ui_logger.info(f"User query: {user_message[:100]}")
            
            # Get or create agent with current settings
            current_agent = get_or_create_agent(model, max_iter)
            
            # Convert Gradio history to agent format
            agent_history = []
            for msg in history:
                agent_history.append({
                    "role": msg["role"],
                    "content": msg["content"]
                })
            
            # Invoke agent
            result = current_agent.invoke(user_message, agent_history)
            
            # Update history
            history.append({"role": "user", "content": user_message})
            history.append({"role": "assistant", "content": result["response"]})
            
            # Format tools used
            tools_used = result.get("tools_used", [])
            if tools_used:
                tools_str = ", ".join([f"🔧 {t['tool']}" for t in tools_used])
            else:
                tools_str = "Không sử dụng công cụ nào"
            
            return "", history, history, str(result.get("iterations", 0)), tools_str

        def reset_chat():
            """Reset chat history"""
            return [], [], "0", "Chưa có"
        
        # Quiz HTML Generator
        def start_quiz_server_for_latest():
            """Generate standalone HTML quiz file and return local path"""
            # Get latest quiz
            quiz_folder = Config.PROJECT_ROOT / "quiz-gen" / "generated_quizzes"
            if not quiz_folder.exists():
                return " Chưa có quiz nào được tạo!", ""
            
            quiz_files = sorted(quiz_folder.glob("quiz_*.json"), reverse=True)
            if not quiz_files:
                return " Chưa có quiz nào được tạo! Hãy tạo quiz trước.", ""
            
            latest_quiz_file = quiz_files[0]
            latest_quiz_id = latest_quiz_file.stem
            
            try:
                # Load quiz data
                with open(latest_quiz_file, 'r', encoding='utf-8') as f:
                    quiz_data = json.load(f)
                
                questions = quiz_data['questions']
                
                # Generate standalone HTML
                html_path = quiz_folder / f"{latest_quiz_id}.html"
                
                with open(html_path, 'w', encoding='utf-8') as f:
                    f.write(generate_standalone_quiz_html(latest_quiz_id, questions))
                
                ui_logger.info(f"Đã tạo file HTML: {html_path}")
                
                # Return both status and file path
                status = f" Quiz HTML đã sẵn sàng!\n\n Quiz: {latest_quiz_id}\n Số câu: {len(questions)}\n\n Mở file HTML bằng trình duyệt để làm bài"
                file_url = f"file:///{str(html_path).replace(chr(92), '/')}"
                
                # Create clickable HTML link
                link_html = f"""
                <div style="padding: 25px; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
                            border-radius: 15px; text-align: center;">
                    <h3 style="color: white; margin-bottom: 15px;"> Link Quiz HTML</h3>
                    <a href="{file_url}" target="_blank" 
                       style="display: inline-block; padding: 15px 40px; background: white; 
                              color: #667eea; text-decoration: none; border-radius: 10px; 
                              font-weight: bold; font-size: 16px; box-shadow: 0 4px 15px rgba(0,0,0,0.2);
                              transition: all 0.3s;"
                       onmouseover="this.style.transform='scale(1.05)'; this.style.boxShadow='0 6px 20px rgba(0,0,0,0.3)';"
                       onmouseout="this.style.transform='scale(1)'; this.style.boxShadow='0 4px 15px rgba(0,0,0,0.2)';">
                         Mở Quiz HTML
                    </a>
                    <div style="margin-top: 20px; padding: 15px; background: rgba(255,255,255,0.2); 
                                border-radius: 10px;">
                        <p style="color: white; font-size: 14px; margin-bottom: 8px;">
                            <strong>File:</strong> {html_path.name}
                        </p>
                        <p style="color: white; font-size: 12px; word-break: break-all;">
                            {file_url}
                        </p>
                    </div>
                    <div style="margin-top: 15px; padding: 12px; background: rgba(255,255,255,0.15); 
                                border-radius: 8px;">
                        <p style="color: white; font-size: 13px;">
                             <strong>Cách chia sẻ:</strong> Gửi file <code style="background: rgba(0,0,0,0.2); 
                            padding: 2px 6px; border-radius: 4px;">{html_path.name}</code> cho sinh viên
                        </p>
                    </div>
                </div>
                """
                
                return status, link_html
                
            except Exception as e:
                ui_logger.error(f"Lỗi tạo HTML: {str(e)}")
                error_html = f"""
                <div style="padding: 20px; background: #f8d7da; border-radius: 10px; border-left: 5px solid #dc3545;">
                    <h4 style="color: #721c24; margin-bottom: 10px;">❌ Lỗi tạo quiz</h4>
                    <p style="color: #721c24;">{str(e)}</p>
                </div>
                """
                return f" Lỗi: {str(e)}", error_html
        
        def generate_standalone_quiz_html(quiz_id, questions):
            """Generate complete standalone HTML file"""
            html = f"""<!DOCTYPE html>
<html lang=\"vi\">
<head>
    <meta charset=\"UTF-8\">
    <meta name=\"viewport\" content=\"width=device-width, initial-scale=1.0\">
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
    <div class=\"container\">\n        <div class=\"header\">\n            <h1> Bài Kiểm Tra Trực Tuyến</h1>\n            <p style=\"font-size: 18px; margin-top: 10px;\">Quiz ID: {quiz_id}</p>\n        </div>\n        <div class=\"content\">\n            <div class=\"student-form\" id=\"studentForm\">\n                <h3 style=\"margin-bottom: 25px; color: #667eea; font-size: 24px;\">Thông Tin Sinh Viên</h3>\n                <div class=\"form-group\">\n                    <label>Họ và Tên *</label>\n                    <input type=\"text\" id=\"studentName\" placeholder=\"Nhập họ tên đầy đủ\" required>\n                </div>\n                <div class=\"form-group\">\n                    <label>Mã Sinh Viên *</label>\n                    <input type=\"text\" id=\"studentId\" placeholder=\"Nhập mã sinh viên\" required>\n                </div>\n                <div class=\"form-group\">\n                    <label>Email *</label>\n                    <input type=\"email\" id=\"studentEmail\" placeholder=\"example@email.com\" required>\n                </div>\n                <button onclick=\"startQuiz()\" class=\"submit-btn\">Bắt Đầu Làm Bài</button>\n            </div>\n            <div class=\"info-display\" id=\"infoDisplay\"></div>\n            <div id=\"quizContent\" style=\"display: none;\">\n                <h3 style=\"color: #667eea; margin-bottom: 30px; font-size: 24px;\"> Câu Hỏi ({len(questions)} câu)</h3>\n"""
            
            # Add questions
            for i, q in enumerate(questions, start=1):
                html += f"""
                <div class=\"question-card\">\n                    <div class=\"question-text\">Câu {i}: {q['question']}</div>\n"""
                for letter, text in q['options'].items():
                    html += f"""
                    <label class=\"option-label\">\n                        <input type=\"radio\" name=\"q{i}\" value=\"{letter}\" 
                               data-correct=\"{q['correct']['letter']}\" 
                               onclick=\"checkAnswer(this, {i})\">\n                        {letter}. {text}\n                    </label>\n"""
                html += f"""
                    <div id=\"result{i}\" class=\"result\"></div>\n                </div>\n"""
            
            html += f"""
                <button onclick=\"submitQuiz()\" class=\"submit-btn\"> Nộp Bài</button>\n                <div class=\"score-panel\" id=\"scorePanel\">\n                    <h3> KẾT QUẢ</h3>\n                    <h2 id=\"scoreText\"></h2>\n                    <p id=\"scoreDetail\" style=\"font-size: 18px; margin-top: 10px;\"></p>\n                </div>\n            </div>\n        </div>\n    </div>\n    <script>\n        let studentInfo = {{}};\n        let answers = {{}};\n        const totalQuestions = {len(questions)};\n        function startQuiz() {{\n            const name = document.getElementById('studentName').value.trim();\n            const id = document.getElementById('studentId').value.trim();\n            const email = document.getElementById('studentEmail').value.trim();\n            if (!name || !id || !email) {{\n                alert(' Vui lòng điền đầy đủ thông tin!');\n                return;\n            }}\n            studentInfo = {{ name, id, email }};\n            document.getElementById('studentForm').style.display = 'none';\n            document.getElementById('infoDisplay').style.display = 'block';\n            document.getElementById('infoDisplay').innerHTML = `\n                <h4 style=\"margin-bottom: 15px; color: #667eea;\">Thông tin của bạn:</h4>\n                <p><strong>Họ tên:</strong> ${{name}}</p>\n                <p><strong>MSSV:</strong> ${{id}}</p>\n                <p><strong>Email:</strong> ${{email}}</p>\n            `;\n            document.getElementById('quizContent').style.display = 'block';\n            window.scrollTo({{ top: 0, behavior: 'smooth' }});\n        }}\n        function checkAnswer(radio, questionNum) {{\n            const correct = radio.getAttribute('data-correct');\n            const result = document.getElementById('result' + questionNum);\n            const labels = radio.parentNode.parentNode.querySelectorAll('.option-label');\n            labels.forEach(l => {{\n                l.style.background = '';\n                l.style.borderColor = '#ddd';\n            }});\n            // Không hiển thị kết quả đúng/sai cho học sinh\n            result.style.display = 'none';\n            if(radio.value === correct) {{\n                radio.parentNode.style.background = '#d4edda';\n                radio.parentNode.style.borderColor = '#28a745';\n                answers[questionNum] = true;\n            }} else {{\n                radio.parentNode.style.background = '#f8d7da';\n                radio.parentNode.style.borderColor = '#dc3545';\n                answers[questionNum] = false;\n            }}\n        }}\n        function submitQuiz() {{\n            let correctCount = 0;\n            let answeredCount = 0;\n            // Duyệt qua tất cả các câu hỏi\n            for (let i = 1; i <= totalQuestions; i++) {{\n                const radios = document.getElementsByName('q' + i);\n                let selected = null;\n                let correct = null;\n                for (let r of radios) {{\n                    if (r.checked) selected = r.value;\n                    correct = r.getAttribute('data-correct');\n                }}\n                if (selected !== null) {{\n                    answeredCount++;\n                    if (selected === correct) correctCount++;\n                }}\n            }}\n            if (answeredCount < totalQuestions) {{\n                if (!confirm(`Bạn mới trả lời ${{answeredCount}}/${{totalQuestions}} câu. Bạn có chắc muốn nộp bài?`)) {{\n                    return;\n                }}\n            }}\n            // Tính điểm trên thang 10\n            const score = ((correctCount / totalQuestions) * 10).toFixed(1);\n            document.getElementById('scoreText').textContent = score + ' điểm';\n            document.getElementById('scoreDetail').textContent = \n                `Đúng ${{correctCount}}/${{totalQuestions}} câu`;\n            document.getElementById('scorePanel').style.display = 'block';\n            window.scrollTo({{ top: document.getElementById('scorePanel').offsetTop - 100, behavior: 'smooth' }});\n            console.log('Kết quả:', {{\n                ...studentInfo,\n                score: score,\n                correct: correctCount,\n                total: totalQuestions,\n                quizId: '{quiz_id}'\n            }});\n        }}\n    </script>\n</body>\n</html>"""
            
            return html
        
        def handle_pdf_upload_quiz(file, cache):
            """Handle PDF upload for quiz generation"""
            if file is None:
                return " Chưa upload file PDF.", 0, cache
            if extract_questions_from_pdf is None:
                return " Module quiz-gen chưa được cài đặt.", 0, cache
            try:
                questions = extract_questions_from_pdf(file.name)
                if not questions:
                    return "Không tìm thấy câu hỏi trong PDF.", 0, []
                return f" Đã tạo thành công! Tổng số câu: {len(questions)}", len(questions), questions
            except Exception as e:
                return f" Lỗi khi đọc PDF: {str(e)}", 0, []
        
        # Student Quiz Functions
        # Quiz Generator Functions (for teachers)
        def handle_pdf_upload_quiz(file, cache):
            """Handle PDF upload for quiz generation"""
            if file is None:
                return " Chưa upload file PDF.", 0, cache
            if extract_questions_from_pdf is None:
                return " Module quiz-gen chưa được cài đặt.", 0, cache
            try:
                questions = extract_questions_from_pdf(file.name)
                if not questions:
                    return "Không tìm thấy câu hỏi trong PDF.", 0, []
                return f" Đã tạo thành công! Tổng số câu: {len(questions)}", len(questions), questions
            except Exception as e:
                return f" Lỗi khi đọc PDF: {str(e)}", 0, []
        
        def generate_quiz_link(num_questions, cache):
            """Generate quiz HTML content and save quiz data for sharing"""
            if not cache:
                return "<div style='color:red; padding:20px;'>❌ Bạn cần upload PDF trước.</div>", ""
            
            quiz_list = random.sample(cache, min(num_questions, len(cache)))
            
            # Save quiz data to JSON file for web access
            import datetime
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            quiz_folder = Config.PROJECT_ROOT / "quiz-gen" / "generated_quizzes"
            quiz_folder.mkdir(parents=True, exist_ok=True)
            
            quiz_id = f"quiz_{timestamp}"
            quiz_data = {
                "id": quiz_id,
                "timestamp": timestamp,
                "questions": quiz_list,
                "num_questions": len(quiz_list)
            }
            
            # Save quiz data
            quiz_json_file = quiz_folder / f"{quiz_id}.json"
            with open(quiz_json_file, 'w', encoding='utf-8') as f:
                json.dump(quiz_data, f, ensure_ascii=False, indent=2)
            
            # Generate full HTML file with student info form
            full_html = """<!DOCTYPE html>
<html lang="vi">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title> Bài Kiểm Tra Trực Tuyến</title>
    <style>
        * { box-sizing: border-box; margin: 0; padding: 0; }
        body { font-family: 'Segoe UI', Arial, sans-serif; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
               padding: 20px; min-height: 100vh; }
        .container { max-width: 900px; margin: 0 auto; background: white; border-radius: 20px; 
                     box-shadow: 0 20px 60px rgba(0,0,0,0.3); overflow: hidden; }
        .header { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; 
                  padding: 30px; text-align: center; }
        .header h1 { font-size: 32px; margin-bottom: 10px; }
        .content { padding: 40px; }
        .student-form { background: #f8f9fa; padding: 25px; border-radius: 15px; margin-bottom: 30px; }
        .form-group { margin-bottom: 15px; }
        .form-group label { display: block; font-weight: bold; margin-bottom: 5px; color: #333; }
        .form-group input { width: 100%; padding: 12px; border: 2px solid #ddd; border-radius: 8px; 
                            font-size: 16px; transition: border-color 0.3s; }
        .form-group input:focus { border-color: #667eea; outline: none; }
        .question-card { background: #fdfdfd; border: 2px solid #e0e0e0; border-radius: 15px; 
                         padding: 25px; margin-bottom: 25px; transition: transform 0.2s; }
        .question-card:hover { transform: translateY(-2px); box-shadow: 0 8px 16px rgba(0,0,0,0.1); }
        .question-text { font-size: 18px; font-weight: bold; color: #333; margin-bottom: 15px; }
        .option-label { display: block; padding: 12px 15px; margin-bottom: 10px; border: 2px solid #ddd; 
                        border-radius: 10px; cursor: pointer; transition: all 0.3s; }
        .option-label:hover { background: #f0f0f0; border-color: #667eea; }
        .option-label input { margin-right: 10px; }
        .result { margin-top: 15px; padding: 10px; border-radius: 8px; font-weight: bold; }
        .submit-btn { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; 
                      padding: 15px 40px; font-size: 18px; border: none; border-radius: 10px; 
                      cursor: pointer; display: block; margin: 30px auto; transition: transform 0.2s; }
        .submit-btn:hover { transform: scale(1.05); }
        .score-display { background: #d4edda; padding: 20px; border-radius: 10px; text-align: center; 
                         font-size: 24px; font-weight: bold; display: none; margin-top: 20px; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1> Bài Kiểm Tra Trực Tuyến</h1>
            <p>Vui lòng điền thông tin và hoàn thành bài kiểm tra</p>
        </div>
        <div class="content">
            <div class="student-form">
                <h3 style="margin-bottom: 20px; color: #667eea;">👤 Thông Tin Sinh Viên</h3>
                <div class="form-group">
                    <label>Họ và Tên:</label>
                    <input type="text" id="studentName" placeholder="Nhập họ tên đầy đủ" required>
                </div>
                <div class="form-group">
                    <label>Mã Sinh Viên:</label>
                    <input type="text" id="studentId" placeholder="Nhập mã sinh viên" required>
                </div>
                <div class="form-group">
                    <label>Email:</label>
                    <input type="email" id="studentEmail" placeholder="example@email.com" required>
                </div>
            </div>
            
            <h3 style="margin-bottom: 20px; color: #667eea;"> Các Câu Hỏi</h3>
"""
            
            # Add questions
            for i, q in enumerate(quiz_list, start=1):
                full_html += f"""
            <div class="question-card">
                <div class="question-text">Câu {i}: {q['question']}</div>
"""
                for letter, text in q['options'].items():
                    full_html += f"""
                <label class="option-label">
                    <input type="radio" name="q{i}" value="{letter}" data-correct="{q['correct']['letter']}" 
                           onclick="checkAnswer(this, {i})">
                    {letter}. {text}
                </label>
"""
                full_html += """
                <div class="result" id="result{0}"></div>
            </div>
""".format(i)
            
            # Add JavaScript and closing tags
            full_html += """
            <button class="submit-btn" onclick="submitQuiz()">📤 Nộp Bài</button>
            <div class="score-display" id="scoreDisplay"></div>
        </div>
    </div>
    
    <script>
        let answers = {};
        
        function checkAnswer(radio, questionNum) {
            const correct = radio.getAttribute('data-correct');
            const result = document.getElementById('result' + questionNum);
            const labels = radio.parentNode.parentNode.querySelectorAll('.option-label');
            
            labels.forEach(l => {
                l.style.background = '';
                l.style.borderColor = '#ddd';
            });
            
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
        
        function submitQuiz() {
            const name = document.getElementById('studentName').value;
            const id = document.getElementById('studentId').value;
            const email = document.getElementById('studentEmail').value;
            
            if(!name || !id || !email) {
                alert('Vui lòng điền đầy đủ thông tin sinh viên!');
                return;
            }
            
            const totalQuestions = """ + str(len(quiz_list)) + """;
            const correctAnswers = Object.values(answers).filter(x => x).length;
            const score = (correctAnswers / totalQuestions * 10).toFixed(2);
            
            const scoreDisplay = document.getElementById('scoreDisplay');
            scoreDisplay.innerHTML = `
                <div style="margin-bottom: 15px;">
                    <strong>${name}</strong> (${id})<br>
                    Email: ${email}
                </div>
                <div style="font-size: 28px; color: ${score >= 5 ? '#28a745' : '#dc3545'}">
                    Điểm: ${score}/10
                </div>
                <div style="margin-top: 10px; font-size: 18px;">
                    Đúng: ${correctAnswers}/${totalQuestions} câu
                </div>
            `;
            scoreDisplay.style.display = 'block';
            
            // Save to localStorage
            const result = {
                name: name,
                studentId: id,
                email: email,
                score: score,
                correct: correctAnswers,
                total: totalQuestions,
                timestamp: new Date().toISOString()
            };
            
            let results = JSON.parse(localStorage.getItem('quizResults') || '[]');
            results.push(result);
            localStorage.setItem('quizResults', JSON.stringify(results));
            
            alert(' Đã nộp bài thành công! Điểm của bạn: ' + score + '/10');
        }
    </script>
</body>
</html>"""
            
            # Save to file
            import datetime
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            quiz_folder = Config.PROJECT_ROOT / "quiz-gen" / "generated_quizzes"
            quiz_folder.mkdir(parents=True, exist_ok=True)
            
            quiz_file = quiz_folder / f"quiz_{timestamp}.html"
            with open(quiz_file, 'w', encoding='utf-8') as f:
                f.write(full_html)
            
            # Create preview HTML for display  
            preview_html = f"""
            <div style='padding:25px; background:linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
                        border-radius:15px; margin-bottom:20px; color:white;'>
                <h2 style='margin:0 0 20px 0;'> Quiz Đã Được Tạo Thành Công!</h2>
                <div style='background:rgba(255,255,255,0.2); padding:20px; border-radius:10px; margin-bottom:15px;'>
                    <p style='margin:5px 0; font-size:16px;'><strong> Quiz ID:</strong> {quiz_id}</p>
                    <p style='margin:5px 0; font-size:16px;'><strong> Số câu:</strong> {len(quiz_list)} câu</p>
                    <p style='margin:5px 0; font-size:16px;'><strong> Thời gian tạo:</strong> {timestamp}</p>
                </div>
            </div>
            
            <div style='padding:20px; background:#f8f9fa; border-radius:10px;'>
                <h4 style='color:#333; margin-top:0;'> Xem Trước Quiz</h4>
                <iframe src="file:///{quiz_file}" width="100%" height="600px" 
                        style="border:2px solid #ddd; border-radius:10px; background:white;"></iframe>
            </div>
            """
            
            # Generate quiz link - just use current Gradio app with query parameter
            # The quiz will be accessible via the main app's share link + ?quiz=quiz_id
            quiz_link_text = f" Quiz ID: {quiz_id}\n\n Để truy cập online:\n1. Chia sẻ link Gradio share của app này\n2. Thêm ?__theme=light vào cuối URL\n3. Sinh viên vào Tab 'Làm Quiz Online'\n4. Chọn quiz {quiz_id} và làm bài\n\n💾 File HTML: {quiz_file}"
            
            return preview_html, quiz_link_text

        # Event handlers - Grading System
        image_upload.change(
            handle_image_upload,
            [image_upload],
            [upload_status]
        )
        
        msg.submit(
            user_submit,
            [msg, chat_history, model_selector, max_iterations],
            [msg, chatbox, chat_history, iterations_display, tools_display]
        )
        submit_btn.click(
            user_submit,
            [msg, chat_history, model_selector, max_iterations],
            [msg, chatbox, chat_history, iterations_display, tools_display]
        )
        clear_btn.click(
            reset_chat,
            None,
            [chatbox, chat_history, iterations_display, tools_display]
        )
        
        # Event handlers - Quiz Generator
        btn_extract.click(
            handle_pdf_upload_quiz,
            [pdf_input, questions_cache],
            [pdf_status, total_questions_display, questions_cache]
        )
        
        btn_generate_quiz.click(
            generate_quiz_link,
            [num_questions_slider, questions_cache],
            [quiz_output, quiz_link_display]
        )
        
        btn_start_quiz_server.click(
            start_quiz_server_for_latest,
            [],
            [quiz_server_status, quiz_link_display]
        )

    return demo


if __name__ == "__main__":
    demo = create_ui()
    demo.launch(share=True)