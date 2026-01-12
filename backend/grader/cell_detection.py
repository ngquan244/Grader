"""
Cell Detection Module
Handles timing marks detection and cell extraction from exam sheets
"""
import cv2
import numpy as np
from typing import List, Tuple, Dict, Any
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)


@dataclass
class CellExtractionConfig:
    """Configuration for cell extraction"""
    cell_size: int = 15
    n_rows: int = 42
    n_cols: int = 18
    
    # Student code region
    student_code_x: int = 892
    student_code_width: int = 145
    student_code_cols: int = 6
    
    # Exam code region
    exam_code_x: int = 1080
    exam_code_width: int = 72
    exam_code_cols: int = 3
    
    # Code rows
    code_row_height: int = 35
    code_row_start: int = 1
    code_row_end: int = 11
    
    # Timing marks strip ratios
    right_strip_ratio: float = 0.05
    bottom_strip_ratio: float = 0.05


def preprocess_strip(strip: np.ndarray, enhance: bool = True) -> np.ndarray:
    """
    Preprocess timing mark strip for detection.
    
    Args:
        strip: Input strip image
        enhance: Whether to apply CLAHE enhancement
        
    Returns:
        Binary image ready for contour detection
    """
    gray = cv2.cvtColor(strip, cv2.COLOR_BGR2GRAY) if len(strip.shape) == 3 else strip
    
    if enhance:
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        gray = clahe.apply(gray)
    
    gray = cv2.GaussianBlur(gray, (3, 3), 0)
    
    binary = cv2.adaptiveThreshold(
        gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY_INV, 11, 2
    )
    
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
    binary = cv2.morphologyEx(binary, cv2.MORPH_CLOSE, kernel)
    
    return binary


def detect_timing_marks(
    binary_strip: np.ndarray,
    axis: str = 'vertical',
    min_area: int = 50,
    max_area: int = 8000,
    min_dist: int = 8,
    aspect_ratio_range: Tuple[float, float] = (0.2, 6.0),
    edge_margin: int = 3
) -> List[int]:
    """
    Detect timing marks (black dots) on a strip for alignment.
    
    Args:
        binary_strip: Binary image of the strip
        axis: 'vertical' for row marks, 'horizontal' for column marks
        min_area: Minimum contour area to consider
        max_area: Maximum contour area to consider
        min_dist: Minimum distance between consecutive marks
        aspect_ratio_range: Valid aspect ratio range for marks
        edge_margin: Margin from edges to ignore
        
    Returns:
        List of mark positions (y-coordinates for vertical, x for horizontal)
    """
    h, w = binary_strip.shape[:2]
    contours, _ = cv2.findContours(
        binary_strip, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
    )
    
    candidates = []
    
    for cnt in contours:
        x, y, w_box, h_box = cv2.boundingRect(cnt)
        area = w_box * h_box
        
        # Filter by area
        if area < min_area or area > max_area:
            continue
        
        # Filter by aspect ratio
        aspect = w_box / h_box if h_box > 0 else 0
        if not (aspect_ratio_range[0] <= aspect <= aspect_ratio_range[1]):
            continue
        
        # Filter by edge proximity and get position
        if axis == 'vertical':
            if x < edge_margin or x + w_box > w - edge_margin:
                continue
            pos = y + h_box // 2
        else:
            if y < edge_margin or y + h_box > h - edge_margin:
                continue
            pos = x + w_box // 2
        
        candidates.append((pos, area))
    
    # Sort by position
    candidates.sort(key=lambda x: x[0])
    
    # Filter by minimum distance
    filtered = []
    for pos, area in candidates:
        if not filtered or abs(pos - filtered[-1]) >= min_dist:
            filtered.append(pos)
    
    return filtered


def extract_timing_strips(
    warped_img: np.ndarray,
    right_ratio: float = 0.05,
    bottom_ratio: float = 0.05
) -> Tuple[np.ndarray, np.ndarray]:
    """
    Extract right and bottom strips containing timing marks.
    
    Args:
        warped_img: Warped exam image
        right_ratio: Ratio of image width for right strip
        bottom_ratio: Ratio of image height for bottom strip
        
    Returns:
        Tuple of (right_strip, bottom_strip)
    """
    h, w = warped_img.shape[:2]
    
    right_start_x = int(w * (1 - right_ratio))
    right_strip = warped_img[:, right_start_x:]
    
    bottom_start_y = int(h * (1 - bottom_ratio))
    bottom_strip = warped_img[bottom_start_y:, :]
    
    return right_strip, bottom_strip


def detect_grid_marks(
    warped_img: np.ndarray,
    config: CellExtractionConfig = None
) -> Tuple[List[int], List[int]]:
    """
    Detect row and column marks from timing strips.
    
    Args:
        warped_img: Warped exam image
        config: Cell extraction configuration
        
    Returns:
        Tuple of (row_marks, col_marks)
    """
    if config is None:
        config = CellExtractionConfig()
    
    right_strip, bottom_strip = extract_timing_strips(
        warped_img, config.right_strip_ratio, config.bottom_strip_ratio
    )
    
    bin_right = preprocess_strip(right_strip)
    bin_bottom = preprocess_strip(bottom_strip)
    
    row_marks = detect_timing_marks(bin_right, axis='vertical', min_area=150, min_dist=10)
    col_marks = detect_timing_marks(bin_bottom, axis='horizontal', min_area=150, min_dist=10)
    
    logger.debug(f"Detected {len(row_marks)} row marks, {len(col_marks)} column marks")
    
    return row_marks, col_marks


