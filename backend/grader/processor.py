"""
Exam Processor Module
Main entry point for processing exam images and generating grades
"""
import cv2
import numpy as np
from pathlib import Path
from typing import List, Dict, Any, Optional, Union
from dataclasses import dataclass
import logging

from .image_processing import TemplateWarper, load_image, denoise_enhance_sharpen
from .cell_detection import CellExtractor, CellExtractionConfig
from .answer_analysis import AnswerAnalyzer
from .grading_engine import GradingEngine, ExamResult, save_results

logger = logging.getLogger(__name__)


@dataclass
class ProcessorConfig:
    """Configuration for exam processor"""
    template_path: str
    student_json_path: str
    answer_json_path: str
    output_path: str = "final_result.json"
    pixel_threshold: int = 100
    num_questions: int = 120
    sift_features: int = 5000


class ExamProcessor:
    """
    Main processor for grading exam images.
    
    Orchestrates the full pipeline:
    1. Image warping to template
    2. Cell extraction
    3. Answer analysis
    4. Grading
    """
    
    def __init__(self, config: ProcessorConfig):
        """
        Initialize processor with configuration.
        
        Args:
            config: ProcessorConfig with paths and settings
        """
        self.config = config
        
        # Load template
        template_img = load_image(config.template_path, grayscale=True)
        if template_img is None:
            raise FileNotFoundError(f"Template not found: {config.template_path}")
        
        # Initialize components
        self.warper = TemplateWarper(template_img, config.sift_features)
        self.cell_extractor = CellExtractor()
        self.analyzer = AnswerAnalyzer(
            pixel_threshold=config.pixel_threshold,
            num_questions=config.num_questions
        )
        self.grading_engine = GradingEngine.from_json_files(
            config.student_json_path,
            config.answer_json_path
        )
        
        logger.info("ExamProcessor initialized successfully")
    
    def process_image(
        self,
        img: np.ndarray,
        image_name: str = ""
    ) -> ExamResult:
        """
        Process a single exam image.
        
        Args:
            img: Exam image (grayscale or BGR)
            image_name: Optional name for logging
            
        Returns:
            ExamResult with grading details
        """
        try:
            logger.info(f"Processing image: {image_name}")
            
            # 1. Warp to template
            try:
                warped = self.warper.warp(img)
            except ValueError as e:
                return ExamResult(
                    image_name=image_name,
                    success=False,
                    error=f"Failed to warp image: {str(e)}",
                    suggestion="Image needs sufficient SIFT features matching template"
                )
            
            # 2. Extract cells
            try:
                cells_data = self.cell_extractor.extract_all(warped)
            except ValueError as e:
                return ExamResult(
                    image_name=image_name,
                    success=False,
                    error=f"Failed to extract cells: {str(e)}",
                    suggestion="Timing marks not detected. Ensure image is clear and not blurry."
                )
            
            # 3. Analyze answers
            analysis = self.analyzer.analyze(
                cells_data["mapped_cells"],
                cells_data["student_code_cells"],
                cells_data["exam_code_cells"]
            )
            
            # 4. Grade
            result = self.grading_engine.grade(
                student_code=analysis["student_code"],
                exam_code=analysis["exam_code"],
                answers=analysis["answers"],
                image_name=image_name
            )
            
            logger.info(
                f"Processed {image_name}: "
                f"Student={result.student_code}, "
                f"Exam={result.exam_code}, "
                f"Score={result.score}"
            )
            
            return result
            
        except Exception as e:
            logger.exception(f"Unexpected error processing {image_name}")
            return ExamResult(
                image_name=image_name,
                success=False,
                error=f"Unexpected error: {str(e)}",
                suggestion="Check image quality or contact support"
            )
    
    def process_file(self, image_path: Union[str, Path]) -> ExamResult:
        """
        Process an exam image file.
        
        Args:
            image_path: Path to image file
            
        Returns:
            ExamResult with grading details
        """
        path = Path(image_path)
        img = load_image(str(path), grayscale=True)
        
        if img is None:
            return ExamResult(
                image_name=path.name,
                success=False,
                error=f"Failed to load image: {path}",
                suggestion="Ensure file exists and is a valid image format"
            )
        
        return self.process_image(img, path.stem)
    
    def process_directory(
        self,
        directory: Union[str, Path],
        extensions: List[str] = None
    ) -> List[ExamResult]:
        """
        Process all exam images in a directory.
        
        Args:
            directory: Path to directory containing images
            extensions: List of valid extensions (default: jpg, jpeg, png)
            
        Returns:
            List of ExamResult objects
        """
        if extensions is None:
            extensions = [".jpg", ".jpeg", ".png"]
        
        directory = Path(directory)
        if not directory.exists():
            logger.warning(f"Directory not found: {directory}")
            return []
        
        # Find all image files (use set to avoid duplicates on case-insensitive systems)
        image_files = set()
        for ext in extensions:
            # Match both lower and upper case on case-insensitive systems
            image_files.update(directory.glob(f"*{ext}"))
            image_files.update(directory.glob(f"*{ext.upper()}"))
        
        # Convert to sorted list
        image_files = sorted(image_files, key=lambda p: p.name.lower())
        
        if not image_files:
            logger.warning(f"No images found in {directory}")
            return []
        
        logger.info(f"Found {len(image_files)} images to process")
        
        results = []
        for image_path in sorted(image_files):
            result = self.process_file(image_path)
            results.append(result)
        
        return results
    
    def process_and_save(
        self,
        directory: Union[str, Path],
        output_path: str = None
    ) -> Dict[str, Any]:
        """
        Process all images in directory and save results.
        
        Args:
            directory: Path to directory containing images
            output_path: Path for output JSON (uses config default if None)
            
        Returns:
            Summary dictionary with counts and results
        """
        results = self.process_directory(directory)
        
        output_path = output_path or self.config.output_path
        save_results(results, output_path)
        
        successful = sum(1 for r in results if r.success)
        failed = len(results) - successful
        
        return {
            "total_images": len(results),
            "successful": successful,
            "failed": failed,
            "output_path": output_path
        }


def create_processor(
    template_path: str,
    student_json_path: str,
    answer_json_path: str,
    **kwargs
) -> ExamProcessor:
    """
    Factory function to create ExamProcessor.
    
    Args:
        template_path: Path to template image
        student_json_path: Path to student info JSON
        answer_json_path: Path to answer keys JSON
        **kwargs: Additional ProcessorConfig options
        
    Returns:
        Configured ExamProcessor instance
    """
    config = ProcessorConfig(
        template_path=template_path,
        student_json_path=student_json_path,
        answer_json_path=answer_json_path,
        **kwargs
    )
    return ExamProcessor(config)
