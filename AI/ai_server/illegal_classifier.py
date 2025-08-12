"""
Illegal Parking Classifier Module for Illegal Parking Detection System

This module implements the illegal parking classification system using a fine-tuned YOLO model
to analyze parking situations and determine if they constitute illegal parking violations.
It processes individual parking events and provides detailed classification results.

Key Features:
- Fine-tuned YOLO model for illegal parking situation classification  
- Context-aware analysis considering location, time, and parking patterns
- Multi-class violation classification (crosswalk, no-parking zone, etc.)
- Confidence scoring and uncertainty quantification
- Batch processing for multiple parking events
- Integration with parking monitor for violation analysis

Architecture:
- IllegalParkingClassifier: Core classification engine with YOLO integration
- ClassificationResult: Structured result with violation types and confidence
- ContextAnalyzer: Environmental and temporal context analysis
- ViolationClassifier: Multi-stream classification coordinator
"""

import logging
import os
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple, Any, Union
from enum import Enum
import threading
import numpy as np
import cv2
from ultralytics import YOLO
from pathlib import Path

from parking_monitor import ParkingEvent, ViolationType

# Configure logging
logger = logging.getLogger(__name__)


class IllegalParkingType(Enum):
    """Types of illegal parking situations that can be detected by YOLO model."""
    CROSSWALK_VIOLATION = "crosswalk_violation"
    NO_PARKING_ZONE = "no_parking_zone" 
    FIRE_HYDRANT_BLOCKING = "fire_hydrant_blocking"
    HANDICAP_SPOT_VIOLATION = "handicap_spot_violation"
    LOADING_ZONE_VIOLATION = "loading_zone_violation"
    BUS_STOP_BLOCKING = "bus_stop_blocking"
    INTERSECTION_BLOCKING = "intersection_blocking"
    SIDEWALK_PARKING = "sidewalk_parking"
    DOUBLE_PARKING = "double_parking"
    YELLOW_LINE_VIOLATION = "yellow_line_violation"
    
    # Korean-specific violations
    KOREAN_NO_PARKING = "한국_주차금지"
    KOREAN_CROSSWALK = "한국_횡단보도"


@dataclass
class ClassificationResult:
    """
    Result of illegal parking classification analysis.
    
    Contains detailed information about the classification decision,
    confidence scores, detected violation types, and supporting evidence.
    """
    # Fields without default values
    is_illegal: bool
    overall_confidence: float
    detected_violations: List[IllegalParkingType]
    violation_confidences: Dict[IllegalParkingType, float]
    raw_detections: List[Dict[str, Any]]
    decision_factors: List[str]
    uncertainty_factors: List[str]

    # Fields with default values
    processed_image_path: Optional[str] = None
    model_version: str = "unknown"
    processing_time: float = 0.0
    image_quality_score: float = 1.0
    
    def get_primary_violation(self) -> Optional[IllegalParkingType]:
        """Get the primary (highest confidence) violation type."""
        if not self.detected_violations:
            return None
        
        # Return violation with highest confidence
        return max(self.detected_violations, 
                  key=lambda v: self.violation_confidences.get(v, 0.0))
    
    def get_violation_summary(self) -> Dict[str, Any]:
        """Get summary of violation analysis."""
        return {
            "is_illegal": self.is_illegal,
            "confidence": self.overall_confidence,
            "primary_violation": self.get_primary_violation().value if self.get_primary_violation() else None,
            "violation_count": len(self.detected_violations),
            "all_violations": [v.value for v in self.detected_violations],
            "decision_factors": self.decision_factors,
            "image_quality": self.image_quality_score
        }


