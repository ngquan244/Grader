import gradio as gr
from utils import extract_questions_from_pdf
import random

# =========================
# Global cache
# =========================
questions_cache = []

# =========================
# Functions
# =========================
def handle_pdf_upload(file):
    global questions_cache
    if file is None:
        return " Chưa upload file PDF.", 0
    try:
        questions_cache = extract_questions_from_pdf(file.name)
        if not questions_cache:
            return "Không tìm thấy câu hỏi trong PDF.", 0
        return f"Đã tạo JSON thành công! Tổng số câu: {len(questions_cache)}", len(questions_cache)
    except Exception as e:
        return f"Lỗi khi đọc PDF: {str(e)}", 0

def generate_quiz_html(num_questions):
    global questions_cache
    if not questions_cache:
        return "<div style='color:red;'>Bạn cần upload PDF trước.</div>"

    quiz_list = random.sample(questions_cache, min(num_questions, len(questions_cache)))
    html_content = """
    <div style='font-family:Arial, sans-serif;'>
    """

    for i, q in enumerate(quiz_list, start=1):
        html_content += f"""
        <div style='margin-bottom:25px; padding:20px; border:1px solid #d0d0d0; border-radius:15px; background:#fdfdfd;
                        box-shadow:0 4px 8px rgba(0,0,0,0.05); transition: transform 0.1s;'>
            <b style='font-size:16px;'>Câu {i}:</b> <span style='font-size:15px;'>{q['question']}</span><br><br>
        """
        for letter, text in q['options'].items():
            html_content += f"""
            <label style='display:block; margin-bottom:6px; cursor:pointer;'>
                <input type="radio" name="q{i}" value="{letter}" style='margin-right:8px;'>
                {letter}. {text}
            </label>
            """
        html_content += "<div class='result' style='margin-top:8px; font-weight:bold;'></div></div>"

    html_content += "</div>"
    return html_content

# =========================
# Gradio UI
# =========================
with gr.Blocks(theme=gr.themes.Monochrome()) as demo:
    gr.Markdown("# Auto Quiz Generator\nUpload PDF → Tạo JSON → Sinh Quiz")

    with gr.Row():
        # Column 1: Upload PDF + JSON
        with gr.Column(scale=1, min_width=300):
            gr.Markdown("## Upload PDF & Tạo JSON")
            pdf_input = gr.File(label="Upload file PDF")
            btn_json = gr.Button("Tạo JSON", variant="primary")
            json_status = gr.Markdown()
            total_questions = gr.Number(label="Tổng số câu đã load", value=0, interactive=False)
            btn_json.click(fn=handle_pdf_upload, inputs=pdf_input, outputs=[json_status, total_questions])

        # Column 2: Sinh quiz + hiển thị
        with gr.Column(scale=2, min_width=600):
            gr.Markdown("## Sinh Quiz Ngẫu Nhiên")
            num_q = gr.Slider(5, 20, value=10, step=1, label="Số câu muốn tạo")
            btn_quiz = gr.Button("Tạo Quiz", variant="primary")
            quiz_output = gr.HTML()
            btn_quiz.click(fn=generate_quiz_html, inputs=num_q, outputs=quiz_output)

demo.launch()
