"""
Analysis Service Module - Phase 2: Event-driven Heavy AI Processing

This module implements the heavy AI processing service that performs detailed
violation analysis on parking event candidates from the monitoring service.
It executes the complete AI pipeline including illegal parking classification,
license plate detection, and OCR recognition.

Key Features:
- Heavy AI processing for detailed violation analysis
- Complete AI pipeline: classification → plate detection → OCR
- Integration with existing AI modules (illegal_classifier, license_plate_detector, ocr_reader)
- Performance tracking and comprehensive violation reporting
- Resource management and model loading optimization

Architecture:
- AnalysisService: Main analysis coordinator for heavy processing
- ModelManager: AI model loading and management
- AnalysisResult generation with comprehensive reporting
- Integration with existing AI component ecosystem
"""

import logging
import time
import threading
import base64
from datetime import datetime
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
import cv2
import numpy as np
import psutil
import gc

# Import existing AI components
from illegal_classifier import get_violation_classifier, ViolationClassifier
from license_plate_detector import get_license_plate_detector, LicensePlateDetectionManager
from ocr_reader import get_ocr_reader, OCRManager
from models import (
    AnalysisTask, ParkingEvent, ViolationReport, AnalysisResult, 
    OCRResult, ModelConfig, PerformanceMetrics
)
from utils.logger import get_logger

# Configure logging
logger = get_logger(__name__)


@dataclass
class ModelLoadingStatus:
    """Status of AI model loading"""
    model_name: str
    is_loaded: bool
    load_time: float = 0.0
    memory_usage_mb: Optional[float] = None
    error_message: Optional[str] = None