class ContextAnalyzer:
    """
    Analyzes environmental and temporal context for parking classification.
    
    Provides additional context information that can influence the classification
    decision, such as time of day, weather conditions, traffic patterns, etc.
    """
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        
    def analyze_temporal_context(self, timestamp: float, location: Tuple[float, float]) -> Dict[str, Any]:
        """
        Analyze temporal context (time of day, day of week, etc.).
        
        Args:
            timestamp: Unix timestamp of the event
            location: Location coordinates
            
        Returns:
            Dict containing temporal context information
        """
        from datetime import datetime
        
        dt = datetime.fromtimestamp(timestamp)
        
        context = {
            "hour": dt.hour,
            "day_of_week": dt.weekday(),
            "is_weekend": dt.weekday() >= 5,
            "is_business_hours": 9 <= dt.hour <= 17,
            "is_peak_hours": dt.hour in [8, 9, 17, 18, 19],
            "is_night_time": dt.hour < 6 or dt.hour > 22,
            "season": self._get_season(dt.month)
        }
        
        return context
    
    def analyze_spatial_context(self, image: np.ndarray, location: Tuple[float, float]) -> Dict[str, Any]:
        """
        Analyze spatial context from image and location.
        
        Args:
            image: Input image for analysis
            location: Location coordinates
            
        Returns:
            Dict containing spatial context information
        """
        context = {
            "image_brightness": np.mean(cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)),
            "image_contrast": np.std(cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)),
            "image_quality": self._assess_image_quality(image),
            "dominant_colors": self._get_dominant_colors(image),
            "edge_density": self._calculate_edge_density(image)
        }
        
        return context
    
    def _get_season(self, month: int) -> str:
        """Get season from month number."""
        if month in [12, 1, 2]:
            return "winter"
        elif month in [3, 4, 5]:
            return "spring"
        elif month in [6, 7, 8]:
            return "summer"
        else:
            return "autumn"
    
    def _assess_image_quality(self, image: np.ndarray) -> float:
        """Assess image quality score (0.0 to 1.0)."""
        # Simple quality assessment based on sharpness and contrast
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        
        # Calculate sharpness using Laplacian variance
        laplacian_var = cv2.Laplacian(gray, cv2.CV_64F).var()
        sharpness = min(laplacian_var / 1000.0, 1.0)  # Normalize
        
        # Calculate contrast
        contrast = gray.std() / 128.0  # Normalize to 0-1
        
        # Combine metrics
        quality = (sharpness + contrast) / 2
        return min(quality, 1.0)
    
    def _get_dominant_colors(self, image: np.ndarray, k: int = 3) -> List[Tuple[int, int, int]]:
        """Get dominant colors in the image."""
        # Reshape image for k-means
        data = image.reshape((-1, 3))
        data = np.float32(data)
        
        # Apply k-means clustering
        criteria = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 20, 1.0)
        _, labels, centers = cv2.kmeans(data, k, None, criteria, 10, cv2.KMEANS_RANDOM_CENTERS)
        
        # Convert back to integers
        centers = np.uint8(centers)
        
        return [tuple(center) for center in centers]
    
    def _calculate_edge_density(self, image: np.ndarray) -> float:
        """Calculate edge density in the image."""
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        edges = cv2.Canny(gray, 50, 150)
        
        # Calculate ratio of edge pixels to total pixels
        edge_density = np.sum(edges > 0) / edges.size
        return edge_density


