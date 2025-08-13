"""
OCR Reader Module for Korean License Plate Recognition

This module implements Korean license plate text recognition using EasyOCR,
specifically optimized for Korean license plate formats and character recognition.
It processes license plate images detected by the license plate detector and
extracts readable text for violation reporting.

Key Features:
- Korean license plate text recognition with EasyOCR
- Optimized preprocessing for license plate OCR
- Support for various Korean license plate formats
- Confidence scoring and text validation
- Batch processing for multiple plates
- Integration with license plate detector pipeline

Architecture:
- LicensePlateOCR: Core OCR engine with Korean language support
- OCRResult: Structured result with text and confidence data
- TextProcessor: Korean text validation and formatting
- OCRManager: Multi-stream OCR coordinator
"""

import logging
import os
import re
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple, Any
import threading
import numpy as np
import cv2
import easyocr
from pathlib import Path

from license_plate_detector import PlateDetectionResult

# Configure logging
logger = logging.getLogger(__name__)


@dataclass
class OCRResult:
    """
    Result of Korean license plate OCR analysis.
    
    Contains recognized text, confidence scores, character-level analysis,
    and validation results for Korean license plate formats.
    """
    # Fields without default values
    recognized_text: str
    confidence_score: float
    characters: List[Dict[str, Any]]
    character_confidences: List[float]
    is_valid_format: bool
    formatted_text: str
    plate_type: str
    preprocessing_applied: List[str]
    plate_image: np.ndarray

    # Fields with default values
    ocr_processing_time: float = 0.0
    text_clarity_score: float = 0.0
    recognition_reliability: float = 0.0
    processed_image: Optional[np.ndarray] = None
    
    def get_text_summary(self) -> Dict[str, Any]:
        """Get summary of OCR text recognition."""
        return {
            "text": self.recognized_text,
            "formatted": self.formatted_text,
            "confidence": self.confidence_score,
            "valid_format": self.is_valid_format,
            "plate_type": self.plate_type,
            "character_count": len(self.characters),
            "reliability": self.recognition_reliability
        }


