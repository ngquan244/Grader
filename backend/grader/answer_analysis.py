"""
Answer Analysis Module
Handles detection of filled circles and answer extraction
"""
import cv2
import numpy as np
from typing import List, Dict, Optional
import logging

logger = logging.getLogger(__name__)

# Answer options
ANSWER_OPTIONS = ["A", "B", "C", "D"]


def preprocess_cell_for_detection(cell: np.ndarray) -> np.ndarray:
    """
    Preprocess cell image for fill detection.
    
    Args:
        cell: Cell image
        
    Returns:
        Preprocessed grayscale image
    """
    gray = cell if len(cell.shape) == 2 else cv2.cvtColor(cell, cv2.COLOR_BGR2GRAY)
    
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    gray = clahe.apply(gray)
    
    kernel = np.array([[0, -1, 0], [-1, 5, -1], [0, -1, 0]], dtype=np.float32)
    sharp = cv2.filter2D(gray, -1, kernel)
    
    return sharp


def binarize_cell(cell: np.ndarray, threshold: int = 128) -> np.ndarray:
    """
    Convert cell to binary image (inverse threshold).
    
    Args:
        cell: Cell image
        threshold: Binarization threshold
        
    Returns:
        Binary image with filled areas as white
    """
    gray = cell if len(cell.shape) == 2 else cv2.cvtColor(cell, cv2.COLOR_BGR2GRAY)
    _, binary = cv2.threshold(gray, threshold, 255, cv2.THRESH_BINARY_INV)
    return binary


def get_fill_count(cell: np.ndarray, threshold: int = 128) -> int:
    """
    Count white pixels in binarized cell.
    
    Args:
        cell: Cell image
        threshold: Binarization threshold
        
    Returns:
        Count of non-zero pixels
    """
    binary = binarize_cell(cell, threshold)
    return cv2.countNonZero(binary)


def is_cell_filled(cell: np.ndarray, pixel_threshold: int = 100) -> bool:
    """
    Determine if a cell is filled (answer selected).
    
    Args:
        cell: Cell image
        pixel_threshold: Minimum pixels to consider filled
        
    Returns:
        True if cell is considered filled
    """
    binary = binarize_cell(cell)
    count = cv2.countNonZero(binary)
    return count > pixel_threshold


def get_question_cells(mapped_cells: List[List[np.ndarray]], q_idx: int) -> List[np.ndarray]:
    """
    Get the 4 answer cells (A, B, C, D) for a specific question.
    
    Args:
        mapped_cells: 2D array of cells
        q_idx: Question index (1-120)
        
    Returns:
        List of 4 cell images for options A, B, C, D
    """
    # Calculate position in grid
    col_block = (q_idx - 1) // 30  # 0, 1, 2, or 3 (4 columns of 30 questions)
    in_block_idx = (q_idx - 1) % 30
    
    row = 11 + in_block_idx  # Answers start at row 11
    col_start = 1 + col_block * 4  # Each block has 4 columns (A, B, C, D)
    col_end = col_start + 4
    
    return mapped_cells[row][col_start:col_end]


def analyze_single_answer(cells: List[np.ndarray], pixel_threshold: int = 100) -> List[str]:
    """
    Analyze which options are selected for a single question.
    
    Args:
        cells: List of 4 cell images (A, B, C, D)
        pixel_threshold: Threshold for considering a cell filled
        
    Returns:
        List of selected options (can be empty or multiple)
    """
    selected = []
    for i, cell in enumerate(cells):
        if is_cell_filled(cell, pixel_threshold):
            selected.append(ANSWER_OPTIONS[i])
    return selected


def analyze_all_answers(
    mapped_cells: List[List[np.ndarray]],
    num_questions: int = 120,
    pixel_threshold: int = 100
) -> Dict[int, List[str]]:
    """
    Analyze answers for all questions.
    
    Args:
        mapped_cells: 2D array of cells
        num_questions: Total number of questions
        pixel_threshold: Threshold for considering a cell filled
        
    Returns:
        Dictionary mapping question number to list of selected answers
    """
    results = {}
    
    for q_idx in range(1, num_questions + 1):
        answer_cells = get_question_cells(mapped_cells, q_idx)
        selected = analyze_single_answer(answer_cells, pixel_threshold)
        results[q_idx] = selected
    
    return results


def predict_code_from_cells(
    cells: List[np.ndarray],
    n_rows: int,
    n_cols: int,
    threshold: int = 128
) -> str:
    """
    Predict numeric code from code region cells.
    
    For each column, finds the row with highest fill count
    and maps to digit (0-9).
    
    Args:
        cells: List of cells in row-major order
        n_rows: Number of rows (should be 10 for digits 0-9)
        n_cols: Number of columns (code length)
        threshold: Binarization threshold
        
    Returns:
        Predicted code string
    """
    code = ""
    
    for col_idx in range(n_cols):
        # Get all cells in this column
        col_cells = [cells[row_idx * n_cols + col_idx] for row_idx in range(n_rows)]
        
        # Preprocess and get fill counts
        fill_counts = []
        for cell in col_cells:
            preprocessed = preprocess_cell_for_detection(cell)
            binary = binarize_cell(preprocessed, threshold)
            fill_counts.append(cv2.countNonZero(binary))
        
        # Find most filled cell
        if max(fill_counts) == 0:
            code += "?"
        else:
            selected_row = int(np.argmax(fill_counts))
            code += str(selected_row % 10)
    
    return code


class AnswerAnalyzer:
    """
    Analyzes exam answers and codes from extracted cells.
    """
    
    def __init__(
        self,
        pixel_threshold: int = 100,
        bin_threshold: int = 128,
        num_questions: int = 120
    ):
        self.pixel_threshold = pixel_threshold
        self.bin_threshold = bin_threshold
        self.num_questions = num_questions
    
    def analyze(
        self,
        mapped_cells: List[List[np.ndarray]],
        student_code_cells: List[np.ndarray],
        exam_code_cells: List[np.ndarray]
    ) -> Dict:
        """
        Analyze all exam data from cells.
        
        Args:
            mapped_cells: 2D array of answer cells
            student_code_cells: Cells for student code region
            exam_code_cells: Cells for exam code region
            
        Returns:
            Dictionary with student_code, exam_code, and answers
        """
        # Predict codes
        student_code = predict_code_from_cells(
            student_code_cells,
            n_rows=10, n_cols=6,
            threshold=self.pixel_threshold
        )
        
        exam_code = predict_code_from_cells(
            exam_code_cells,
            n_rows=10, n_cols=3,
            threshold=self.pixel_threshold
        )
        
        # Analyze answers
        answers = analyze_all_answers(
            mapped_cells,
            self.num_questions,
            self.pixel_threshold
        )
        
        return {
            "student_code": student_code,
            "exam_code": exam_code,
            "answers": answers
        }
