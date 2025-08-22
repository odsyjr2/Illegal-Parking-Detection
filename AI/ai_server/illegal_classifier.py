"""
YOLO-seg + timm ResNet Illegal Parking Classifier Module

This module implements the illegal parking classification system using YOLO-seg for 
segmentation and timm ResNet for final classification. It replaces the previous 
YOLO-only approach with a two-stage pipeline that provides more accurate results.

Key Features:
- YOLO-seg model for vehicle and lane segmentation (9 classes)
- timm ResNet model for final classification (danger, normal, violation)
- Polygon to mask conversion with class mapping
- VLO format generation for ResNet input
- Seamless API compatibility with existing system

Architecture:
- YOLOSegResNetClassifier: Main classifier with two-stage pipeline
- SegmentationProcessor: Handles YOLO-seg output processing
- MaskConverter: Converts segmentation to ResNet input format
- ViolationClassifier: Maintains compatibility with existing API
"""

import logging
import os
import time
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple, Any, Union
from enum import Enum
import threading
import numpy as np
import cv2
from PIL import Image
import torch
import timm
from ultralytics import YOLO
from pathlib import Path

from parking_monitor import ParkingEvent, ViolationType

# Configure logging
logger = logging.getLogger(__name__)


class IllegalParkingType(Enum):
    """Types of illegal parking situations detected by the ResNet classifier."""
    DANGER = "danger"
    NORMAL = "normal" 
    VIOLATION = "violation"


@dataclass
class ClassificationResult:
    """
    Result of YOLO-seg + ResNet classification analysis.
    
    Maintains compatibility with existing API while supporting new pipeline.
    """
    # Core results (compatible with existing API)
    is_illegal: bool
    overall_confidence: float
    
    # Extended results for new pipeline
    detected_violations: List[IllegalParkingType]
    violation_confidences: Dict[IllegalParkingType, float]
    raw_detections: List[Dict[str, Any]]
    decision_factors: List[str]
    uncertainty_factors: List[str]
    
    # Segmentation specific results
    segmentation_results: Optional[Dict[str, Any]] = None
    vehicle_mask_bbox: Optional[Tuple[int, int, int, int]] = None
    
    # Metadata
    processed_image_path: Optional[str] = None
    model_version: str = "yolo_seg_resnet_v1"
    processing_time: float = 0.0
    image_quality_score: float = 1.0
    
    def get_primary_violation(self) -> Optional[IllegalParkingType]:
        """Get the primary (highest confidence) violation type."""
        if not self.detected_violations:
            return None
        
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
            "image_quality": self.image_quality_score,
            "vehicle_mask_bbox": self.vehicle_mask_bbox
        }