class TextProcessor:
    """
    Korean license plate text validation and formatting processor.
    
    Handles Korean license plate format validation, text cleaning,
    and standardization according to Korean license plate regulations.
    """
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        
        # Korean license plate patterns
        self.plate_patterns = {
            # Standard format: 숫자+한글+숫자 (예: 12가3456)
            "standard": re.compile(r'^(\d{2,3})([가-힣])(\d{4})$'),
            
            # Old format: 지역+숫자+한글+숫자 (예: 서울12가3456)  
            "regional": re.compile(r'^([가-힣]{2})(\d{2,3})([가-힣])(\d{4})$'),
            
            # Commercial format: 숫자+한글+숫자 with specific characters
            "commercial": re.compile(r'^(\d{2,3})([아-자])(\d{4})$'),
            
            # Diplomatic format: 외교+숫자
            "diplomatic": re.compile(r'^(외교)(\d{3,4})$'),
            
            # Military format: 국방+숫자+한글+숫자
            "military": re.compile(r'^(국방)(\d{2,3})([가-힣])(\d{4})$')
        }
        
        # Valid Korean license plate characters
        self.valid_characters = {
            "numbers": "0123456789",
            "hangul_general": "가나다라마거너더러머버서어저고노도로모보소오조구누두루무부수우주",
            "hangul_commercial": "아바사자",
            "regions": ["서울", "부산", "대구", "인천", "광주", "대전", "울산", "세종", 
                       "경기", "강원", "충북", "충남", "전북", "전남", "경북", "경남", "제주"]
        }
    
    def validate_and_format(self, raw_text: str) -> Tuple[bool, str, str]:
        """
        Validate and format Korean license plate text.
        
        Args:
            raw_text: Raw OCR text result
            
        Returns:
            Tuple[bool, str, str]: (is_valid, formatted_text, plate_type)
        """
        # Clean the text
        cleaned_text = self._clean_text(raw_text)
        
        if not cleaned_text:
            return False, "", "unknown"
        
        # Try to match against known patterns
        for plate_type, pattern in self.plate_patterns.items():
            match = pattern.match(cleaned_text)
            if match:
                formatted_text = self._format_matched_text(match.groups(), plate_type)
                korean_plate_type = self._get_korean_plate_type(plate_type, match.groups())
                return True, formatted_text, korean_plate_type
        
        # If no exact match, try fuzzy matching
        fuzzy_result = self._fuzzy_match_format(cleaned_text)
        if fuzzy_result[0]:
            return fuzzy_result
        
        return False, cleaned_text, "unknown"
    
    def _clean_text(self, text: str) -> str:
        """Clean and preprocess OCR text."""
        if not text:
            return ""
        
        # Remove whitespace and special characters
        cleaned = re.sub(r'[^\w가-힣]', '', text)
        
        # Common OCR error corrections for Korean plates
        corrections = {
            # Number corrections
            'O': '0', 'o': '0', 'I': '1', 'l': '1',
            'S': '5', 'G': '6', 'B': '8',
            
            # Korean character corrections
            '가': '가', '나': '나',  # Examples - expand based on common errors
        }
        
        for wrong, correct in corrections.items():
            cleaned = cleaned.replace(wrong, correct)
        
        return cleaned.upper()  # Normalize to uppercase
    
    def _format_matched_text(self, groups: tuple, plate_type: str) -> str:
        """Format matched text groups into standard plate format."""
        try:
            if plate_type == "standard":
                # Format: 12가3456
                return f"{groups[0]}{groups[1]}{groups[2]}"
            
            elif plate_type == "regional":
                # Format: 서울12가3456
                return f"{groups[0]}{groups[1]}{groups[2]}{groups[3]}"
            
            elif plate_type in ["commercial", "military"]:
                return f"{groups[0]}{groups[1]}{groups[2]}"
            
            elif plate_type == "diplomatic":
                return f"{groups[0]}{groups[1]}"
            
            else:
                return "".join(groups)
                
        except Exception as e:
            logger.debug(f"Error formatting text groups: {e}")
            return "".join(groups)
    
    def _get_korean_plate_type(self, pattern_type: str, groups: tuple) -> str:
        """Get Korean description of plate type."""
        type_mapping = {
            "standard": "일반",
            "regional": "지역",
            "commercial": "영업용",
            "diplomatic": "외교",
            "military": "군용"
        }
        
        return type_mapping.get(pattern_type, "기타")
    
    def _fuzzy_match_format(self, text: str) -> Tuple[bool, str, str]:
        """Attempt fuzzy matching for imperfect OCR results."""
        # Simple heuristics for common Korean plate formats
        
        # Look for pattern: numbers + Korean char + numbers
        match = re.search(r'(\d+)([가-힣])(\d+)', text)
        if match:
            numbers1, korean, numbers2 = match.groups()
            
            # Check if it looks like a valid plate
            if (2 <= len(numbers1) <= 3 and 
                korean in self.valid_characters["hangul_general"] and
                len(numbers2) == 4):
                
                formatted = f"{numbers1}{korean}{numbers2}"
                return True, formatted, "일반"
        
        return False, text, "unknown"
    
    def assess_text_quality(self, text: str, character_confidences: List[float]) -> float:
        """Assess the quality/reliability of recognized text."""
        if not text or not character_confidences:
            return 0.0
        
        # Base score on average character confidence
        avg_confidence = np.mean(character_confidences)
        
        # Penalty for very short or very long text
        length_penalty = 1.0
        if len(text) < 5:
            length_penalty = 0.8
        elif len(text) > 10:
            length_penalty = 0.9
        
        # Bonus for valid format
        is_valid, _, _ = self.validate_and_format(text)
        format_bonus = 1.2 if is_valid else 1.0
        
        quality_score = avg_confidence * length_penalty * format_bonus
        return min(quality_score, 1.0)


