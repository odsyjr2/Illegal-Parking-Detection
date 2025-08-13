"""
License Plate Detection Module for Illegal Parking Detection System

This module implements license plate detection using a fine-tuned YOLO model specifically
trained for Korean license plate detection. It processes vehicle images and extracts
license plate regions for subsequent OCR processing.

Key Features:
- Fine-tuned YOLO model for Korean license plate detection
- High-precision plate localization with confidence scoring
- Multiple plate format support (Korean standard, compact, etc.)
- Plate orientation and quality assessment
- Batch processing for multiple vehicles
- Integration with OCR pipeline for text extraction

Architecture:
- LicensePlateDetector: Core detection engine with YOLO integration
- PlateDetectionResult: Structured result with plate location and metadata
- PlateRegionProcessor: Image preprocessing for optimal OCR performance
- LicensePlateDetectionManager: Multi-stream detection coordinator
"""

import logging
import os
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple, Any
import threading
import numpy as np
import cv2
from ultralytics import YOLO
from pathlib import Path

# Configure logging
logger = logging.getLogger(__name__)


@dataclass
class PlateDetectionResult:
    """
    Result of license plate detection analysis.
    
    Contains detailed information about detected license plates including
    location, confidence, orientation, and preprocessed image data.
    """
    # Fields without default values
    detected: bool
    confidence: float
    bbox: Tuple[int, int, int, int]
    center_point: Tuple[float, float]
    width: int
    height: int
    area: int
    aspect_ratio: float
    original_image: np.ndarray
    cropped_plate: np.ndarray

    # Fields with default values
    rotation_angle: float = 0.0
    preprocessed_plate: Optional[np.ndarray] = None
    clarity_score: float = 0.0
    lighting_quality: float = 0.0
    ocr_readiness: float = 0.0
    raw_detection: Optional[Dict[str, Any]] = None
    model_version: str = "unknown"
    processing_time: float = 0.0
    
    def get_plate_summary(self) -> Dict[str, Any]:
        """Get summary of plate detection."""
        return {
            "detected": self.detected,
            "confidence": self.confidence,
            "bbox": self.bbox,
            "center": self.center_point,
            "dimensions": {"width": self.width, "height": self.height},
            "aspect_ratio": self.aspect_ratio,
            "rotation": self.rotation_angle,
            "quality_scores": {
                "clarity": self.clarity_score,
                "lighting": self.lighting_quality,
                "ocr_readiness": self.ocr_readiness
            }
        }


