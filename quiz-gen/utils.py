import re
import json
import pdfplumber
import random
import html

def extract_questions_from_pdf(pdf_path):
    all_text = ""
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            t = page.extract_text()
            if t:
                all_text += t + "\n"

    pattern_question = re.compile(
        r"Câu Hỏi\s+(\d+)\s+(Đúng|Sai)\s*\n"
        r"(.+?)\n"
        r"(a\..+?\n)"
        r"(b\..+?\n)"
        r"(c\..+?\n)"
        r"(d\..+?)\n"
        r"Câu trả lời đúng là:\s*(.+?)\n",
        re.DOTALL
    )

    questions = []

    for match in pattern_question.finditer(all_text):
        q_number = int(match.group(1))
        q_text = match.group(3).strip()

        option_a = match.group(4).strip()[2:].strip()
        option_b = match.group(5).strip()[2:].strip()
        option_c = match.group(6).strip()[2:].strip()
        option_d = match.group(7).strip()[2:].strip()

        options = {
            "A": option_a,
            "B": option_b,
            "C": option_c,
            "D": option_d
        }

        correct_text = match.group(8).strip()

        correct_letter = None
        for letter, content in options.items():
            if content.lower() in correct_text.lower() or correct_text.lower() in content.lower():
                correct_letter = letter
                break

        questions.append({
            "question_number": q_number,
            "question": q_text,
            "options": options,
            "correct": {
                "letter": correct_letter,
                "text": correct_text
            }
        })

    return questions


# ==================================
#  HTML RANDOM QUIZ GENERATOR
# ==================================

def generate_quiz(questions, n=10):
    selected = random.sample(questions, min(n, len(questions)))

    html_output = "<div style='font-family: Arial; font-size: 16px;'>"

    for idx, q in enumerate(selected, start=1):
        html_output += f"<div style='margin-bottom: 20px;'>"
        html_output += f"<b>Câu {idx}:</b> {html.escape(q['question'])}<br>"

        for letter, opt in q["options"].items():
            html_output += f"&nbsp;&nbsp; <b>{letter}.</b> {html.escape(opt)}<br>"

        html_output += "</div>"

    html_output += "</div>"

    return html_output