class LicensePlateOCR:
    """
    Core Korean license plate OCR engine using EasyOCR.
    
    Handles Korean text recognition from license plate images,
    with optimized settings for Korean license plate formats.
    """
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.reader = None
        self.text_processor = TextProcessor(config)
        self.lock = threading.Lock()
        
        # OCR configuration
        self.languages = config.get('languages', ['ko', 'en'])  # Korean and English
        self.use_gpu = config.get('use_gpu', True)
        self.confidence_threshold = config.get('confidence_threshold', 0.5)
        
        # Initialize EasyOCR
        self._initialize_ocr()
        
        logger.info("LicensePlateOCR initialized")
    
    def _initialize_ocr(self) -> bool:
        """Initialize EasyOCR reader with Korean language support."""
        try:
            logger.info("Initializing EasyOCR reader...")
            
            # Initialize EasyOCR reader
            self.reader = easyocr.Reader(
                self.languages,
                gpu=self.use_gpu,
                verbose=False
            )
            
            logger.info("EasyOCR reader initialized successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize EasyOCR: {e}")
            return False
    
    def recognize_plate_text(self, plate_image: np.ndarray, 
                           preprocessing_metadata: Optional[Dict[str, Any]] = None) -> OCRResult:
        """
        Recognize text from Korean license plate image.
        
        Args:
            plate_image: Preprocessed license plate image
            preprocessing_metadata: Metadata from plate preprocessing
            
        Returns:
            OCRResult: Complete OCR analysis result
        """
        import time
        start_time = time.time()
        
        if self.reader is None:
            logger.error("OCR reader not initialized")
            return self._create_error_result(plate_image, "OCR reader not initialized")
        
        try:
            with self.lock:
                # Apply additional preprocessing for OCR
                processed_image = self._preprocess_for_ocr(plate_image)
                
                # Run OCR
                ocr_results = self.reader.readtext(
                    processed_image,
                    detail=1,  # Get detailed results with bounding boxes
                    paragraph=False,  # Don't group into paragraphs
                    width_ths=0.7,  # Text width threshold
                    height_ths=0.7  # Text height threshold
                )
                
                # Process OCR results
                result = self._process_ocr_results(
                    ocr_results, plate_image, processed_image, preprocessing_metadata
                )
                
                result.ocr_processing_time = time.time() - start_time
                return result
                
        except Exception as e:
            logger.error(f"Error during OCR recognition: {e}")
            return self._create_error_result(plate_image, f"OCR error: {str(e)}")
    
    def _preprocess_for_ocr(self, image: np.ndarray) -> np.ndarray:
        """Apply additional preprocessing optimized for OCR."""
        processed = image.copy()
        
        try:
            # Convert to grayscale if needed
            if len(processed.shape) == 3:
                processed = cv2.cvtColor(processed, cv2.COLOR_BGR2GRAY)
            
            # Resize to optimal size for OCR (height around 64-128 pixels)
            height, width = processed.shape
            if height < 32:
                # Upscale small images
                scale_factor = 64 / height
                new_width = int(width * scale_factor)
                processed = cv2.resize(processed, (new_width, 64), interpolation=cv2.INTER_CUBIC)
            elif height > 128:
                # Downscale large images
                scale_factor = 128 / height
                new_width = int(width * scale_factor)
                processed = cv2.resize(processed, (new_width, 128), interpolation=cv2.INTER_AREA)
            
            # Normalize and enhance contrast
            processed = cv2.equalizeHist(processed)
            
            # Slight blur to reduce noise
            processed = cv2.GaussianBlur(processed, (3, 3), 0)
            
            # Threshold to binary image
            _, processed = cv2.threshold(processed, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
            
            return processed
            
        except Exception as e:
            logger.debug(f"OCR preprocessing failed: {e}")
            return image
    
    def _process_ocr_results(self, ocr_results: List, plate_image: np.ndarray,
                           processed_image: np.ndarray, 
                           preprocessing_metadata: Optional[Dict[str, Any]]) -> OCRResult:
        """Process EasyOCR results into structured OCRResult."""
        
        if not ocr_results:
            return self._create_error_result(plate_image, "No text detected")
        
        # Extract text and confidences
        all_text = []
        all_confidences = []
        character_details = []
        
        for result in ocr_results:
            bbox, text, confidence = result
            
            if confidence >= self.confidence_threshold:
                all_text.append(text)
                all_confidences.append(confidence)
                
                character_details.append({
                    "text": text,
                    "bbox": bbox,
                    "confidence": confidence
                })
        
        # Combine all recognized text
        combined_text = "".join(all_text)
        
        if not combined_text:
            return self._create_error_result(plate_image, "No text above confidence threshold")
        
        # Process and validate text
        is_valid, formatted_text, plate_type = self.text_processor.validate_and_format(combined_text)
        
        # Calculate overall confidence
        overall_confidence = np.mean(all_confidences) if all_confidences else 0.0
        
        # Assess text quality
        text_quality = self.text_processor.assess_text_quality(combined_text, all_confidences)
        
        # Create result
        return OCRResult(
            recognized_text=combined_text,
            confidence_score=overall_confidence,
            characters=character_details,
            character_confidences=all_confidences,
            is_valid_format=is_valid,
            formatted_text=formatted_text,
            plate_type=plate_type,
            preprocessing_applied=preprocessing_metadata.get('preprocessing_applied', []) if preprocessing_metadata else [],
            text_clarity_score=text_quality,
            recognition_reliability=min(overall_confidence * 1.2 if is_valid else overall_confidence * 0.8, 1.0),
            plate_image=plate_image,
            processed_image=processed_image
        )
    
    def _create_error_result(self, plate_image: np.ndarray, error_message: str) -> OCRResult:
        """Create error result for failed OCR."""
        return OCRResult(
            recognized_text="",
            confidence_score=0.0,
            characters=[],
            character_confidences=[],
            is_valid_format=False,
            formatted_text="",
            plate_type="error",
            preprocessing_applied=[f"error: {error_message}"],
            plate_image=plate_image
        )
    
    def batch_recognize_plates(self, plate_images: List[np.ndarray]) -> List[OCRResult]:
        """
        Recognize text from multiple license plate images in batch.
        
        Args:
            plate_images: List of preprocessed license plate images
            
        Returns:
            List[OCRResult]: Results for each input image
        """
        results = []
        
        for image in plate_images:
            result = self.recognize_plate_text(image)
            results.append(result)
        
        return results
    
    def get_ocr_info(self) -> Dict[str, Any]:
        """Get information about OCR configuration."""
        return {
            "reader_initialized": self.reader is not None,
            "languages": self.languages,
            "use_gpu": self.use_gpu,
            "confidence_threshold": self.confidence_threshold
        }


class OCRManager:
    """
    Multi-stream OCR coordinator for Korean license plate recognition.
    
    Manages OCR processing across multiple CCTV streams,
    coordinates with license plate detector, and provides centralized OCR services.
    """
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.ocr_engine: Optional[LicensePlateOCR] = None
        self.lock = threading.Lock()
        
        # Load OCR configuration
        self.ocr_config = config.get('models', {}).get('ocr_reader', {})
        
        self._initialize_ocr()
        
        logger.info("OCRManager initialized")
    
    def _initialize_ocr(self) -> bool:
        """Initialize the OCR engine."""
        try:
            self.ocr_engine = LicensePlateOCR(self.ocr_config)
            return self.ocr_engine.reader is not None
            
        except Exception as e:
            logger.error(f"Failed to initialize OCR engine: {e}")
            return False
    
    def process_plate_detection(self, plate_result: PlateDetectionResult) -> OCRResult:
        """
        Process a license plate detection result with OCR.
        
        Args:
            plate_result: License plate detection result
            
        Returns:
            OCRResult: OCR recognition result
        """
        if not self.ocr_engine:
            logger.error("OCR engine not initialized")
            return self._create_error_result(plate_result.cropped_plate, "OCR engine not initialized")
        
        # Use preprocessed plate image if available, otherwise use cropped plate
        plate_image = plate_result.preprocessed_plate if plate_result.preprocessed_plate is not None else plate_result.cropped_plate
        
        # Extract preprocessing metadata
        preprocessing_metadata = {
            "preprocessing_applied": ["license_plate_detection"],
            "detection_confidence": plate_result.confidence,
            "plate_quality": {
                "clarity": plate_result.clarity_score,
                "lighting": plate_result.lighting_quality,
                "ocr_readiness": plate_result.ocr_readiness
            }
        }
        
        return self.ocr_engine.recognize_plate_text(plate_image, preprocessing_metadata)
    
    def batch_process_plates(self, plate_results: List[PlateDetectionResult]) -> List[OCRResult]:
        """
        Process multiple license plate detection results with OCR.
        
        Args:
            plate_results: List of license plate detection results
            
        Returns:
            List[OCRResult]: OCR results for each plate
        """
        results = []
        
        for plate_result in plate_results:
            ocr_result = self.process_plate_detection(plate_result)
            results.append(ocr_result)
        
        return results
    
    def _create_error_result(self, plate_image: np.ndarray, error_message: str) -> OCRResult:
        """Create error result for failed OCR."""
        return OCRResult(
            recognized_text="",
            confidence_score=0.0,
            characters=[],
            character_confidences=[],
            is_valid_format=False,
            formatted_text="",
            plate_type="error",
            preprocessing_applied=[f"error: {error_message}"],
            plate_image=plate_image
        )
    
    def is_ready(self) -> bool:
        """Check if OCR manager is ready for use."""
        return self.ocr_engine is not None and self.ocr_engine.reader is not None
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get OCR manager statistics and status."""
        return {
            "ready": self.is_ready(),
            "ocr_info": self.ocr_engine.get_ocr_info() if self.ocr_engine else {},
            "config": self.ocr_config
        }


# Global instance - will be initialized by main application
ocr_manager: Optional[OCRManager] = None


def initialize_ocr_reader(config: Dict[str, Any]) -> bool:
    """
    Initialize the global OCR reader instance.
    
    Args:
        config: Configuration dictionary from config.yaml
        
    Returns:
        bool: True if initialization successful
    """
    global ocr_manager
    
    try:
        ocr_manager = OCRManager(config)
        success = ocr_manager.is_ready()
        
        if success:
            logger.info("OCR reader initialized successfully")
        else:
            logger.error("OCR reader initialization failed")
        
        return success
        
    except Exception as e:
        logger.error(f"Failed to initialize OCR reader: {e}")
        return False


def get_ocr_reader() -> Optional[OCRManager]:
    """
    Get the global OCR reader instance.
    
    Returns:
        Optional[OCRManager]: OCR manager instance or None if not initialized
    """
    return ocr_manager