class PlateRegionProcessor:
    """
    Image preprocessing for license plate regions to optimize OCR performance.
    
    Handles image enhancement, noise reduction, perspective correction,
    and other preprocessing tasks to improve OCR accuracy.
    """
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        
        # Processing parameters
        self.target_height = config.get('target_height', 64)  # Standard height for OCR
        self.enhance_contrast = config.get('enhance_contrast', True)
        self.apply_denoising = config.get('apply_denoising', True)
        self.correct_perspective = config.get('correct_perspective', True)
        
    def preprocess_plate_region(self, plate_image: np.ndarray, 
                              rotation_angle: float = 0.0) -> Tuple[np.ndarray, Dict[str, Any]]:
        """
        Preprocess license plate region for optimal OCR performance.
        
        Args:
            plate_image: Cropped license plate image
            rotation_angle: Estimated rotation angle in degrees
            
        Returns:
            Tuple[np.ndarray, Dict[str, Any]]: Preprocessed image and processing metadata
        """
        processing_metadata = {}
        processed_image = plate_image.copy()
        
        try:
            # Step 1: Resize to standard height while maintaining aspect ratio
            processed_image, resize_info = self._resize_plate_image(processed_image)
            processing_metadata['resize'] = resize_info
            
            # Step 2: Rotation correction if needed
            if abs(rotation_angle) > 2.0:  # Only correct significant rotations
                processed_image, rotation_info = self._correct_rotation(processed_image, rotation_angle)
                processing_metadata['rotation_correction'] = rotation_info
            
            # Step 3: Perspective correction (if enabled and needed)
            if self.correct_perspective:
                processed_image, perspective_info = self._correct_perspective(processed_image)
                processing_metadata['perspective_correction'] = perspective_info
            
            # Step 4: Enhance contrast and brightness
            if self.enhance_contrast:
                processed_image, contrast_info = self._enhance_contrast(processed_image)
                processing_metadata['contrast_enhancement'] = contrast_info
            
            # Step 5: Noise reduction
            if self.apply_denoising:
                processed_image, denoise_info = self._apply_denoising(processed_image)
                processing_metadata['denoising'] = denoise_info
            
            # Step 6: Final sharpening
            processed_image, sharpen_info = self._apply_sharpening(processed_image)
            processing_metadata['sharpening'] = sharpen_info
            
            processing_metadata['success'] = True
            
        except Exception as e:
            logger.error(f"Error in plate preprocessing: {e}")
            processing_metadata['error'] = str(e)
            processing_metadata['success'] = False
        
        return processed_image, processing_metadata
    
    def _resize_plate_image(self, image: np.ndarray) -> Tuple[np.ndarray, Dict[str, Any]]:
        """Resize plate image to standard height."""
        original_height, original_width = image.shape[:2]
        
        if original_height == self.target_height:
            return image, {"resized": False, "original_size": (original_width, original_height)}
        
        # Calculate new width maintaining aspect ratio
        aspect_ratio = original_width / original_height
        new_width = int(self.target_height * aspect_ratio)
        
        # Resize image
        resized = cv2.resize(image, (new_width, self.target_height), interpolation=cv2.INTER_CUBIC)
        
        return resized, {
            "resized": True,
            "original_size": (original_width, original_height),
            "new_size": (new_width, self.target_height),
            "aspect_ratio": aspect_ratio
        }
    
    def _correct_rotation(self, image: np.ndarray, angle: float) -> Tuple[np.ndarray, Dict[str, Any]]:
        """Correct image rotation."""
        height, width = image.shape[:2]
        center = (width // 2, height // 2)
        
        # Create rotation matrix
        rotation_matrix = cv2.getRotationMatrix2D(center, -angle, 1.0)
        
        # Apply rotation
        corrected = cv2.warpAffine(image, rotation_matrix, (width, height), 
                                 flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE)
        
        return corrected, {"angle_corrected": angle, "method": "affine_transform"}
    
    def _correct_perspective(self, image: np.ndarray) -> Tuple[np.ndarray, Dict[str, Any]]:
        """Apply perspective correction if needed."""
        # Simple perspective correction - in production, this could be more sophisticated
        # For now, just apply a slight enhancement
        
        try:
            # Find contours to identify the plate boundary
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY) if len(image.shape) == 3 else image
            edges = cv2.Canny(gray, 50, 150)
            contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            
            if contours:
                # Find the largest contour (likely the plate boundary)
                largest_contour = max(contours, key=cv2.contourArea)
                
                # Approximate to quadrilateral
                epsilon = 0.02 * cv2.arcLength(largest_contour, True)
                approx = cv2.approxPolyDP(largest_contour, epsilon, True)
                
                if len(approx) == 4:
                    # We have a quadrilateral - apply perspective correction
                    height, width = image.shape[:2]
                    
                    # Define destination points (rectangle)
                    dst_points = np.array([
                        [0, 0],
                        [width - 1, 0], 
                        [width - 1, height - 1],
                        [0, height - 1]
                    ], dtype=np.float32)
                    
                    # Source points from detected quadrilateral
                    src_points = approx.reshape(4, 2).astype(np.float32)
                    
                    # Calculate perspective transform matrix
                    matrix = cv2.getPerspectiveTransform(src_points, dst_points)
                    
                    # Apply transform
                    corrected = cv2.warpPerspective(image, matrix, (width, height))
                    
                    return corrected, {"corrected": True, "method": "perspective_transform"}
            
            return image, {"corrected": False, "reason": "no_suitable_contour"}
            
        except Exception as e:
            return image, {"corrected": False, "error": str(e)}
    
    def _enhance_contrast(self, image: np.ndarray) -> Tuple[np.ndarray, Dict[str, Any]]:
        """Enhance image contrast and brightness."""
        # Convert to LAB color space for better contrast enhancement
        if len(image.shape) == 3:
            lab = cv2.cvtColor(image, cv2.COLOR_BGR2LAB)
            l_channel, a_channel, b_channel = cv2.split(lab)
        else:
            l_channel = image.copy()
        
        # Apply CLAHE (Contrast Limited Adaptive Histogram Equalization)
        clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8))
        enhanced_l = clahe.apply(l_channel)
        
        if len(image.shape) == 3:
            # Merge channels back
            enhanced_lab = cv2.merge([enhanced_l, a_channel, b_channel])
            enhanced = cv2.cvtColor(enhanced_lab, cv2.COLOR_LAB2BGR)
        else:
            enhanced = enhanced_l
        
        return enhanced, {"method": "CLAHE", "clip_limit": 3.0}
    
    def _apply_denoising(self, image: np.ndarray) -> Tuple[np.ndarray, Dict[str, Any]]:
        """Apply noise reduction."""
        if len(image.shape) == 3:
            # Color image denoising
            denoised = cv2.fastNlMeansDenoisingColored(image, None, 10, 10, 7, 21)
        else:
            # Grayscale image denoising
            denoised = cv2.fastNlMeansDenoising(image, None, 10, 7, 21)
        
        return denoised, {"method": "fastNlMeansDenoising"}
    
    def _apply_sharpening(self, image: np.ndarray) -> Tuple[np.ndarray, Dict[str, Any]]:
        """Apply image sharpening."""
        # Define sharpening kernel
        kernel = np.array([[-1, -1, -1],
                          [-1,  9, -1], 
                          [-1, -1, -1]], dtype=np.float32)
        
        # Apply sharpening
        sharpened = cv2.filter2D(image, -1, kernel)
        
        # Blend with original to avoid over-sharpening
        alpha = 0.7  # Weight for sharpened image
        result = cv2.addWeighted(sharpened, alpha, image, 1 - alpha, 0)
        
        return result, {"method": "unsharp_mask", "alpha": alpha}
    
    def assess_image_quality(self, image: np.ndarray) -> Dict[str, float]:
        """Assess image quality for OCR readiness."""
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY) if len(image.shape) == 3 else image
        
        # Calculate clarity (sharpness) using Laplacian variance
        laplacian_var = cv2.Laplacian(gray, cv2.CV_64F).var()
        clarity_score = min(laplacian_var / 1000.0, 1.0)  # Normalize
        
        # Calculate lighting quality (contrast and brightness)
        mean_brightness = np.mean(gray)
        brightness_score = 1.0 - abs(mean_brightness - 127) / 127  # Optimal around 127
        
        contrast = np.std(gray)
        contrast_score = min(contrast / 64.0, 1.0)  # Normalize
        
        lighting_quality = (brightness_score + contrast_score) / 2
        
        # Overall OCR readiness score
        ocr_readiness = (clarity_score + lighting_quality) / 2
        
        return {
            "clarity": clarity_score,
            "lighting": lighting_quality,
            "ocr_readiness": ocr_readiness
        }