class IllegalParkingClassifier:
    """
    Core illegal parking classification engine using fine-tuned YOLO model.
    
    Handles loading the illegal parking classification model, processing images,
    and generating detailed classification results with confidence scores.
    """
    
    def __init__(self, model_path: str, config: Dict[str, Any]):
        self.model_path = model_path
        self.config = config
        self.model: Optional[YOLO] = None
        self.context_analyzer = ContextAnalyzer(config)
        self.lock = threading.Lock()
        
        # Model configuration
        self.confidence_threshold = config.get('confidence_threshold', 0.6)
        self.iou_threshold = config.get('iou_threshold', 0.45)
        
        # Load model
        self._load_model()
        
        logger.info(f"IllegalParkingClassifier initialized with model: {model_path}")
    
    def _load_model(self) -> bool:
        """
        Load the fine-tuned illegal parking YOLO model.
        
        Returns:
            bool: True if model loaded successfully
        """
        try:
            if not os.path.exists(self.model_path):
                logger.error(f"Model file not found: {self.model_path}")
                return False
            
            logger.info(f"Loading illegal parking model from: {self.model_path}")
            
            # Load the fine-tuned YOLO model
            self.model = YOLO(self.model_path)
            
            # Configure model parameters
            self.model.conf = self.confidence_threshold
            self.model.iou = self.iou_threshold
            
            # Test model with dummy input
            dummy_frame = np.zeros((640, 640, 3), dtype=np.uint8)
            test_results = self.model(dummy_frame, verbose=False)
            
            logger.info(f"Illegal parking model loaded successfully")
            logger.info(f"Model classes: {self.model.names}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to load illegal parking model: {e}")
            return False
    
    def classify_parking_situation(self, image: np.ndarray, 
                                 parking_event: Optional[ParkingEvent] = None,
                                 context_info: Optional[Dict[str, Any]] = None) -> ClassificationResult:
        """
        Classify whether a parking situation is illegal.
        
        Args:
            image: Input image showing the parking situation
            parking_event: Optional parking event data for context
            context_info: Optional additional context information
            
        Returns:
            ClassificationResult: Detailed classification result
        """
        import time
        start_time = time.time()
        
        if self.model is None:
            logger.error("Model not loaded")
            return self._create_error_result("Model not loaded")
        
        try:
            with self.lock:
                # Run YOLO inference
                results = self.model(image, verbose=False)
                
                # Process results
                classification_result = self._process_yolo_results(
                    results, image, parking_event, context_info
                )
                
                # Add processing time
                classification_result.processing_time = time.time() - start_time
                
                return classification_result
                
        except Exception as e:
            logger.error(f"Error during classification: {e}")
            return self._create_error_result(f"Classification error: {str(e)}")
    
    def _process_yolo_results(self, results, image: np.ndarray,
                            parking_event: Optional[ParkingEvent] = None,
                            context_info: Optional[Dict[str, Any]] = None) -> ClassificationResult:
        """Process YOLO results and generate classification decision."""
        
        detected_violations = []
        violation_confidences = {}
        raw_detections = []
        decision_factors = []
        uncertainty_factors = []
        
        # Analyze context
        if parking_event:
            temporal_context = self.context_analyzer.analyze_temporal_context(
                parking_event.start_time, parking_event.location
            )
            spatial_context = self.context_analyzer.analyze_spatial_context(
                image, parking_event.location
            )
        else:
            temporal_context = {}
            spatial_context = self.context_analyzer.analyze_spatial_context(
                image, (0, 0)
            )
        
        # Process YOLO detections
        for result in results:
            if result.boxes is not None:
                boxes = result.boxes
                
                for i, box in enumerate(boxes):
                    x1, y1, x2, y2 = box.xyxy[0].cpu().numpy()
                    confidence = float(box.conf[0].cpu().numpy())
                    class_id = int(box.cls[0].cpu().numpy())
                    class_name = self.model.names.get(class_id, f"class_{class_id}")
                    
                    # Store raw detection
                    detection = {
                        "bbox": [int(x1), int(y1), int(x2), int(y2)],
                        "confidence": confidence,
                        "class_id": class_id,
                        "class_name": class_name
                    }
                    raw_detections.append(detection)
                    
                    # Map class name to violation type
                    violation_type = self._map_class_to_violation(class_name)
                    if violation_type:
                        detected_violations.append(violation_type)
                        violation_confidences[violation_type] = confidence
                        
                        decision_factors.append(
                            f"Detected {violation_type.value} with {confidence:.2f} confidence"
                        )
        
        # Determine overall classification
        is_illegal = len(detected_violations) > 0
        
        # Calculate overall confidence
        if detected_violations:
            # Use maximum confidence among detected violations
            overall_confidence = max(violation_confidences.values())
            
            # Apply context-based adjustments
            overall_confidence = self._apply_context_adjustments(
                overall_confidence, temporal_context, spatial_context, 
                parking_event, decision_factors, uncertainty_factors
            )
        else:
            # No violations detected
            overall_confidence = 1.0 - max([d["confidence"] for d in raw_detections] if raw_detections else [0.0])
            decision_factors.append("No illegal parking violations detected")
        
        # Assess image quality
        image_quality = spatial_context.get("image_quality", 1.0)
        if image_quality < 0.5:
            uncertainty_factors.append(f"Low image quality: {image_quality:.2f}")
            overall_confidence *= 0.8  # Reduce confidence for poor quality images
        
        return ClassificationResult(
            is_illegal=is_illegal,
            overall_confidence=max(0.0, min(1.0, overall_confidence)),
            detected_violations=detected_violations,
            violation_confidences=violation_confidences,
            raw_detections=raw_detections,
            decision_factors=decision_factors,
            uncertainty_factors=uncertainty_factors,
            model_version=getattr(self.model, 'model_name', 'unknown'),
            image_quality_score=image_quality
        )
    
    def _map_class_to_violation(self, class_name: str) -> Optional[IllegalParkingType]:
        """Map YOLO class name to violation type."""
        # Define mapping from model class names to violation types
        # Adjust these mappings based on your specific model's classes
        
        class_mappings = {
            # English class names
            'crosswalk_violation': IllegalParkingType.CROSSWALK_VIOLATION,
            'no_parking': IllegalParkingType.NO_PARKING_ZONE,
            'fire_hydrant': IllegalParkingType.FIRE_HYDRANT_BLOCKING,
            'handicap_violation': IllegalParkingType.HANDICAP_SPOT_VIOLATION,
            'loading_zone': IllegalParkingType.LOADING_ZONE_VIOLATION,
            'bus_stop': IllegalParkingType.BUS_STOP_BLOCKING,
            'intersection': IllegalParkingType.INTERSECTION_BLOCKING,
            'sidewalk': IllegalParkingType.SIDEWALK_PARKING,
            'double_parking': IllegalParkingType.DOUBLE_PARKING,
            'yellow_line': IllegalParkingType.YELLOW_LINE_VIOLATION,
            
            # Korean class names (if your model uses them)
            '횡단보도': IllegalParkingType.KOREAN_CROSSWALK,
            '주차금지': IllegalParkingType.KOREAN_NO_PARKING,
            '불법주차': IllegalParkingType.NO_PARKING_ZONE,
            
            # Generic terms that might appear in your model
            'illegal': IllegalParkingType.NO_PARKING_ZONE,
            'violation': IllegalParkingType.NO_PARKING_ZONE
        }
        
        # Try exact match first
        if class_name.lower() in class_mappings:
            return class_mappings[class_name.lower()]
        
        # Try partial matches
        for key, violation_type in class_mappings.items():
            if key.lower() in class_name.lower():
                return violation_type
        
        logger.debug(f"Unknown violation class: {class_name}")
        return None
    
    def _apply_context_adjustments(self, base_confidence: float, 
                                 temporal_context: Dict[str, Any],
                                 spatial_context: Dict[str, Any],
                                 parking_event: Optional[ParkingEvent],
                                 decision_factors: List[str],
                                 uncertainty_factors: List[str]) -> float:
        """Apply context-based confidence adjustments."""
        
        adjusted_confidence = base_confidence
        
        # Temporal adjustments
        if temporal_context.get('is_night_time', False):
            # Reduce confidence for nighttime detections due to lighting
            adjusted_confidence *= 0.9
            uncertainty_factors.append("Nighttime detection - reduced visibility")
        
        if temporal_context.get('is_business_hours', False):
            # Higher confidence during business hours when violations are more likely
            adjusted_confidence *= 1.1
            decision_factors.append("Business hours - increased violation likelihood")
        
        # Spatial adjustments
        image_brightness = spatial_context.get('image_brightness', 128)
        if image_brightness < 50 or image_brightness > 200:
            # Poor lighting conditions
            adjusted_confidence *= 0.85
            uncertainty_factors.append(f"Poor lighting conditions: {image_brightness:.1f}")
        
        # Parking event duration adjustment
        if parking_event and parking_event.duration:
            if parking_event.duration > 300:  # 5 minutes
                # Longer parking duration increases violation likelihood
                duration_factor = min(1.2, 1.0 + (parking_event.duration - 300) / 1800)
                adjusted_confidence *= duration_factor
                decision_factors.append(f"Long parking duration: {parking_event.duration:.1f}s")
        
        return max(0.0, min(1.0, adjusted_confidence))
    
    def _create_error_result(self, error_message: str) -> ClassificationResult:
        """Create error result for failed classifications."""
        return ClassificationResult(
            is_illegal=False,
            overall_confidence=0.0,
            detected_violations=[],
            violation_confidences={},
            raw_detections=[],
            decision_factors=[f"Error: {error_message}"],
            uncertainty_factors=["Classification failed"]
        )
    
    def batch_classify(self, image_batches: List[Tuple[np.ndarray, Optional[ParkingEvent]]]) -> List[ClassificationResult]:
        """
        Classify multiple parking situations in batch.
        
        Args:
            image_batches: List of (image, parking_event) tuples
            
        Returns:
            List[ClassificationResult]: Results for each input
        """
        results = []
        
        for image, parking_event in image_batches:
            result = self.classify_parking_situation(image, parking_event)
            results.append(result)
        
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


