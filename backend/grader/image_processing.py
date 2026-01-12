"""
Image Processing Module
Handles image preprocessing and SIFT-based warping to template
"""
import cv2
import numpy as np
from typing import Tuple, Optional
import logging

logger = logging.getLogger(__name__)


def denoise_enhance_sharpen(img: np.ndarray) -> np.ndarray:
    """
    Apply denoising, CLAHE enhancement, and sharpening to an image.
    
    Args:
        img: Input image (grayscale or BGR)
        
    Returns:
        Processed grayscale image
    """
    # Convert to grayscale if needed
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY) if len(img.shape) == 3 else img
    
    # Denoise
    denoised = cv2.fastNlMeansDenoising(
        gray, None, h=10, templateWindowSize=7, searchWindowSize=21
    )
    
    # CLAHE enhancement
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    enhanced = clahe.apply(denoised)
    
    # Sharpen
    blur = cv2.GaussianBlur(enhanced, (3, 3), 0)
    sharpened = cv2.addWeighted(enhanced, 1.5, blur, -0.5, 0)
    sharpened = np.clip(sharpened, 0, 255).astype(np.uint8)
    
    return sharpened


class TemplateWarper:
    """
    Handles SIFT-based image warping to match a template.
    """
    
    def __init__(self, template_img: np.ndarray, n_features: int = 5000):
        """
        Initialize with template image.
        
        Args:
            template_img: Template image (grayscale)
            n_features: Number of SIFT features to detect
        """
        self.template_img = template_img
        self.template_proc = denoise_enhance_sharpen(template_img)
        
        # Initialize SIFT and detect features on template
        self.sift = cv2.SIFT_create(nfeatures=n_features)
        self.template_kp, self.template_des = self.sift.detectAndCompute(
            self.template_proc, None
        )
        
        logger.info(f"Template initialized with {len(self.template_kp)} SIFT features")
    
    def warp(self, img: np.ndarray, ratio_threshold: float = 0.75) -> np.ndarray:
        """
        Warp input image to match template using SIFT feature matching.
        
        Args:
            img: Input image to warp
            ratio_threshold: Lowe's ratio test threshold
            
        Returns:
            Warped image aligned to template
            
        Raises:
            ValueError: If not enough matching points found
        """
        # Preprocess input image
        img_proc = denoise_enhance_sharpen(img)
        
        # Detect features
        kp, des = self.sift.detectAndCompute(img_proc, None)
        
        # Match features using BFMatcher
        bf = cv2.BFMatcher(cv2.NORM_L2)
        matches = bf.knnMatch(self.template_des, des, k=2)
        
        # Apply Lowe's ratio test
        good_matches = [
            m for m, n in matches 
            if m.distance < ratio_threshold * n.distance
        ]
        
        if len(good_matches) < 4:
            raise ValueError(
                f"Not enough matching points for homography: {len(good_matches)} found, 4 required"
            )
        
        # Extract matching points
        pts_template = np.float32([
            self.template_kp[m.queryIdx].pt for m in good_matches
        ]).reshape(-1, 1, 2)
        
        pts_img = np.float32([
            kp[m.trainIdx].pt for m in good_matches
        ]).reshape(-1, 1, 2)
        
        # Compute homography
        H, mask = cv2.findHomography(pts_img, pts_template, cv2.RANSAC, 5.0)
        
        # Warp image
        h, w = self.template_img.shape[:2]
        warped = cv2.warpPerspective(img_proc, H, (w, h))
        
        return warped


def load_image(path: str, grayscale: bool = True) -> Optional[np.ndarray]:
    """
    Load image from file.
    
    Args:
        path: Path to image file
        grayscale: Whether to load as grayscale
        
    Returns:
        Image array or None if loading fails
    """
    flag = cv2.IMREAD_GRAYSCALE if grayscale else cv2.IMREAD_COLOR
    img = cv2.imread(str(path), flag)
    
    if img is None:
        logger.warning(f"Failed to load image: {path}")
    
    return img
