"""
Grader Module
Provides exam grading functionality using SIFT-based image processing

Usage:
    from backend.grader import ExamProcessor, create_processor
    
    # Create processor
    processor = create_processor(
        template_path="path/to/template.jpg",
        student_json_path="path/to/student_coords.json",
        answer_json_path="path/to/answer.json"
    )
    
    # Process single image
    result = processor.process_file("path/to/exam_image.jpg")
    
    # Process directory
    results = processor.process_directory("path/to/images/")
    
    # Process and save
    summary = processor.process_and_save("path/to/images/", "results.json")
"""

from .image_processing import (
    denoise_enhance_sharpen,
    TemplateWarper,
    load_image,
)

from .cell_detection import (
    CellExtractionConfig,
    CellExtractor,
    detect_timing_marks,
    extract_answer_cells,
    map_cells_to_2d,
)

from .answer_analysis import (
    AnswerAnalyzer,
    analyze_all_answers,
    is_cell_filled,
    predict_code_from_cells,
)

from .grading_engine import (
    GradingEngine,
    ExamResult,
    save_results,
    load_results,
)

from .processor import (
    ExamProcessor,
    ProcessorConfig,
    create_processor,
)

__all__ = [
    # Image processing
    "denoise_enhance_sharpen",
    "TemplateWarper",
    "load_image",
    # Cell detection
    "CellExtractionConfig",
    "CellExtractor",
    "detect_timing_marks",
    "extract_answer_cells",
    "map_cells_to_2d",
    # Answer analysis
    "AnswerAnalyzer",
    "analyze_all_answers",
    "is_cell_filled",
    "predict_code_from_cells",
    # Grading
    "GradingEngine",
    "ExamResult",
    "save_results",
    "load_results",
    # Processor
    "ExamProcessor",
    "ProcessorConfig",
    "create_processor",
]