class ModelManager:
    """Manages loading and lifecycle of heavy AI models"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.models_config = config.get('models', {})
        
        # Model instances
        self.illegal_classifier: Optional[ViolationClassifier] = None
        self.plate_detector: Optional[LicensePlateDetectionManager] = None
        self.ocr_reader: Optional[OCRManager] = None
        
        # Model loading status
        self.loading_status: Dict[str, ModelLoadingStatus] = {}
        self.models_loaded = False
        self.total_memory_usage = 0.0
        
        # Performance tracking
        self.model_performance: Dict[str, List[float]] = {
            'classification': [],
            'plate_detection': [],
            'ocr': []
        }
        
        logger.info("ModelManager initialized")
    
    def load_all_models(self) -> bool:
        """Load all heavy AI models for analysis"""
        logger.info("Loading heavy AI models for analysis...")
        start_time = time.time()
        
        try:
            # Track initial memory usage
            initial_memory = psutil.Process().memory_info().rss / 1024 / 1024
            
            # Load models sequentially to avoid memory issues
            success = True
            
            # 1. Load Illegal Parking Classifier
            success &= self._load_illegal_classifier()
            
            # 2. Load License Plate Detector
            success &= self._load_plate_detector()
            
            # 3. Load OCR Reader
            success &= self._load_ocr_reader()
            
            # Calculate total memory usage
            final_memory = psutil.Process().memory_info().rss / 1024 / 1024
            self.total_memory_usage = final_memory - initial_memory
            
            self.models_loaded = success
            load_time = time.time() - start_time
            
            if success:
                logger.info(f"All AI models loaded successfully in {load_time:.2f}s, "
                          f"memory usage: {self.total_memory_usage:.1f}MB")
            else:
                logger.error("Failed to load some AI models")
            
            return success
            
        except Exception as e:
            logger.error(f"Error loading AI models: {e}")
            return False
    
    def _load_illegal_classifier(self) -> bool:
        """Load YOLO-seg + ResNet illegal parking classification pipeline"""
        model_name = "illegal_classifier"
        start_time = time.time()
        
        try:
            # Import and initialize the new violation classifier
            from illegal_classifier import initialize_violation_classifier
            
            # Initialize with full config
            classifier_config = {
                'illegal_parking': self.models_config.get('illegal_parking', {})
            }
            
            success = initialize_violation_classifier(classifier_config)
            
            if success:
                from illegal_classifier import get_violation_classifier
                self.illegal_classifier = get_violation_classifier()
                
                load_time = time.time() - start_time
                memory_usage = self._estimate_model_memory(model_name)
                
                self.loading_status[model_name] = ModelLoadingStatus(
                    model_name=model_name,
                    is_loaded=True,
                    load_time=load_time,
                    memory_usage_mb=memory_usage
                )
                
                logger.info(f"YOLO-seg + ResNet classifier loaded in {load_time:.2f}s")
                return True
            else:
                self.loading_status[model_name] = ModelLoadingStatus(
                    model_name=model_name,
                    is_loaded=False,
                    error_message="Failed to initialize YOLO-seg + ResNet pipeline"
                )
                return False
                
        except Exception as e:
            self.loading_status[model_name] = ModelLoadingStatus(
                model_name=model_name,
                is_loaded=False,
                error_message=str(e)
            )
            logger.error(f"Error loading YOLO-seg + ResNet classifier: {e}")
            return False
    
    def _load_plate_detector(self) -> bool:
        """Load license plate detection model"""
        model_name = "plate_detector"
        start_time = time.time()
        
        try:
            self.plate_detector = get_license_plate_detector()
            
            if self.plate_detector:
                # Initialize with configuration
                detector_config = self.models_config.get('license_plate', {})
                success = self.plate_detector.load_model(detector_config)
                
                if success:
                    load_time = time.time() - start_time
                    memory_usage = self._estimate_model_memory(model_name)
                    
                    self.loading_status[model_name] = ModelLoadingStatus(
                        model_name=model_name,
                        is_loaded=True,
                        load_time=load_time,
                        memory_usage_mb=memory_usage
                    )
                    
                    logger.info(f"License plate detector loaded in {load_time:.2f}s")
                    return True
                else:
                    self.loading_status[model_name] = ModelLoadingStatus(
                        model_name=model_name,
                        is_loaded=False,
                        error_message="Failed to load model configuration"
                    )
                    return False
            else:
                self.loading_status[model_name] = ModelLoadingStatus(
                    model_name=model_name,
                    is_loaded=False,
                    error_message="Failed to get detector instance"
                )
                return False
                
        except Exception as e:
            self.loading_status[model_name] = ModelLoadingStatus(
                model_name=model_name,
                is_loaded=False,
                error_message=str(e)
            )
            logger.error(f"Error loading plate detector: {e}")
            return False
    
    def _load_ocr_reader(self) -> bool:
        """Load OCR recognition model"""
        model_name = "ocr_reader"
        start_time = time.time()
        
        try:
            self.ocr_reader = get_ocr_reader()
            
            if self.ocr_reader:
                # Initialize with configuration
                ocr_config = self.models_config.get('license_plate', {})
                success = self.ocr_reader.load_model(ocr_config)
                
                if success:
                    load_time = time.time() - start_time
                    memory_usage = self._estimate_model_memory(model_name)
                    
                    self.loading_status[model_name] = ModelLoadingStatus(
                        model_name=model_name,
                        is_loaded=True,
                        load_time=load_time,
                        memory_usage_mb=memory_usage
                    )
                    
                    logger.info(f"OCR reader loaded in {load_time:.2f}s")
                    return True
                else:
                    self.loading_status[model_name] = ModelLoadingStatus(
                        model_name=model_name,
                        is_loaded=False,
                        error_message="Failed to load model configuration"
                    )
                    return False
            else:
                self.loading_status[model_name] = ModelLoadingStatus(
                    model_name=model_name,
                    is_loaded=False,
                    error_message="Failed to get OCR instance"
                )
                return False
                
        except Exception as e:
            self.loading_status[model_name] = ModelLoadingStatus(
                model_name=model_name,
                is_loaded=False,
                error_message=str(e)
            )
            logger.error(f"Error loading OCR reader: {e}")
            return False
    
    def _estimate_model_memory(self, model_name: str) -> float:
        """Estimate memory usage for a specific model"""
        try:
            # Simple estimation based on current process memory
            current_memory = psutil.Process().memory_info().rss / 1024 / 1024
            return current_memory * 0.1  # Rough estimation
        except:
            return 0.0
    
    def get_loading_summary(self) -> Dict[str, Any]:
        """Get summary of model loading status"""
        return {
            "models_loaded": self.models_loaded,
            "total_memory_usage_mb": self.total_memory_usage,
            "model_status": {
                name: {
                    "loaded": status.is_loaded,
                    "load_time": status.load_time,
                    "memory_mb": status.memory_usage_mb,
                    "error": status.error_message
                }
                for name, status in self.loading_status.items()
            }
        }
    
    def unload_models(self):
        """Unload all models to free memory"""
        logger.info("Unloading AI models...")
        
        try:
            self.illegal_classifier = None
            self.plate_detector = None
            self.ocr_reader = None
            
            # Force garbage collection
            gc.collect()
            
            self.models_loaded = False
            logger.info("AI models unloaded successfully")
            
        except Exception as e:
            logger.error(f"Error unloading models: {e}")


class AnalysisService:
    """Phase 2: Heavy AI processing for detailed violation analysis"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.analysis_config = config.get('analysis', {})
        
        # Model management
        self.model_manager = ModelManager(config)
        
        # Performance tracking
        self.analysis_stats = {
            'total_processed': 0,
            'violations_confirmed': 0,
            'ocr_success_count': 0,
            'avg_processing_time': 0.0,
            'processing_times': []
        }
        
        # Threading
        self.lock = threading.Lock()
        
        # Error tracking
        self.error_count = 0
        self.last_error: Optional[str] = None
        
        logger.info("AnalysisService initialized")
    
    def initialize_models(self) -> bool:
        """Initialize heavy AI models for analysis"""
        logger.info("Initializing AnalysisService models...")
        
        try:
            success = self.model_manager.load_all_models()
            
            if success:
                logger.info("AnalysisService models initialized successfully")
            else:
                logger.error("Failed to initialize AnalysisService models")
            
            return success
            
        except Exception as e:
            logger.error(f"Error initializing AnalysisService: {e}")
            return False
    
    def analyze_violation(self, task: AnalysisTask) -> AnalysisResult:
        """Process violation through complete AI pipeline"""
        start_time = time.time()
        parking_event = task.parking_event
        
        logger.info(f"Starting analysis for task {task.task_id}")
        
        try:
            # Validate models are loaded
            if not self.model_manager.models_loaded:
                raise RuntimeError("AI models not loaded")
            
            # Step 1: Illegal Parking Classification
            classification_start = time.time()
            is_illegal, classification_confidence = self._classify_parking_violation(
                parking_event.violation_frame, parking_event
            )
            classification_time = time.time() - classification_start
            
            logger.info(f"Classification result for task {task.task_id}: "
                       f"illegal={is_illegal}, confidence={classification_confidence:.3f}")
            
            # Step 2: License Plate Detection (if classification suggests violation)
            plate_detection_time = 0.0
            plate_results = []
            
            if is_illegal and classification_confidence > 0.5:  # Only if likely violation
                plate_start = time.time()
                plate_results = self._detect_license_plates(
                    parking_event.violation_frame, parking_event.vehicle_track
                )
                plate_detection_time = time.time() - plate_start
                
                logger.info(f"Plate detection for task {task.task_id}: "
                          f"{len(plate_results)} plates detected")
            
            # Step 3: OCR Processing (if plates detected)
            ocr_start = time.time()
            ocr_result = self._perform_ocr_recognition(plate_results)
            ocr_time = time.time() - ocr_start
            
            if ocr_result.is_successful:
                logger.info(f"OCR success for task {task.task_id}: "
                          f"plate={ocr_result.plate_number}")
            else:
                logger.info(f"OCR failed for task {task.task_id}")
            
            # Step 4: Generate comprehensive analysis result
            total_processing_time = time.time() - start_time
            
            analysis_result = AnalysisResult(
                task_id=task.task_id,
                parking_event=parking_event,
                is_illegal_by_model=is_illegal,
                model_confidence=classification_confidence,
                vehicle_type=parking_event.vehicle_track.vehicle_type,
                ocr_result=ocr_result,
                processing_time=total_processing_time
            )
            
            # Update statistics
            self._update_analysis_stats(analysis_result, {
                'classification_time': classification_time,
                'plate_detection_time': plate_detection_time,
                'ocr_time': ocr_time
            })
            
            logger.info(f"Analysis completed for task {task.task_id} in {total_processing_time:.3f}s")
            return analysis_result
            
        except Exception as e:
            error_msg = f"Analysis failed for task {task.task_id}: {e}"
            logger.error(error_msg)
            
            with self.lock:
                self.error_count += 1
                self.last_error = str(e)
            
            # Return failed analysis result
            return AnalysisResult(
                task_id=task.task_id,
                parking_event=parking_event,
                is_illegal_by_model=False,
                model_confidence=0.0,
                vehicle_type="unknown",
                ocr_result=OCRResult(is_successful=False, error_message=str(e)),
                processing_time=time.time() - start_time
            )
    
    def _classify_parking_violation(self, frame: np.ndarray, 
                                  parking_event: ParkingEvent) -> Tuple[bool, float]:
        """Classify parking situation using YOLO-seg + ResNet pipeline"""
        try:
            if not self.model_manager.illegal_classifier:
                logger.warning("YOLO-seg + ResNet classifier not available")
                return False, 0.0
            
            # Use full frame (not crop) for new pipeline
            classification_result = self.model_manager.illegal_classifier.classify_violation(
                frame, parking_event
            )
            
            is_illegal = classification_result.is_illegal
            confidence = classification_result.overall_confidence
            
            # Track performance
            self.model_manager.model_performance['classification'].append(
                classification_result.processing_time
            )
            
            # Log additional info for debugging
            logger.debug(f"YOLO-seg + ResNet result: {is_illegal}, confidence: {confidence:.3f}")
            if classification_result.decision_factors:
                logger.debug(f"Decision factors: {classification_result.decision_factors}")
            
            return is_illegal, confidence
            
        except Exception as e:
            logger.error(f"Error in YOLO-seg + ResNet classification: {e}")
            return False, 0.0
    
    def _detect_license_plates(self, frame: np.ndarray, 
                             vehicle_track) -> List[Dict[str, Any]]:
        """Detect license plates in vehicle region"""
        try:
            if not self.model_manager.plate_detector:
                logger.warning("Plate detector not available")
                return []
            
            # Get vehicle bounding box
            bbox = vehicle_track.bbox
            
            # Detect plates within vehicle region
            plate_results = self.model_manager.plate_detector.detect_vehicle_plates(
                frame, bbox
            )
            
            # Track performance
            if hasattr(self.model_manager.plate_detector, 'last_processing_time'):
                self.model_manager.model_performance['plate_detection'].append(
                    self.model_manager.plate_detector.last_processing_time
                )
            
            return plate_results
            
        except Exception as e:
            logger.error(f"Error in license plate detection: {e}")
            return []
    
    def _perform_ocr_recognition(self, plate_results: List[Dict[str, Any]]) -> OCRResult:
        """Perform OCR recognition on detected plates"""
        try:
            if not plate_results:
                return OCRResult(
                    is_successful=False,
                    error_message="No plates detected"
                )
            
            if not self.model_manager.ocr_reader:
                return OCRResult(
                    is_successful=False,
                    error_message="OCR reader not available"
                )
            
            # Process plates through OCR
            ocr_results = self.model_manager.ocr_reader.batch_process_plates(plate_results)
            
            # Find best OCR result
            best_result = None
            best_confidence = 0.0
            
            for result in ocr_results:
                if result.is_successful and result.confidence > best_confidence:
                    best_result = result
                    best_confidence = result.confidence
            
            if best_result:
                # Track performance
                self.model_manager.model_performance['ocr'].append(
                    best_result.processing_time
                )
                
                return OCRResult(
                    is_successful=True,
                    plate_number=best_result.plate_number,
                    confidence=best_result.confidence,
                    processing_time=best_result.processing_time
                )
            else:
                return OCRResult(
                    is_successful=False,
                    error_message="OCR recognition failed for all detected plates"
                )
                
        except Exception as e:
            logger.error(f"Error in OCR recognition: {e}")
            return OCRResult(
                is_successful=False,
                error_message=str(e)
            )
    
    def _update_analysis_stats(self, result: AnalysisResult, timings: Dict[str, float]):
        """Update analysis performance statistics"""
        with self.lock:
            self.analysis_stats['total_processed'] += 1
            
            if result.is_illegal_by_model:
                self.analysis_stats['violations_confirmed'] += 1
            
            if result.ocr_result.is_successful:
                self.analysis_stats['ocr_success_count'] += 1
            
            # Update processing times
            self.analysis_stats['processing_times'].append(result.processing_time)
            
            # Keep only recent processing times (last 100)
            if len(self.analysis_stats['processing_times']) > 100:
                self.analysis_stats['processing_times'] = self.analysis_stats['processing_times'][-100:]
            
            # Update average processing time
            if self.analysis_stats['processing_times']:
                self.analysis_stats['avg_processing_time'] = (
                    sum(self.analysis_stats['processing_times']) / 
                    len(self.analysis_stats['processing_times'])
                )
    
    def create_violation_report(self, analysis_result: AnalysisResult, 
                              cctv_id: int) -> ViolationReport:
        """Create violation report for backend communication"""
        try:
            # Encode violation frame as base64
            frame = analysis_result.parking_event.violation_frame
            _, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 85])
            image_base64 = base64.b64encode(buffer).decode('utf-8')
            
            # Create violation report
            violation_report = analysis_result.to_violation_report(cctv_id)
            violation_report.vehicle_image = image_base64
            
            return violation_report
            
        except Exception as e:
            logger.error(f"Error creating violation report: {e}")
            raise
    
    def get_analysis_stats(self) -> Dict[str, Any]:
        """Get analysis service performance statistics"""
        with self.lock:
            stats = self.analysis_stats.copy()
            
            # Add success rates
            if stats['total_processed'] > 0:
                stats['violation_rate'] = stats['violations_confirmed'] / stats['total_processed']
                stats['ocr_success_rate'] = stats['ocr_success_count'] / stats['total_processed']
            else:
                stats['violation_rate'] = 0.0
                stats['ocr_success_rate'] = 0.0
            
            # Add model performance
            stats['model_performance'] = {}
            for model_name, times in self.model_manager.model_performance.items():
                if times:
                    stats['model_performance'][model_name] = {
                        'avg_time': sum(times) / len(times),
                        'min_time': min(times),
                        'max_time': max(times),
                        'samples': len(times)
                    }
            
            # Add model loading status
            stats['model_status'] = self.model_manager.get_loading_summary()
            
            # Add error information
            stats['error_count'] = self.error_count
            stats['last_error'] = self.last_error
            
            return stats
    
    def is_ready(self) -> bool:
        """Check if analysis service is ready for processing"""
        return self.model_manager.models_loaded
    
    def cleanup(self):
        """Cleanup analysis service and unload models"""
        logger.info("Cleaning up AnalysisService...")
        self.model_manager.unload_models()