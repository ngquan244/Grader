"""
Notebook execution tool for running Kaggle notebooks locally
"""
import json
import subprocess
import os
from typing import Optional, Type, Dict, Any, List
from pathlib import Path
from langchain.tools import BaseTool
from pydantic import BaseModel, Field
from .config import Config
from .logger import logger
import pyodbc

def check_role(role_required: str) -> bool:
    actual_role = getattr(Config, "ROLE", None)
    if (actual_role or "").lower() != role_required.lower():
        logger.warning(f"Access denied. Required role: {role_required}, actual role: {actual_role}")
        return False
    return True


SQL_SERVER_CONN_STR = (
    "Driver={ODBC Driver 17 for SQL Server};"
    "Server=244-NGUYEN-QUAN\\SQL2022;"
    "Database=Agent;"
    "Trusted_Connection=yes;"
    "Encrypt=no;"
)


class NotebookExecutorInput(BaseModel):
    """Input schema for notebook executor"""
    notebook_name: str = Field(
        description="Tên file notebook cần chạy (ví dụ: 'grading-timing-mark.ipynb')",
        default="grading-timing-mark.ipynb"
    )


class NotebookExecutorTool(BaseTool):
    """Tool để execute Jupyter notebook và lấy kết quả"""
    
    name: str = "execute_notebook"
    description: str = """
    Thực thi Jupyter notebook để chấm điểm bài thi trắc nghiệm.
    Sử dụng khi người dùng yêu cầu:
    - Chấm điểm bài thi
    - Chạy notebook grading
    - Xem kết quả chấm điểm
    - Execute grading notebook
    
    Tool này sẽ:
    1. Chạy notebook grading-timing-mark.ipynb
    2. Xử lý ảnh bài thi trong thư mục Filled-temp/
    3. Trả về kết quả chấm điểm dạng JSON với cấu trúc:
    
    {
        "student_id": "Mã số sinh viên (ví dụ: 22028171)",
        "name": "Họ và tên sinh viên",
        "email": "Email sinh viên",
        "student_code": "Mã sinh viên ngắn",
        "exam_code": "Mã đề thi",
        "total_questions": "Tổng số câu hỏi",
        "correct": "Số câu đúng",
        "wrong": "Số câu sai",
        "blank": "Số câu bỏ trống",
        "score": "Điểm số (thang 10)",
        "details": [{"question": 1, "student_answer": "A", "correct_answer": "A", "result": "correct"}, ...]
    }
    
    KHI TRẢ LỜI USER: Hãy trích xuất và hiển thị ĐẦY ĐỦ thông tin sinh viên (student_id, name, email) 
    cùng với kết quả chấm điểm (score, correct, wrong, blank).
    
    Input: Tên notebook (mặc định: grading-timing-mark.ipynb)
    """
    args_schema: Type[BaseModel] = NotebookExecutorInput
    
    def _run(self, notebook_name: str = "grading-timing-mark.ipynb") -> str:
        """Execute notebook and return results"""
        
        try:
            if not check_role("teacher"):
                actual_role = getattr(Config, "ROLE", None)
                return json.dumps({
                    "error": "Chỉ giáo viên mới có quyền yêu cầu chấm điểm",
                    "fatal": True,
                    "required_role": "teacher",
                    "your_role": actual_role,
                    "message": f"Bạn không có quyền thực hiện chức năng này. Yêu cầu quyền: teacher. Quyền hiện tại: {actual_role if actual_role else 'Không xác định'}"
                }, ensure_ascii=False, indent=2)

            logger.info(f" NotebookExecutorTool._run() called with notebook: {notebook_name}")
            kaggle_dir = Config.PROJECT_ROOT / "kaggle"
            notebook_path = kaggle_dir / notebook_name
            logger.info(f" Kaggle directory: {kaggle_dir}")
            logger.info(f" Notebook path: {notebook_path}")
            logger.info(f" Notebook exists: {notebook_path.exists()}")
            if not notebook_path.exists():
                error_msg = f"Notebook không tồn tại: {notebook_name}"
                logger.error(f" {error_msg}")
                return json.dumps({
                    "error": error_msg,
                    "available_notebooks": [f.name for f in kaggle_dir.glob("*.ipynb")]
                }, ensure_ascii=False, indent=2)
            # Execute notebook using papermill or jupyter nbconvert
            output_path = kaggle_dir / "output.ipynb"
            logger.info(f" Starting notebook execution with papermill...")
            logger.info(f" Output will be saved to: {output_path}")
            # Try using papermill first (better for programmatic execution)
            try:
                import papermill as pm
                logger.info(f" Papermill imported successfully")
                pm.execute_notebook(
                    str(notebook_path),
                    str(output_path),
                    kernel_name='python3'
                )
                logger.info(f" Notebook execution completed!")
                # Read results from output notebook
                result = self._extract_results(output_path)
                try:
                    if isinstance(result, dict) and "results" in result:
                        self._save_results_to_db(result["results"])
                except Exception as db_err:
                    logger.error(f" Error saving results to DB: {str(db_err)}")
                logger.info(f" Results extracted: {type(result)}")
                logger.info(f" Result keys: {result.keys() if isinstance(result, dict) else 'N/A'}")
            except ImportError:
                # Fallback to nbconvert
                cmd = [
                    "jupyter", "nbconvert",
                    "--to", "notebook",
                    "--execute",
                    str(notebook_path),
                    "--output", str(output_path)
                ]
                result = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    cwd=str(kaggle_dir)
                )
                if result.returncode != 0:
                    return json.dumps({
                        "error": "Lỗi khi chạy notebook",
                        "stderr": result.stderr,
                        "hint": "Kiểm tra dependencies và data files"
                    }, ensure_ascii=False, indent=2)
                result = self._extract_results(output_path)
            logger.info(f" Returning results to agent...")
            return json.dumps({
                "success": True,
                "notebook": notebook_name,
                "results": result,
                "output_path": str(output_path)
            }, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f" Exception in _run(): {str(e)}")
            logger.exception(e)
            return json.dumps({
                "error": str(e),
                "type": type(e).__name__,
                "hint": "Kiểm tra notebook syntax và dependencies"
            }, ensure_ascii=False, indent=2)
    
    def _extract_results(self, output_path: Path) -> Dict[str, Any]:
        """Extract results from executed notebook"""
        try:
            logger.info(f" Extracting results from: {output_path}")
            
            # Try to find final_result.json in project root directory
            result_file = Config.PROJECT_ROOT / "final_result.json"
            logger.info(f" Looking for result file: {result_file}")
            logger.info(f" Result file exists: {result_file.exists()}")
            
            if result_file.exists():
                logger.info(f" Reading result file...")
                with open(result_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                logger.info(f" Successfully loaded JSON from file")
                logger.info(f" Data keys: {data.keys()}")
                logger.info(f" Score: {data.get('score')}, Correct: {data.get('correct')}/{data.get('total_questions')}")
                return data
            
            logger.warning(f" Result file not found, parsing notebook outputs...")
            
            # If not found, parse notebook output cells to find JSON output
            with open(output_path, 'r', encoding='utf-8') as f:
                notebook_data = json.load(f)
            
            # Look for the last cell that outputs JSON with final_result
            for cell in reversed(notebook_data.get('cells', [])):
                if cell.get('cell_type') == 'code':
                    outputs = cell.get('outputs', [])
                    for output in outputs:
                        if output.get('output_type') == 'stream' and 'text' in output:
                            text = ''.join(output['text'])
                            # Try to parse JSON from output
                            if '{' in text and 'student_code' in text:
                                try:
                                    # Find JSON object in text
                                    start = text.find('{')
                                    end = text.rfind('}') + 1
                                    json_str = text[start:end]
                                    return json.loads(json_str)
                                except:
                                    pass
            
            return {
                "error": "Không tìm thấy kết quả chấm điểm",
                "note": "Notebook đã chạy nhưng không tìm thấy output JSON",
                "hint": "Kiểm tra xem notebook có xuất final_result.json không"
            }
            
        except Exception as e:
            logger.error(f" Error extracting results: {str(e)}")
            logger.exception(e)
            return {
                "error": f"Không thể đọc kết quả: {str(e)}"
            }
    
    async def _arun(self, notebook_name: str = "grading-timing-mark.ipynb") -> str:
        """Execute tool asynchronously"""
        return self._run(notebook_name)

    def _save_results_to_db(self, results: List[Dict[str, Any]]):
        """
        Lưu danh sách kết quả chấm điểm vào SQL Server
        KHÔNG ảnh hưởng logic chính
        """
        if not results:
            return

        conn = pyodbc.connect(SQL_SERVER_CONN_STR)
        cursor = conn.cursor()

        sql = """
        MERGE dbo.FinalExamResult AS target
        USING (
            SELECT ?, ?, ?, ?, ?, ?, ?, ?, ?, ?
        ) AS source (
            student_id, name, email, student_code, exam_code,
            total_questions, correct, wrong, blank, score
        )
        ON target.student_id = source.student_id
        AND target.exam_code = source.exam_code

        WHEN MATCHED THEN
            UPDATE SET
                name = source.name,
                email = source.email,
                student_code = source.student_code,
                total_questions = source.total_questions,
                correct = source.correct,
                wrong = source.wrong,
                blank = source.blank,
                score = source.score

        WHEN NOT MATCHED THEN
            INSERT (
                student_id, name, email, student_code, exam_code,
                total_questions, correct, wrong, blank, score
            )
            VALUES (
                source.student_id, source.name, source.email, source.student_code, source.exam_code,
                source.total_questions, source.correct, source.wrong, source.blank, source.score
            );
        """

        for r in results:
            cursor.execute(
                sql,
                r.get("student_id"),
                r.get("name"),
                r.get("email"),
                r.get("student_code"),
                r.get("exam_code"),
                int(r.get("total_questions", 0)),
                int(r.get("correct", 0)),
                int(r.get("wrong", 0)),
                int(r.get("blank", 0)),
                float(r.get("score", 0))
            )

        conn.commit()
        cursor.close()
        conn.close()


# Add to tools registry
def get_notebook_tool():
    """Factory function to create notebook executor tool"""
    return NotebookExecutorTool()



