"""
Grading tool for the Teaching Assistant Grader.
Handles exam grading using SIFT/OpenCV image processing.
"""
import json
import os
from typing import Optional, Type, Dict, Any, List
from pathlib import Path
from langchain.tools import BaseTool
from pydantic import BaseModel, Field
from ..config import settings
from ..core.logger import logger
import pyodbc

# Import the grader module
from ..grader import create_processor, ExamProcessor


# Role management (imported from tools.py, duplicated here for standalone use)
ROLE_FILE = settings.PROJECT_ROOT / "role.txt"
_ROLE = None


def get_role():
    """Get current role from file, fallback to default"""
    global _ROLE
    if _ROLE is not None:
        return _ROLE
    if ROLE_FILE.exists():
        try:
            with open(ROLE_FILE, 'r', encoding='utf-8') as f:
                role = f.read().strip().upper()
                if role in ("STUDENT", "TEACHER"):
                    _ROLE = role
                    return role
        except Exception:
            pass
    _ROLE = "STUDENT"
    return _ROLE


def check_role(role_required: str) -> bool:
    actual_role = get_role()
    if (actual_role or "").lower() != role_required.lower():
        logger.warning(f"Access denied. Required role: {role_required}, actual role: {actual_role}")
        return False
    return True


SQL_SERVER_CONN_STR = settings.SQL_SERVER_CONN_STR


class GradingInput(BaseModel):
    """Input schema for grading tool"""
    notebook_name: str = Field(
        description="Tên file notebook cần chạy (không còn sử dụng, giữ để tương thích)",
        default="grading-timing-mark.ipynb"
    )


# Global processor instance
_processor: Optional[ExamProcessor] = None


def get_grader_processor() -> ExamProcessor:
    """Get or create the exam processor singleton"""
    global _processor
    if _processor is None:
        kaggle_dir = settings.PROJECT_ROOT / "kaggle"
        _processor = create_processor(
            template_path=str(kaggle_dir / "Template" / "temp.jpg"),
            student_json_path=str(kaggle_dir / "Input Materials" / "student_coords.json"),
            answer_json_path=str(kaggle_dir / "Input Materials" / "answer.json"),
            output_path=str(settings.PROJECT_ROOT / "final_result.json")
        )
    return _processor