class SegmentationProcessor:
    """Processes YOLO-seg segmentation results."""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        
        # Class mappings from config
        class_mapping = config.get('class_mapping', {})
        self.vehicle_types = class_mapping.get('vehicle_types', [
            'vehicle_car', 'vehicle_bus', 'vehicle_truck', 'vehicle_bike'
        ])
        self.lane_types = class_mapping.get('lane_types', [
            'lane_shoulder_single_solid', 'lane_shoulder_double_solid', 
            'lane_shoulder_single_dashed', 'lane_shoulder_left_dashed_double',
            'lane_shoulder_right_dashed_double'
        ])
        
    def process_segmentation_results(self, seg_results, image_shape: Tuple[int, int]) -> Dict[str, Any]:
        """
        Process YOLO-seg results and extract segmentation data.
        
        Args:
            seg_results: YOLO segmentation results
            image_shape: (height, width) of original image
            
        Returns:
            Dict containing processed segmentation data
        """
        height, width = image_shape
        processed_data = {
            'masks': {},
            'polygons': {},
            'class_names': {},
            'confidences': {}
        }
        
        try:
            for result in seg_results:
                if result.masks is not None:
                    masks = result.masks.data.cpu().numpy()  # (N, H, W)
                    boxes = result.boxes
                    
                    for i, mask in enumerate(masks):
                        # Get class info
                        class_id = int(boxes.cls[i].cpu().numpy())
                        confidence = float(boxes.conf[i].cpu().numpy())
                        class_name = self._get_class_name(class_id)
                        
                        # Resize mask to original image size
                        resized_mask = cv2.resize(mask.astype(np.uint8), (width, height))
                        
                        # Store results
                        mask_id = f"{class_name}_{i}"
                        processed_data['masks'][mask_id] = resized_mask
                        processed_data['class_names'][mask_id] = class_name
                        processed_data['confidences'][mask_id] = confidence
                        
                        # Extract polygon from mask
                        contours, _ = cv2.findContours(resized_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
                        if contours:
                            # Use largest contour
                            largest_contour = max(contours, key=cv2.contourArea)
                            polygon = largest_contour.reshape(-1, 2)
                            processed_data['polygons'][mask_id] = polygon
                        
        except Exception as e:
            logger.error(f"Error processing segmentation results: {e}")
            
        return processed_data
    
    def _get_class_name(self, class_id: int) -> str:
        """Get class name from class ID."""
        # Default YOLO-seg class names based on provided mapping
        class_names = {
            0: 'vehicle_car',
            1: 'vehicle_bus', 
            2: 'vehicle_truck',
            3: 'vehicle_bike',
            4: 'lane_shoulder_single_solid',
            5: 'lane_shoulder_double_solid',
            6: 'lane_shoulder_single_dashed',
            7: 'lane_shoulder_left_dashed_double',
            8: 'lane_shoulder_right_dashed_double'
        }
        return class_names.get(class_id, f'unknown_{class_id}')


class MaskConverter:
    """Converts segmentation masks to ResNet input format."""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        
        # Class mappings
        class_mapping = config.get('class_mapping', {})
        self.vehicle_types = class_mapping.get('vehicle_types', [
            'vehicle_car', 'vehicle_bus', 'vehicle_truck', 'vehicle_bike'
        ])
        self.lane_types = class_mapping.get('lane_types', [
            'lane_shoulder_single_solid', 'lane_shoulder_double_solid', 
            'lane_shoulder_single_dashed', 'lane_shoulder_left_dashed_double',
            'lane_shoulder_right_dashed_double'
        ])
    
    def convert_seg_to_4class(self, seg_data: Dict[str, Any], image_shape: Tuple[int, int]) -> np.ndarray:
        """
        Convert YOLO-seg 9-class results to 4-class mask.
        
        Args:
            seg_data: Processed segmentation data
            image_shape: (height, width) of original image
            
        Returns:
            4-class mask: 0=background, 1=vehicle, 2=lane, 3=overlap
        """
        height, width = image_shape
        
        # Initialize masks
        vehicle_mask = np.zeros((height, width), dtype=np.uint8)
        lane_mask = np.zeros((height, width), dtype=np.uint8)
        
        # Process each segmented object
        for mask_id, mask in seg_data['masks'].items():
            class_name = seg_data['class_names'][mask_id]
            
            if class_name in self.vehicle_types:
                vehicle_mask = np.logical_or(vehicle_mask, mask).astype(np.uint8)
            elif class_name in self.lane_types:
                lane_mask = np.logical_or(lane_mask, mask).astype(np.uint8)
        
        # Create 4-class mask
        four_class_mask = np.zeros((height, width), dtype=np.uint8)
        
        # Assign classes
        four_class_mask[vehicle_mask == 1] = 1  # vehicle
        four_class_mask[lane_mask == 1] = 2     # lane
        
        # Find overlap (vehicle AND lane)
        overlap_mask = np.logical_and(vehicle_mask, lane_mask)
        four_class_mask[overlap_mask] = 3       # overlap
        
        # background remains 0
        
        return four_class_mask
    
    def mask_to_VLO(self, mask_img: np.ndarray, mask_mode: str = "id") -> np.ndarray:
        """
        Convert 4-class mask to VLO format for ResNet input.
        
        Args:
            mask_img: 4-class mask (H, W) with values 0,1,2,3
            mask_mode: "id" for ID-based mask, "color" for color-based (not used here)
            
        Returns:
            VLO format array (3, H, W) float32 in [0,1]
        """
        # Extract vehicle, lane, overlap masks
        V = (mask_img == 1).astype(np.float32)  # vehicle
        L = (mask_img == 2).astype(np.float32)  # lane  
        O = (mask_img == 3).astype(np.float32)  # overlap
        
        # Stack to create (3, H, W) format
        vlo = np.stack([V, L, O], axis=0)
        
        return vlo
    
    def extract_vehicle_mask_bbox(self, four_class_mask: np.ndarray, 
                                 original_bbox: Tuple[int, int, int, int]) -> Tuple[int, int, int, int]:
        """
        Extract bbox from vehicle mask for cropping.
        
        Args:
            four_class_mask: 4-class mask array
            original_bbox: Original vehicle bbox (x1, y1, x2, y2)
            
        Returns:
            Vehicle mask bbox (x1, y1, x2, y2)
        """
        # Extract vehicle pixels (class 1 and 3)
        vehicle_pixels = np.logical_or(four_class_mask == 1, four_class_mask == 3)
        
        if not np.any(vehicle_pixels):
            # No vehicle mask found, return original bbox
            logger.warning("No vehicle mask found, using original bbox")
            return original_bbox
        
        # Find bounding box of vehicle pixels
        rows, cols = np.where(vehicle_pixels)
        
        if len(rows) == 0:
            return original_bbox
            
        y1, y2 = np.min(rows), np.max(rows) + 1
        x1, x2 = np.min(cols), np.max(cols) + 1
        
        return (int(x1), int(y1), int(x2), int(y2))


class YOLOSegResNetClassifier:
    """
    Main classifier using YOLO-seg + timm ResNet pipeline.
    
    Implements two-stage classification:
    1. YOLO-seg for vehicle/lane segmentation
    2. timm ResNet for final violation classification
    """
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        
        # Model paths and settings
        yolo_config = config.get('yolo_seg', {})
        resnet_config = config.get('resnet', {})
        
        self.yolo_path = yolo_config.get('path', '')
        self.resnet_path = resnet_config.get('path', '')
        self.resnet_model_name = resnet_config.get('model_name', 'resnet50')
        self.resnet_num_classes = resnet_config.get('num_classes', 3)
        self.device = resnet_config.get('device', 'cpu')
        
        # Models
        self.yolo_model: Optional[YOLO] = None
        self.resnet_model: Optional[torch.nn.Module] = None
        
        # Processors
        self.seg_processor = SegmentationProcessor(config)
        self.mask_converter = MaskConverter(config)
        
        # Threading
        self.lock = threading.Lock()
        
        # Load models
        self._load_models()
        
        logger.info("YOLOSegResNetClassifier initialized")
    
    def _load_models(self) -> bool:
        """Load both YOLO-seg and timm ResNet models."""
        success = True
        
        # Load YOLO-seg model
        success &= self._load_yolo_seg_model()
        
        # Load timm ResNet model
        success &= self._load_timm_resnet_model()
        
        return success
    
    def _load_yolo_seg_model(self) -> bool:
        """Load YOLO-seg segmentation model."""
        try:
            if not os.path.exists(self.yolo_path):
                logger.error(f"YOLO-seg model not found: {self.yolo_path}")
                return False
            
            logger.info(f"Loading YOLO-seg model from: {self.yolo_path}")
            
            self.yolo_model = YOLO(self.yolo_path)
            
            # Test with dummy input
            dummy_frame = np.zeros((640, 640, 3), dtype=np.uint8)
            test_results = self.yolo_model(dummy_frame, verbose=False)
            
            logger.info("YOLO-seg model loaded successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to load YOLO-seg model: {e}")
            return False
    
    def _load_timm_resnet_model(self) -> bool:
        """Load timm ResNet classification model."""
        try:
            if not os.path.exists(self.resnet_path):
                logger.error(f"ResNet model not found: {self.resnet_path}")
                return False
            
            logger.info(f"Loading timm ResNet model: {self.resnet_model_name}")
            
            # Create timm model
            self.resnet_model = timm.create_model(
                self.resnet_model_name, 
                pretrained=False,
                num_classes=self.resnet_num_classes,
                in_chans=3  # VLO format has 3 channels
            )
            
            # Load trained weights
            logger.info(f"Loading ResNet weights from: {self.resnet_path}")
            checkpoint = torch.load(self.resnet_path, map_location=self.device)
            
            # Handle different checkpoint formats
            if 'model_state_dict' in checkpoint:
                self.resnet_model.load_state_dict(checkpoint['model_state_dict'])
            elif 'state_dict' in checkpoint:
                self.resnet_model.load_state_dict(checkpoint['state_dict'])
            else:
                self.resnet_model.load_state_dict(checkpoint)
            
            # Set to evaluation mode and move to device
            self.resnet_model.eval()
            self.resnet_model.to(self.device)
            
            logger.info("timm ResNet model loaded successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to load timm ResNet model: {e}")
            return False
    
    def classify_parking_situation(self, image: np.ndarray, 
                                 parking_event: Optional[ParkingEvent] = None,
                                 context_info: Optional[Dict[str, Any]] = None) -> ClassificationResult:
        """
        Main classification function using YOLO-seg + ResNet pipeline.
        
        Args:
            image: Input image showing the parking situation
            parking_event: Optional parking event data for context
            context_info: Optional additional context information
            
        Returns:
            ClassificationResult: Detailed classification result
        """
        start_time = time.time()
        
        if self.yolo_model is None or self.resnet_model is None:
            logger.error("Models not loaded")
            return self._create_error_result("Models not loaded")
        
        try:
            with self.lock:
                # Step 1: YOLO-seg segmentation
                seg_results = self.yolo_model(image, verbose=False)
                
                # Step 2: Process segmentation results
                height, width = image.shape[:2]
                seg_data = self.seg_processor.process_segmentation_results(seg_results, (height, width))
                
                # Step 3: Convert to 4-class mask
                four_class_mask = self.mask_converter.convert_seg_to_4class(seg_data, (height, width))
                
                # Step 4: Convert to VLO format
                vlo_input = self.mask_converter.mask_to_VLO(four_class_mask)
                
                # Step 5: ResNet classification
                violation_logits = self._run_resnet_classification(vlo_input)
                
                # Step 6: Process final results
                classification_result = self._process_pipeline_results(
                    violation_logits, seg_data, four_class_mask, 
                    parking_event, context_info
                )
                
                # Add processing time
                classification_result.processing_time = time.time() - start_time
                
                return classification_result
                
        except Exception as e:
            logger.error(f"Error during classification: {e}")
            return self._create_error_result(f"Classification error: {str(e)}")
    
    def _run_resnet_classification(self, vlo_input: np.ndarray) -> np.ndarray:
        """Run ResNet classification on VLO input."""
        try:
            # Convert to tensor and add batch dimension
            vlo_tensor = torch.from_numpy(vlo_input).float().unsqueeze(0).to(self.device)
            
            # Run inference
            with torch.no_grad():
                logits = self.resnet_model(vlo_tensor)
                logits = logits.cpu().numpy().squeeze(0)  # Remove batch dimension
            
            return logits
            
        except Exception as e:
            logger.error(f"Error in ResNet classification: {e}")
            return np.array([0.0, 1.0, 0.0])  # Default to 'normal'
    
    def _process_pipeline_results(self, logits: np.ndarray, 
                                seg_data: Dict[str, Any],
                                four_class_mask: np.ndarray,
                                parking_event: Optional[ParkingEvent],
                                context_info: Optional[Dict[str, Any]]) -> ClassificationResult:
        """Process final pipeline results and create ClassificationResult."""
        
        # Convert logits to probabilities
        exp_logits = np.exp(logits - np.max(logits))  # Numerical stability
        probabilities = exp_logits / np.sum(exp_logits)
        
        # Get class predictions
        class_names = ['danger', 'normal', 'violation']
        predicted_class_idx = np.argmax(probabilities)
        predicted_class = class_names[predicted_class_idx]
        confidence = probabilities[predicted_class_idx]
        
        # Determine if illegal (violation class)
        is_illegal = predicted_class == 'violation'
        violation_confidence = probabilities[2]  # violation is index 2
        
        # Create violation types
        detected_violations = []
        violation_confidences = {}
        
        if is_illegal:
            violation_type = IllegalParkingType.VIOLATION
            detected_violations.append(violation_type)
            violation_confidences[violation_type] = violation_confidence
        
        # Decision factors
        decision_factors = [
            f"ResNet prediction: {predicted_class} (confidence: {confidence:.3f})",
            f"Violation probability: {violation_confidence:.3f}"
        ]
        
        # Add segmentation info to decision factors
        vehicle_count = sum(1 for name in seg_data['class_names'].values() 
                          if name in self.mask_converter.vehicle_types)
        lane_count = sum(1 for name in seg_data['class_names'].values() 
                        if name in self.mask_converter.lane_types)
        
        decision_factors.extend([
            f"Detected vehicles: {vehicle_count}",
            f"Detected lanes: {lane_count}"
        ])
        
        # Extract vehicle mask bbox if available
        vehicle_mask_bbox = None
        if parking_event:
            original_bbox = (
                parking_event.bbox[0], parking_event.bbox[1],
                parking_event.bbox[2], parking_event.bbox[3]
            ) if hasattr(parking_event, 'bbox') else (0, 0, 100, 100)
            
            vehicle_mask_bbox = self.mask_converter.extract_vehicle_mask_bbox(
                four_class_mask, original_bbox
            )
        
        return ClassificationResult(
            is_illegal=is_illegal,
            overall_confidence=violation_confidence,
            detected_violations=detected_violations,
            violation_confidences=violation_confidences,
            raw_detections=[{
                'class_predictions': dict(zip(class_names, probabilities)),
                'logits': dict(zip(class_names, logits)),
                'predicted_class': predicted_class
            }],
            decision_factors=decision_factors,
            uncertainty_factors=[],
            segmentation_results=seg_data,
            vehicle_mask_bbox=vehicle_mask_bbox,
            model_version="yolo_seg_resnet_v1"
        )
    
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
    
    def get_model_info(self) -> Dict[str, Any]:
        """Get information about loaded models."""
        return {
            "yolo_status": "loaded" if self.yolo_model else "not_loaded",
            "resnet_status": "loaded" if self.resnet_model else "not_loaded",
            "yolo_path": self.yolo_path,
            "resnet_path": self.resnet_path,
            "resnet_model_name": self.resnet_model_name,
            "device": self.device
        }


class ViolationClassifier:
    """
    Maintains API compatibility with existing system.
    
    Wraps the new YOLOSegResNetClassifier to provide the same interface
    as the previous IllegalParkingClassifier.
    """
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.classifier: Optional[YOLOSegResNetClassifier] = None
        self.lock = threading.Lock()
        
        # Load classifier configuration
        self.classifier_config = config.get('illegal_parking', {})
        
        self._initialize_classifier()
        
        logger.info("ViolationClassifier initialized")
    
    def _initialize_classifier(self) -> bool:
        """Initialize the YOLO-seg + ResNet classifier."""
        try:
            self.classifier = YOLOSegResNetClassifier(self.classifier_config)
            return self.classifier.yolo_model is not None and self.classifier.resnet_model is not None
            
        except Exception as e:
            logger.error(f"Failed to initialize classifier: {e}")
            return False
    
    def classify_violation(self, image: np.ndarray, 
                          parking_event: ParkingEvent,
                          context_info: Optional[Dict[str, Any]] = None) -> ClassificationResult:
        """
        Classify a parking violation event.
        
        Maintains API compatibility with existing system.
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
        return (self.classifier is not None and 
                self.classifier.yolo_model is not None and 
                self.classifier.resnet_model is not None)
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get classifier statistics and status."""
        return {
            "ready": self.is_ready(),
            "model_info": self.classifier.get_model_info() if self.classifier else {},
            "config": self.classifier_config
        }


# Global instance - maintains compatibility with existing code
violation_classifier: Optional[ViolationClassifier] = None


def initialize_violation_classifier(config: Dict[str, Any]) -> bool:
    """
    Initialize the global violation classifier instance.
    
    Maintains API compatibility with existing system.
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
    
    Maintains API compatibility with existing system.
    """
    return violation_classifier