class LicensePlateDetector:
    """
    Core license plate detection engine using fine-tuned YOLO model.
    
    Handles Korean license plate detection with high precision,
    including plate localization, orientation estimation, and quality assessment.
    """
    
    def __init__(self, model_path: str, config: Dict[str, Any]):
        self.model_path = model_path
        self.config = config
        self.model: Optional[YOLO] = None
        self.processor = PlateRegionProcessor(config)
        self.lock = threading.Lock()
        
        # Model configuration
        self.confidence_threshold = config.get('confidence_threshold', 0.7)
        self.iou_threshold = config.get('iou_threshold', 0.4)
        
        # Load model
        self._load_model()
        
        logger.info(f"LicensePlateDetector initialized with model: {model_path}")
    
    def _load_model(self) -> bool:
        """
        Load the fine-tuned license plate detection YOLO model.
        
        Returns:
            bool: True if model loaded successfully
        """
        try:
            if not os.path.exists(self.model_path):
                logger.error(f"Model file not found: {self.model_path}")
                return False
            
            logger.info(f"Loading license plate model from: {self.model_path}")
            
            # Load the fine-tuned YOLO model
            self.model = YOLO(self.model_path)
            
            # Configure model parameters
            self.model.conf = self.confidence_threshold
            self.model.iou = self.iou_threshold
            
            # Test model with dummy input
            dummy_frame = np.zeros((640, 640, 3), dtype=np.uint8)
            test_results = self.model(dummy_frame, verbose=False)
            
            logger.info(f"License plate model loaded successfully")
            logger.info(f"Model classes: {self.model.names}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to load license plate model: {e}")
            return False
    
    def detect_plates(self, image: np.ndarray, vehicle_bbox: Optional[Tuple[int, int, int, int]] = None) -> List[PlateDetectionResult]:
        """
        Detect license plates in vehicle image.
        
        Args:
            image: Input vehicle image
            vehicle_bbox: Optional vehicle bounding box to focus detection
            
        Returns:
            List[PlateDetectionResult]: List of detected license plates
        """
        import time
        start_time = time.time()
        
        if self.model is None:
            logger.error("Model not loaded")
            return []
        
        try:
            with self.lock:
                # Crop to vehicle region if bbox provided
                if vehicle_bbox:
                    x1, y1, x2, y2 = vehicle_bbox
                    detection_region = image[y1:y2, x1:x2]
                    offset_x, offset_y = x1, y1
                else:
                    detection_region = image
                    offset_x, offset_y = 0, 0
                
                # Run YOLO inference
                results = self.model(detection_region, verbose=False)
                
                # Process results
                plate_detections = []
                
                for result in results:
                    if result.boxes is not None:
                        boxes = result.boxes
                        
                        for i, box in enumerate(boxes):
                            x1, y1, x2, y2 = box.xyxy[0].cpu().numpy()
                            confidence = float(box.conf[0].cpu().numpy())
                            class_id = int(box.cls[0].cpu().numpy())
                            class_name = self.model.names.get(class_id, f"class_{class_id}")
                            
                            # Filter for license plate classes
                            if self._is_license_plate_class(class_name):
                                # Adjust coordinates to original image space
                                adjusted_bbox = (
                                    int(x1 + offset_x), int(y1 + offset_y),
                                    int(x2 + offset_x), int(y2 + offset_y)
                                )
                                
                                # Create plate detection result
                                plate_result = self._create_plate_result(
                                    image, adjusted_bbox, confidence, class_name, box
                                )
                                
                                if plate_result:
                                    plate_result.processing_time = time.time() - start_time
                                    plate_detections.append(plate_result)
                
                # Sort by confidence (highest first)
                plate_detections.sort(key=lambda x: x.confidence, reverse=True)
                
                logger.debug(f"Detected {len(plate_detections)} license plates")
                return plate_detections
                
        except Exception as e:
            logger.error(f"Error during plate detection: {e}")
            return []
    
    def _is_license_plate_class(self, class_name: str) -> bool:
        """Check if detected class is a license plate."""
        # Define license plate class names from your model
        plate_classes = [
            'license_plate', 'plate', 'number_plate',
            'korean_plate', 'car_plate', 'vehicle_plate',
            # Korean terms
            '번호판', '자동차번호판', '차량번호판'
        ]
        
        return class_name.lower() in [pc.lower() for pc in plate_classes]
    
    def _create_plate_result(self, image: np.ndarray, bbox: Tuple[int, int, int, int],
                           confidence: float, class_name: str, yolo_box) -> Optional[PlateDetectionResult]:
        """Create plate detection result from YOLO detection."""
        try:
            x1, y1, x2, y2 = bbox
            
            # Validate bbox
            if x2 <= x1 or y2 <= y1:
                return None
            
            # Ensure bbox is within image bounds
            h, w = image.shape[:2]
            x1 = max(0, min(x1, w-1))
            y1 = max(0, min(y1, h-1)) 
            x2 = max(x1+1, min(x2, w))
            y2 = max(y1+1, min(y2, h))
            
            # Calculate properties
            width = x2 - x1
            height = y2 - y1
            area = width * height
            center_point = ((x1 + x2) / 2, (y1 + y2) / 2)
            aspect_ratio = width / height if height > 0 else 0
            
            # Crop plate region
            cropped_plate = image[y1:y2, x1:x2]
            
            # Estimate rotation angle (simplified)
            rotation_angle = self._estimate_rotation(cropped_plate)
            
            # Preprocess plate image
            preprocessed_plate, processing_metadata = self.processor.preprocess_plate_region(
                cropped_plate, rotation_angle
            )
            
            # Assess image quality
            quality_metrics = self.processor.assess_image_quality(preprocessed_plate)
            
            # Create detection result
            result = PlateDetectionResult(
                detected=True,
                confidence=confidence,
                bbox=(x1, y1, x2, y2),
                center_point=center_point,
                width=width,
                height=height,
                area=area,
                aspect_ratio=aspect_ratio,
                rotation_angle=rotation_angle,
                original_image=image,
                cropped_plate=cropped_plate,
                preprocessed_plate=preprocessed_plate,
                clarity_score=quality_metrics['clarity'],
                lighting_quality=quality_metrics['lighting'],
                ocr_readiness=quality_metrics['ocr_readiness'],
                raw_detection={
                    "bbox": bbox,
                    "confidence": confidence,
                    "class_name": class_name,
                    "processing_metadata": processing_metadata
                },
                model_version=getattr(self.model, 'model_name', 'unknown')
            )
            
            return result
            
        except Exception as e:
            logger.error(f"Error creating plate result: {e}")
            return None
    
    def _estimate_rotation(self, plate_image: np.ndarray) -> float:
        """Estimate plate rotation angle."""
        try:
            # Convert to grayscale
            gray = cv2.cvtColor(plate_image, cv2.COLOR_BGR2GRAY) if len(plate_image.shape) == 3 else plate_image
            
            # Apply edge detection
            edges = cv2.Canny(gray, 50, 150, apertureSize=3)
            
            # Detect lines using Hough transform
            lines = cv2.HoughLines(edges, 1, np.pi/180, threshold=50)
            
            if lines is not None:
                angles = []
                for rho, theta in lines[0:min(10, len(lines))]:  # Use up to 10 lines
                    angle = (theta - np.pi/2) * 180 / np.pi  # Convert to degrees
                    angles.append(angle)
                
                if angles:
                    # Return median angle to reduce outlier influence
                    return float(np.median(angles))
            
            return 0.0
            
        except Exception as e:
            logger.debug(f"Rotation estimation failed: {e}")
            return 0.0
    
    def batch_detect_plates(self, images_with_bboxes: List[Tuple[np.ndarray, Optional[Tuple[int, int, int, int]]]]) -> List[List[PlateDetectionResult]]:
        """
        Batch detect license plates in multiple images.
        
        Args:
            images_with_bboxes: List of (image, vehicle_bbox) tuples
            
        Returns:
            List[List[PlateDetectionResult]]: Results for each input image
        """
        results = []
        
        for image, vehicle_bbox in images_with_bboxes:
            plate_results = self.detect_plates(image, vehicle_bbox)
            results.append(plate_results)
        
        return results
    
    def get_model_info(self) -> Dict[str, Any]:
        """Get information about the loaded model."""
        if not self.model:
            return {"status": "not_loaded"}
        
        return {
            "status": "loaded",
            "model_path": self.model_path,
            "classes": list(self.model.names.values()) if hasattr(self.model, 'names') else [],
            "confidence_threshold": self.confidence_threshold,
            "iou_threshold": self.iou_threshold
        }