class GradingTool(BaseTool):
    """Tool để chấm điểm bài thi trắc nghiệm"""
    
    name: str = "execute_notebook"
    description: str = """
    Chấm điểm bài thi trắc nghiệm từ ảnh đã upload.
    
    Sử dụng khi người dùng yêu cầu chấm điểm bài thi.
    
    CÁCH TRẢ LỜI (BẮT BUỘC):
    
    1. Nói ngắn gọn: "Đã chấm xong X bài thi"
    
    2. Hiển thị kết quả mỗi sinh viên theo format:
    
     **Kết quả chấm điểm**
    
    **Sinh viên: [Họ tên]**
    - Mã SV: [student_id]
    - Email: [email]
    - Mã đề: [exam_code]
    - **Điểm: [score]/10**
    - Đúng: [correct] | Sai: [wrong] | Bỏ trống: [blank]
    
    3. KHÔNG viết code Python
    4. KHÔNG hướng dẫn cách đọc JSON
    5. KHÔNG giải thích cách tính điểm
    """
    args_schema: Type[BaseModel] = GradingInput
    
    def _run(self, notebook_name: str = "grading-timing-mark.ipynb") -> str:
        """Execute grading using the refactored Python module"""
        try:
            if not check_role("teacher"):
                actual_role = get_role()
                return json.dumps({
                    "error": "Chỉ giáo viên mới có quyền yêu cầu chấm điểm",
                    "fatal": True,
                    "required_role": "teacher",
                    "your_role": actual_role,
                    "message": f"Bạn không có quyền thực hiện chức năng này. Yêu cầu quyền: teacher. Quyền hiện tại: {actual_role if actual_role else 'Không xác định'}"
                }, ensure_ascii=False, indent=2)

            # Update JSON from database
            try:
                self._update_json_from_db()
            except Exception as dbjson_err:
                logger.error(f"Lỗi khi cập nhật answer.json/student_coords.json từ DB: {str(dbjson_err)}")
                return json.dumps({
                    "error": "Lỗi khi cập nhật answer.json/student_coords.json từ DB",
                    "detail": str(dbjson_err)
                }, ensure_ascii=False, indent=2)

            logger.info("Starting grading using Python module (no notebook)")
            
            kaggle_dir = settings.PROJECT_ROOT / "kaggle"
            filled_dir = kaggle_dir / "Filled-temp"
            output_path = settings.PROJECT_ROOT / "final_result.json"
            
            # Check if images exist
            if not filled_dir.exists():
                return json.dumps({
                    "error": f"Thư mục Filled-temp không tồn tại: {filled_dir}",
                    "hint": "Vui lòng upload ảnh bài thi vào thư mục Filled-temp/"
                }, ensure_ascii=False, indent=2)
            
            # Get or create processor
            try:
                processor = get_grader_processor()
            except FileNotFoundError as e:
                return json.dumps({
                    "error": f"Không thể khởi tạo processor: {str(e)}",
                    "hint": "Kiểm tra template image và JSON files"
                }, ensure_ascii=False, indent=2)
            
            # Process all images
            logger.info(f"Processing images in: {filled_dir}")
            summary = processor.process_and_save(filled_dir, str(output_path))
            
            logger.info(f"Grading completed: {summary['successful']}/{summary['total_images']} successful")
            
            # Read results from output file
            result_data = self._read_results(output_path)
            
            # Save to database
            try:
                if isinstance(result_data, dict) and "results" in result_data:
                    self._save_results_to_db(result_data["results"])
            except Exception as db_err:
                logger.error(f"Error saving results to DB: {str(db_err)}")
            
            # Format output for agent - flatten and simplify
            graded_results = result_data.get("results", []) if isinstance(result_data, dict) else []
            
            # Build simple response for agent
            response = {
                "success": True,
                "message": f"Đã chấm điểm {summary['successful']}/{summary['total_images']} bài thi thành công",
                "total_images": summary["total_images"],
                "successful": summary["successful"],
                "failed": summary["failed"],
            }
            
            # Add individual results with simplified format
            students_results = []
            for r in graded_results:
                if r.get("success", False):
                    students_results.append({
                        "student_id": r.get("student_id"),
                        "name": r.get("name"),
                        "email": r.get("email"),
                        "exam_code": r.get("exam_code"),
                        "score": r.get("score"),
                        "correct": r.get("correct"),
                        "wrong": r.get("wrong"),
                        "blank": r.get("blank"),
                        "total_questions": r.get("total_questions")
                    })
                else:
                    students_results.append({
                        "image_name": r.get("image_name"),
                        "error": r.get("error"),
                        "suggestion": r.get("suggestion")
                    })
            
            response["students"] = students_results
            
            return json.dumps(response, ensure_ascii=False, indent=2)
            
        except Exception as e:
            logger.error(f"Exception in _run(): {str(e)}")
            logger.exception(e)
            return json.dumps({
                "error": str(e),
                "type": type(e).__name__,
                "hint": "Kiểm tra ảnh và dependencies"
            }, ensure_ascii=False, indent=2)
    
    def _read_results(self, result_path: Path) -> Dict[str, Any]:
        """Read results from JSON file"""
        try:
            if result_path.exists():
                with open(result_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            return {"error": "Không tìm thấy file kết quả"}
        except Exception as e:
            return {"error": f"Không thể đọc kết quả: {str(e)}"}
    
    def _update_json_from_db(self):
        """
        Lấy dữ liệu từ DB và ghi đè:
        - answer.json
        - student_coords.json
        """

        conn = pyodbc.connect(SQL_SERVER_CONN_STR)
        cursor = conn.cursor()

        cursor.execute("""
            SELECT id, exam_code, question_count
            FROM exams
        """)
        exams = cursor.fetchall()

        answer_json = []

        for exam in exams:
            exam_id = exam.id
            exam_code = exam.exam_code
            question_count = exam.question_count

            cursor.execute("""
                SELECT question_number, correct_answer
                FROM exam_answers
                WHERE exam_id = ?
                ORDER BY question_number ASC
            """, exam_id)

            answers = [
                {
                    "question": row.question_number,
                    "answer": row.correct_answer
                }
                for row in cursor.fetchall()
            ]

            answer_json.append({
                "exam_code": exam_code,
                "question_count": question_count,
                "answers": answers
            })

        cursor.execute("""
            SELECT student_id, email, full_name, student_code
            FROM students
        """)
        students = cursor.fetchall()

        student_coords_json = [
            {
                "student_id": stu.student_id,
                "name": stu.full_name,
                "email": stu.email,
                "coords": stu.student_code
            }
            for stu in students
        ]

        cursor.close()
        conn.close()

        kaggle_input_dir = settings.PROJECT_ROOT / "kaggle" / "Input Materials"
        kaggle_input_dir.mkdir(parents=True, exist_ok=True)

        answer_path = kaggle_input_dir / "answer.json"
        student_coords_path = kaggle_input_dir / "student_coords.json"

        with open(answer_path, "w", encoding="utf-8") as f:
            json.dump(answer_json, f, ensure_ascii=False, indent=2)

        with open(student_coords_path, "w", encoding="utf-8") as f:
            json.dump(student_coords_json, f, ensure_ascii=False, indent=2)

    async def _arun(self, notebook_name: str = "grading-timing-mark.ipynb") -> str:
        """Execute tool asynchronously"""
        return self._run(notebook_name)

    def _save_results_to_db(self, results):
        if not results:
            return

        conn = pyodbc.connect(SQL_SERVER_CONN_STR)
        cursor = conn.cursor()

        sql_check_student = """
        SELECT 1 FROM students WHERE student_id = ?
        """

        sql_result = """
        MERGE dbo.final_results AS target
        USING (
            SELECT ?, ?, ?, ?, ?, ?, ?
        ) AS source (
            student_id,
            exam_code,
            total_questions,
            correct,
            wrong,
            blank,
            score
        )
        ON target.student_id = source.student_id
        AND target.exam_code = source.exam_code

        WHEN MATCHED THEN
            UPDATE SET
                total_questions = source.total_questions,
                correct = source.correct,
                wrong = source.wrong,
                blank = source.blank,
                score = source.score

        WHEN NOT MATCHED THEN
            INSERT (
                student_id,
                exam_code,
                total_questions,
                correct,
                wrong,
                blank,
                score
            )
            VALUES (
                source.student_id,
                source.exam_code,
                source.total_questions,
                source.correct,
                source.wrong,
                source.blank,
                source.score
            );
        """

        for r in results:
            cursor.execute(sql_check_student, r["student_id"])
            if cursor.fetchone() is None:
                logger.error(
                    f"Skip result: student_id NOT FOUND → {r['student_id']}"
                )
                continue

            cursor.execute(
                sql_result,
                r["student_id"],
                r["exam_code"],
                int(r["total_questions"]),
                int(r["correct"]),
                int(r["wrong"]),
                int(r["blank"]),
                float(r["score"])
            )

        conn.commit()
        cursor.close()
        conn.close()


def get_grading_tool() -> GradingTool:
    """Factory function to create grading tool"""
    return GradingTool()


# Alias for backward compatibility
def get_notebook_tool() -> GradingTool:
    """Alias for get_grading_tool for backward compatibility"""
    return get_grading_tool()
