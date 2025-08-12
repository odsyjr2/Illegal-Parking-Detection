# AI Server - Standalone Processor for Illegal Parking Detection

## Purpose
This directory contains the standalone AI processor with two-phase architecture for illegal parking detection. It operates independently without web dependencies and communicates with the Spring Boot backend via REST API.

## Core Components

### Two-Phase Processing System
- `main.py` - Standalone processor orchestrator (replaces FastAPI)
- `core/monitoring.py` - Phase 1: Continuous multi-stream monitoring (lightweight)
- `core/analysis.py` - Phase 2: Event-driven detailed analysis (heavy AI)
- `workers/analysis_worker.py` - Worker thread pool for task processing

### AI Analysis Modules
- `analysis_pipeline.py` - Orchestrates the complete AI workflow
- `multi_vehicle_tracker.py` - YOLO-based vehicle detection and tracking
- `parking_monitor.py` - Monitors vehicle stationary duration
- `illegal_classifier.py` - YOLO model for illegal parking classification
- `license_plate_detector.py` - YOLO model for license plate detection
- `ocr_reader.py` - EasyOCR for Korean license plate text recognition

### System Infrastructure
- `cctv_manager.py` - Manages multiple CCTV streams (local files or live APIs)
- `event_reporter.py` - Backend communication via REST API
- `models.py` - Data structures and task definitions
- `utils/config_loader.py` - Multi-YAML configuration management
- `utils/logger.py` - Centralized logging system

### Testing Framework
- `test/multi_stream_visualizer.py` - Visual testing with 6 OpenCV windows
- `test/performance_tester.py` - Performance and load testing
- `test/integration_tester.py` - End-to-end pipeline testing
- `test/test_config.py` - Configuration system validation

## Architecture Benefits
- **Decoupled Design:** AI processor operates independently from web interface
- **Scalable Processing:** Two-phase system with task queue communication
- **Resource Efficient:** Lightweight monitoring + heavy analysis on-demand
- **Production Ready:** No web dependencies, robust error handling, comprehensive testing