class LicensePlateDetectionManager:
    """
    Multi-stream license plate detection coordinator.
    
    Manages license plate detection across multiple CCTV streams,
    coordinates with vehicle tracker and parking monitor.
    """
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.detector: Optional[LicensePlateDetector] = None
        self.lock = threading.Lock()
        
        # Load detector configuration
        self.detector_config = config.get('models', {}).get('license_plate_detector', {})
        self.model_path = self.detector_config.get('path', '')
        
        self._initialize_detector()
        
        logger.info("LicensePlateDetectionManager initialized")
    
    def _initialize_detector(self) -> bool:
        """Initialize the license plate detector."""
        try:
            if not os.path.exists(self.model_path):
                logger.error(f"Detector model not found: {self.model_path}")
                return False
            
            self.detector = LicensePlateDetector(self.model_path, self.detector_config)
            return self.detector.model is not None
            
        except Exception as e:
            logger.error(f"Failed to initialize detector: {e}")
            return False
    
    def detect_vehicle_plates(self, vehicle_image: np.ndarray, 
                            vehicle_bbox: Optional[Tuple[int, int, int, int]] = None) -> List[PlateDetectionResult]:
        """
        Detect license plates for a vehicle.
        
        Args:
            vehicle_image: Image containing the vehicle
            vehicle_bbox: Optional vehicle bounding box
            
        Returns:
            List[PlateDetectionResult]: Detected license plates
        """
        if not self.detector:
            logger.error("Detector not initialized")
            return []
        
        return self.detector.detect_plates(vehicle_image, vehicle_bbox)
    
    def is_ready(self) -> bool:
        """Check if detector is ready for use."""
        return self.detector is not None and self.detector.model is not None
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get detector statistics and status."""
        return {
            "ready": self.is_ready(),
            "model_info": self.detector.get_model_info() if self.detector else {},
            "config": self.detector_config
        }


# Global instance - will be initialized by main application
license_plate_detector: Optional[LicensePlateDetectionManager] = None


def initialize_license_plate_detector(config: Dict[str, Any]) -> bool:
    """
    Initialize the global license plate detector instance.
    
    Args:
        config: Configuration dictionary from config.yaml
        
    Returns:
        bool: True if initialization successful
    """
    global license_plate_detector
    
    try:
        license_plate_detector = LicensePlateDetectionManager(config)
        success = license_plate_detector.is_ready()
        
        if success:
            logger.info("License plate detector initialized successfully")
        else:
            logger.error("License plate detector initialization failed")
        
        return success
        
    except Exception as e:
        logger.error(f"Failed to initialize license plate detector: {e}")
        return False


def get_license_plate_detector() -> Optional[LicensePlateDetectionManager]:
    """
    Get the global license plate detector instance.
    
    Returns:
        Optional[LicensePlateDetectionManager]: Detector instance or None if not initialized
    """
    return license_plate_detector