class ViolationClassifier:
    """
    Multi-stream illegal parking classification coordinator.
    
    Manages illegal parking classification across multiple CCTV streams,
    coordinates with parking monitor, and provides centralized classification services.
    """
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.classifier: Optional[IllegalParkingClassifier] = None
        self.lock = threading.Lock()
        
        # Load classifier configuration
        self.classifier_config = config.get('models', {}).get('illegal_classifier', {})
        self.model_path = self.classifier_config.get('path', '')
        
        self._initialize_classifier()
        
        logger.info("ViolationClassifier initialized")
    
    def _initialize_classifier(self) -> bool:
        """Initialize the illegal parking classifier."""
        try:
            if not os.path.exists(self.model_path):
                logger.error(f"Classifier model not found: {self.model_path}")
                return False
            
            self.classifier = IllegalParkingClassifier(self.model_path, self.classifier_config)
            return self.classifier.model is not None
            
        except Exception as e:
            logger.error(f"Failed to initialize classifier: {e}")
            return False
    
    def classify_violation(self, image: np.ndarray, 
                          parking_event: ParkingEvent,
                          context_info: Optional[Dict[str, Any]] = None) -> ClassificationResult:
        """
        Classify a parking violation event.
        
        Args:
            image: Image showing the parking situation
            parking_event: Parking event data
            context_info: Additional context information
            
        Returns:
            ClassificationResult: Classification result
        """
        if not self.classifier:
            logger.error("Classifier not initialized")
            return ClassificationResult(
                is_illegal=False,
                overall_confidence=0.0,
                detected_violations=[],
                violation_confidences={},
                raw_detections=[],
                decision_factors=["Classifier not initialized"],
                uncertainty_factors=["System error"]
            )
        
        return self.classifier.classify_parking_situation(image, parking_event, context_info)
    
    def is_ready(self) -> bool:
        """Check if classifier is ready for use."""
        return self.classifier is not None and self.classifier.model is not None
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get classifier statistics and status."""
        return {
            "ready": self.is_ready(),
            "model_info": self.classifier.get_model_info() if self.classifier else {},
            "config": self.classifier_config
        }


# Global instance - will be initialized by main application
violation_classifier: Optional[ViolationClassifier] = None


def initialize_violation_classifier(config: Dict[str, Any]) -> bool:
    """
    Initialize the global violation classifier instance.
    
    Args:
        config: Configuration dictionary from config.yaml
        
    Returns:
        bool: True if initialization successful
    """
    global violation_classifier
    
    try:
        violation_classifier = ViolationClassifier(config)
        success = violation_classifier.is_ready()
        
        if success:
            logger.info("Violation classifier initialized successfully")
        else:
            logger.error("Violation classifier initialization failed")
        
        return success
        
    except Exception as e:
        logger.error(f"Failed to initialize violation classifier: {e}")
        return False


def get_violation_classifier() -> Optional[ViolationClassifier]:
    """
    Get the global violation classifier instance.
    
    Returns:
        Optional[ViolationClassifier]: Classifier instance or None if not initialized
    """
    return violation_classifier