def extract_answer_cells(
    warped_img: np.ndarray,
    row_marks: List[int],
    col_marks: List[int],
    cell_size: int = 15
) -> List[np.ndarray]:
    """
    Extract individual answer cells from warped image.
    
    Args:
        warped_img: Warped exam image
        row_marks: List of row mark positions
        col_marks: List of column mark positions
        cell_size: Half-size of cell extraction area
        
    Returns:
        List of cell images in row-major order
    """
    h, w = warped_img.shape[:2]
    cells = []
    
    for y in row_marks:
        for x in col_marks:
            y1, y2 = max(0, y - cell_size), min(h, y + cell_size)
            x1, x2 = max(0, x - cell_size), min(w, x + cell_size)
            cell = warped_img[y1:y2, x1:x2]
            cells.append(cell)
    
    return cells


def map_cells_to_2d(
    cells: List[np.ndarray],
    n_rows: int = 42,
    n_cols: int = 18
) -> List[List[np.ndarray]]:
    """
    Map flat cell list to 2D array.
    
    Args:
        cells: List of cell images
        n_rows: Expected number of rows
        n_cols: Expected number of columns
        
    Returns:
        2D list of cells [row][col]
        
    Raises:
        ValueError: If cell count doesn't match expected grid
    """
    required_cells = n_rows * n_cols
    if len(cells) < required_cells:
        raise ValueError(
            f"Insufficient cells: got {len(cells)}, need {required_cells}. "
            "Image may be blurry or timing marks not detected properly."
        )
    
    mapped = []
    idx = 0
    for r in range(n_rows):
        row_cells = []
        for c in range(n_cols):
            row_cells.append(cells[idx])
            idx += 1
        mapped.append(row_cells)
    
    return mapped


def extract_code_region_cells(
    warped_img: np.ndarray,
    row_marks: List[int],
    x_start: int,
    total_width: int,
    n_cols: int,
    row_height: int = 35,
    row_start: int = 1,
    row_end: int = 11
) -> List[np.ndarray]:
    """
    Extract cells from student code or exam code region.
    
    Args:
        warped_img: Warped exam image
        row_marks: List of row mark positions
        x_start: X coordinate where code region starts
        total_width: Total width of code region
        n_cols: Number of columns in code region
        row_height: Height of each row
        row_start: Starting row index in row_marks
        row_end: Ending row index in row_marks (exclusive)
        
    Returns:
        List of cell images
    """
    half_h = row_height // 2
    cell_w = total_width / n_cols
    blocks = []
    
    selected_rows = [row_marks[i] for i in range(row_start, row_end)]
    
    for y_center in selected_rows:
        y1 = max(0, int(y_center - half_h))
        y2 = min(warped_img.shape[0], int(y_center + half_h))
        
        for col_idx in range(n_cols):
            x1 = int(x_start + col_idx * cell_w)
            x2 = int(x_start + (col_idx + 1) * cell_w)
            x2 = min(warped_img.shape[1], x2)
            
            if y2 > y1 and x2 > x1:
                block = warped_img[y1:y2, x1:x2]
                blocks.append(block)
    
    return blocks


class CellExtractor:
    """
    Extracts all relevant cells from a warped exam image.
    """
    
    def __init__(self, config: CellExtractionConfig = None):
        self.config = config or CellExtractionConfig()
    
    def extract_all(self, warped_img: np.ndarray) -> Dict[str, Any]:
        """
        Extract all cells from warped image.
        
        Args:
            warped_img: Warped exam image
            
        Returns:
            Dictionary containing:
                - mapped_cells: 2D array of answer cells
                - student_code_cells: List of student code cells
                - exam_code_cells: List of exam code cells
                - row_marks: Detected row marks
                - col_marks: Detected column marks
        """
        cfg = self.config
        
        # Detect timing marks
        row_marks, col_marks = detect_grid_marks(warped_img, cfg)
        
        # Validate minimum marks
        if len(row_marks) < 30 or len(col_marks) < 15:
            raise ValueError(
                f"Insufficient timing marks: {len(row_marks)} rows, {len(col_marks)} cols. "
                "Need at least 30 rows and 15 columns."
            )
        
        # Extract answer cells
        cells = extract_answer_cells(warped_img, row_marks, col_marks, cfg.cell_size)
        mapped_cells = map_cells_to_2d(cells, cfg.n_rows, cfg.n_cols)
        
        # Extract student code cells
        student_code_cells = extract_code_region_cells(
            warped_img, row_marks,
            cfg.student_code_x, cfg.student_code_width, cfg.student_code_cols,
            cfg.code_row_height, cfg.code_row_start, cfg.code_row_end
        )
        
        # Extract exam code cells
        exam_code_cells = extract_code_region_cells(
            warped_img, row_marks,
            cfg.exam_code_x, cfg.exam_code_width, cfg.exam_code_cols,
            cfg.code_row_height, cfg.code_row_start, cfg.code_row_end
        )
        
        return {
            "mapped_cells": mapped_cells,
            "student_code_cells": student_code_cells,
            "exam_code_cells": exam_code_cells,
            "row_marks": row_marks,
            "col_marks": col_marks
        }
