"""
Grading Engine Module
Handles score calculation and result generation
"""
import json
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field, asdict
from pathlib import Path
import logging

logger = logging.getLogger(__name__)


@dataclass
class QuestionResult:
    """Result for a single question"""
    question: int
    student_answer: Optional[Any]
    correct_answer: str
    result: str  # "correct", "wrong", "blank", "multi"


@dataclass
class ExamResult:
    """Complete exam result"""
    student_id: Optional[str] = None
    name: str = "Unknown"
    email: Optional[str] = None
    student_code: str = ""
    exam_code: str = ""
    total_questions: int = 0
    correct: int = 0
    wrong: int = 0
    blank: int = 0
    score: float = 0.0
    image_name: str = ""
    success: bool = True
    error: Optional[str] = None
    suggestion: Optional[str] = None
    details: List[Dict] = field(default_factory=list)
    
    def to_dict(self) -> Dict:
        """Convert to dictionary"""
        result = asdict(self)
        # Remove None values
        return {k: v for k, v in result.items() if v is not None}


class GradingEngine:
    """
    Engine for grading exams against answer keys.
    """
    
    def __init__(
        self,
        students_data: List[Dict],
        answer_keys: List[Dict]
    ):
        """
        Initialize grading engine.
        
        Args:
            students_data: List of student info dicts with 'coords', 'student_id', 'name', 'email'
            answer_keys: List of answer key dicts with 'exam_code' and 'answers'
        """
        # Index students by coords (student code)
        self.students_by_code = {
            s.get("coords"): s for s in students_data
        }
        
        # Index answer keys by exam code
        self.answer_keys_by_code = {
            a.get("exam_code"): a for a in answer_keys
        }
    
    @classmethod
    def from_json_files(
        cls,
        student_json_path: str,
        answer_json_path: str
    ) -> "GradingEngine":
        """
        Create engine from JSON files.
        
        Args:
            student_json_path: Path to student info JSON
            answer_json_path: Path to answer keys JSON
            
        Returns:
            GradingEngine instance
        """
        with open(student_json_path, "r", encoding="utf-8") as f:
            students_data = json.load(f)
        
        with open(answer_json_path, "r", encoding="utf-8") as f:
            answer_keys = json.load(f)
        
        return cls(students_data, answer_keys)
    
    def get_student_info(self, student_code: str) -> Dict:
        """Get student info by code"""
        student = self.students_by_code.get(student_code)
        if student:
            return {
                "student_id": student.get("student_id"),
                "name": student.get("name", "Unknown"),
                "email": student.get("email")
            }
        return {"student_id": None, "name": "Unknown", "email": None}
    
    def get_correct_answers(self, exam_code: str) -> Optional[Dict[int, str]]:
        """
        Get correct answers for an exam code.
        
        Returns:
            Dict mapping question number to correct answer, or None if not found
        """
        key = self.answer_keys_by_code.get(exam_code)
        if not key:
            return None
        
        return {
            item["question"]: item["answer"]
            for item in key.get("answers", [])
        }
    
    def grade(
        self,
        student_code: str,
        exam_code: str,
        answers: Dict[int, List[str]],
        image_name: str = ""
    ) -> ExamResult:
        """
        Grade an exam.
        
        Args:
            student_code: Student's code from exam sheet
            exam_code: Exam code from exam sheet
            answers: Dict mapping question number to list of selected answers
            image_name: Name of source image
            
        Returns:
            ExamResult with scores and details
        """
        # Get student info
        student_info = self.get_student_info(student_code)
        
        # Get correct answers
        correct_answers = self.get_correct_answers(exam_code)
        
        if correct_answers is None:
            return ExamResult(
                student_code=student_code,
                exam_code=exam_code,
                image_name=image_name,
                success=False,
                error=f"Answer key not found for exam code: {exam_code}"
            )
        
        total = len(correct_answers)
        correct_count = 0
        wrong_count = 0
        blank_count = 0
        details = []
        
        for q_idx in range(1, total + 1):
            ans = answers.get(q_idx, [])
            correct_ans = correct_answers.get(q_idx, "")
            
            # Determine result
            if len(ans) == 0:
                blank_count += 1
                result = "blank"
                student_answer = None
            elif len(ans) > 1:
                wrong_count += 1
                result = "multi"
                student_answer = ans
            else:
                student_answer = ans[0]
                if student_answer == correct_ans:
                    correct_count += 1
                    result = "correct"
                else:
                    wrong_count += 1
                    result = "wrong"
            
            details.append({
                "question": q_idx,
                "student_answer": student_answer,
                "correct_answer": correct_ans,
                "result": result
            })
        
        # Calculate score (10-point scale)
        score = round((correct_count / total) * 10, 2) if total > 0 else 0.0
        
        return ExamResult(
            student_id=student_info.get("student_id"),
            name=student_info.get("name", "Unknown"),
            email=student_info.get("email"),
            student_code=student_code,
            exam_code=exam_code,
            total_questions=total,
            correct=correct_count,
            wrong=wrong_count,
            blank=blank_count,
            score=score,
            image_name=image_name,
            success=True,
            details=details
        )


def save_results(results: List[ExamResult], output_path: str) -> None:
    """
    Save grading results to JSON file.
    
    Args:
        results: List of ExamResult objects
        output_path: Path to output JSON file
    """
    successful = sum(1 for r in results if r.success)
    failed = len(results) - successful
    
    output_data = {
        "total_images": len(results),
        "successful": successful,
        "failed": failed,
        "results": [r.to_dict() for r in results]
    }
    
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(output_data, f, ensure_ascii=False, indent=4)
    
    logger.info(f"Saved {len(results)} results to {output_path}")


def load_results(input_path: str) -> List[Dict]:
    """
    Load grading results from JSON file.
    
    Args:
        input_path: Path to input JSON file
        
    Returns:
        List of result dictionaries
    """
    with open(input_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    
    return data.get("results", [])
