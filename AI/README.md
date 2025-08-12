# AI Processor for Illegal Parking Detection System

## Overview

This AI processor implements a two-phase architecture for illegal parking detection across multiple CCTV streams. It performs real-time vehicle tracking, parking duration monitoring, violation classification, license plate detection, and OCR processing.

## Architecture

### Two-Phase Processing System

1. **Phase 1: Continuous Monitoring** (Lightweight)
   - Real-time vehicle detection and tracking
   - Parking duration monitoring
   - Violation candidate identification

2. **Phase 2: Detailed Analysis** (Heavy AI Processing)
   - Illegal parking classification
   - License plate detection and OCR
   - Comprehensive violation analysis

### Core Components

```
AI/ai_server/
├── main.py                    # Standalone processor orchestrator
├── core/
│   ├── monitoring.py          # Phase 1: Continuous multi-stream monitoring
│   └── analysis.py           # Phase 2: Event-driven detailed analysis
├── workers/
│   └── analysis_worker.py    # Worker thread pool for task processing
├── models.py                 # Data structures & task definitions
├── utils/
│   ├── config_loader.py      # Multi-YAML configuration management
│   └── logger.py             # Centralized logging system
└── test/                     # Comprehensive testing framework
```

## Testing Methods

### 1. Visual Multi-Stream Detection Test

Test continuous detection visualization for multiple CCTV streams with real-time AI overlays.

#### Method A: Interactive Visual Demonstration
```bash
# Navigate to AI directory
cd AI/ai_server

# Run visual test with 6 OpenCV windows
python test/multi_stream_visualizer.py
```

**Features:**
- 6 simultaneous CCTV stream windows (2x3 grid layout)
- Real-time vehicle tracking with bounding boxes and IDs
- Parking violation detection with visual alerts
- Interactive controls: pause/resume, screenshots, statistics
- Performance metrics display (FPS, processing times, violations)

**Controls:**
- `SPACE`: Pause/Resume all streams
- `S`: Save screenshots of all windows
- `Q`: Quit application
- `R`: Reset statistics
- `1-6`: Focus on individual stream

#### Method B: Performance Testing
```bash
# Run progressive load testing (1-6 streams)
python test/performance_tester.py
```

**Features:**
- Progressive load testing with 1-6 concurrent streams
- Resource monitoring (CPU, memory, GPU usage)
- Performance bottleneck identification
- Comprehensive reporting with charts and statistics

### 2. API Communication Test

Test sending violation data to Spring Boot backend via REST API.

#### Method A: Integration Testing with Mock Backend
```bash
# Run end-to-end pipeline testing
python test/integration_tester.py
```

**Features:**
- Complete pipeline validation (monitoring → analysis → reporting)
- Mock Spring Boot server for API testing
- Violation data transmission validation
- Error handling and recovery testing

#### Method B: Real Backend Testing
```bash
# Configure backend endpoint in config/config.yaml
backend:
  url: "http://localhost:8080"
  enabled: true

# Run with real backend
python main.py
```

### 3. Configuration Testing
```bash
# Basic configuration validation
python test/simple_test_config.py

# Comprehensive configuration testing
python test/test_config.py
```

### 4. Complete Test Suite
```bash
# Run all automated tests
python -c "import test; test.run_all_tests()"
```

## API Specification

### 1. Violation Report API

#### Endpoint: POST /api/ai/v1/report-detection

**Purpose:** Send violation detection results to Spring Boot backend

**Request Format:**
```json
{
  "cctvId": 1,
  "timestamp": "2025-01-15T10:30:00Z",
  "location": {
    "latitude": 37.5665,
    "longitude": 126.9780
  },
  "vehicleImage": "base64_encoded_image_data",
  "aiAnalysis": {
    "is_illegal_by_model": true,
    "violation_confidence": 0.85,
    "violation_types": ["crosswalk_violation"],
    "license_plate": {
      "detected": true,
      "text": "12가3456",
      "confidence": 0.92,
      "is_valid_format": true
    },
    "vehicle_tracking": {
      "track_id": 42,
      "parking_duration": 320.5,
      "vehicle_type": "car"
    },
    "detection_metadata": {
      "model_version": "yolo_illegal_v1",
      "processing_time": 1.24,
      "image_quality": 0.78
    }
  }
}
```

**Response Format:**
```json
{
  "status": "success",
  "message": "Violation report processed",
  "reportId": "RPT-2025-001234",
  "processed_at": "2025-01-15T10:30:05Z"
}
```

### 2. System Status API

#### Endpoint: GET /api/ai/v1/status

**Purpose:** Check AI processor system status

**Response Format:**
```json
{
  "status": "healthy",
  "components": {
    "monitoring_service": {
      "status": "running",
      "active_streams": 6,
      "total_violations_detected": 42
    },
    "analysis_service": {
      "status": "ready",
      "worker_count": 3,
      "queue_size": 2
    },
    "models": {
      "vehicle_detector": {"loaded": true, "version": "yolo_v11"},
      "illegal_classifier": {"loaded": true, "version": "yolo_illegal_v1"},
      "license_plate_detector": {"loaded": true, "version": "yolo_plate_v1"},
      "ocr_reader": {"loaded": true, "version": "easyocr_korean_v1"}
    }
  }
}
```

### 3. Configuration API

#### Endpoint: GET /api/ai/v1/config

**Purpose:** Retrieve current AI processor configuration

**Response Format:**
```json
{
  "monitoring": {
    "parking_duration_threshold": 300,
    "frame_skip_rate": 5,
    "update_interval": 0.1
  },
  "analysis": {
    "worker_pool_size": 3,
    "queue_max_size": 100,
    "confidence_thresholds": {
      "vehicle_detection": 0.5,
      "illegal_classification": 0.7,
      "license_plate": 0.7,
      "ocr": 0.5
    }
  },
  "streams": {
    "active_count": 6,
    "sources": ["file", "rtsp"]
  }
}
```

## Configuration Files

### Multi-YAML Configuration System

```
AI/config/
├── config.yaml              # Main application configuration
├── models.yaml              # AI model-specific configurations  
├── streams.yaml             # CCTV stream configurations
└── processing.yaml          # Processing parameters
```

### config.yaml
```yaml
application:
  name: "Illegal Parking Detection AI"
  version: "1.0.0"
  mode: "production"

backend:
  url: "http://localhost:8080"
  enabled: true
  timeout: 30
  retry_attempts: 3
  retry_delay: 5

logging:
  level: "INFO"
  console_output:
    enabled: true
    colored: true
  file_logging:
    enabled: true
    path: "../data/outputs/ai_processor.log"
    max_size_mb: 100
    backup_count: 5
  component_levels:
    monitoring: "INFO"
    analysis: "INFO"
    workers: "DEBUG"
```

### models.yaml
```yaml
vehicle_detection:
  path: "models/vehicle_detection/yolo_vehicle_v1.pt"
  confidence_threshold: 0.5
  iou_threshold: 0.45
  device: "auto"

illegal_parking:
  path: "models/illegal_parking/yolo_illegal_v1.pt"
  confidence_threshold: 0.7
  iou_threshold: 0.45
  device: "auto"

license_plate:
  detector_path: "models/license_plate/yolo_plate_detector_v1.pt"
  detector_confidence: 0.7
  detector_iou: 0.4
  ocr_path: "models/license_plate/easyocr_korean_plate_v1.pth"
  ocr_languages: ["ko", "en"]
  ocr_gpu: true
  ocr_confidence: 0.5
```

### streams.yaml
```yaml
cctv_streams:
  fetch_from_backend: true
  backend_endpoint: "/api/cctvs"
  test_mode: true
  test_data_path: "../data/test_videos"
  
  local_streams:
    - id: "stream_001"
      name: "Main Intersection"
      source: "../data/test_videos/test_video_1.mp4"
      location:
        latitude: 37.5665
        longitude: 126.9780
    - id: "stream_002"  
      name: "Parking Zone A"
      source: "../data/test_videos/test_video_2.mp4"
      location:
        latitude: 37.5675
        longitude: 126.9790
```

### processing.yaml
```yaml
monitoring:
  parking_duration_threshold: 300  # seconds
  frame_skip_rate: 5
  max_tracking_distance: 100
  update_interval: 0.1

analysis:
  worker_pool_size: 3
  queue_max_size: 100
  batch_processing: false
  retry_attempts: 3
  retry_delay: 5

visualization:
  enabled: true
  window_size: [640, 480]
  fps_display: true
  save_screenshots: true
```

## Running the Tests

### Prerequisites

1. **Install Dependencies:**
```bash
pip install -r requirements.txt
```

2. **Prepare Test Data:**
```bash
# Create test video directory
mkdir -p ../data/test_videos

# Add sample video files (MP4 format recommended)
# Files should be named: test_video_1.mp4, test_video_2.mp4, etc.
```

3. **Configure Models:**
```bash
# Ensure AI models are available in models/ directory
mkdir -p models/{vehicle_detection,illegal_parking,license_plate}
```

### Test Execution Sequence

#### 1. Configuration Validation
```bash
cd AI/ai_server
python test/simple_test_config.py
python test/test_config.py
```

#### 2. Visual Multi-Stream Test
```bash
# Interactive visual demonstration (6 OpenCV windows)
python test/multi_stream_visualizer.py

# Expected output:
# - 6 OpenCV windows showing CCTV streams
# - Real-time vehicle tracking overlays
# - Parking violation detection alerts
# - Performance metrics display
```

#### 3. API Communication Test
```bash
# Mock backend integration test
python test/integration_tester.py

# Expected output:
# - Mock backend server starts on localhost:8080
# - Violation detection data sent via POST /api/ai/v1/report-detection
# - API response validation
# - End-to-end pipeline verification
```

#### 4. Performance Test
```bash
# Progressive load testing
python test/performance_tester.py

# Expected output:
# - Resource usage monitoring
# - FPS performance across 1-6 streams
# - Memory and CPU utilization charts
# - Performance bottleneck identification
```

#### 5. Complete Integration Test
```bash
# Run all tests
python -c "import test; test.run_all_tests()"
```

### Expected Test Results

#### Visual Test Success Criteria:
- ✅ 6 OpenCV windows display simultaneously
- ✅ Vehicle tracking with bounding boxes and IDs
- ✅ Parking duration counters visible
- ✅ Violation alerts appear for stationary vehicles
- ✅ Performance metrics show stable FPS (>10 FPS per stream)

#### API Test Success Criteria:
- ✅ Mock backend receives violation data
- ✅ JSON payload format matches API specification
- ✅ Backend responds with success status
- ✅ License plate OCR data included when detected
- ✅ Error handling and retry mechanisms work

## File Cleanup Guide

After successful testing, the following files can be removed:

### Files to DELETE (FastAPI/WebSocket Legacy):
```bash
# Remove FastAPI web server components
rm AI/ai_server/response_models.py
rm AI/ai_server/visualization_manager.py  
rm AI/ai_server/frame_processor.py

# Remove old main.py (FastAPI version)
# Note: Keep the new standalone main.py
```

### Files to KEEP (Core System):
```bash
# Keep all files in these directories:
AI/ai_server/core/                    # Phase 1 & 2 processors
AI/ai_server/workers/                 # Worker thread pool
AI/ai_server/utils/                   # Configuration & logging
AI/ai_server/test/                    # Testing framework
AI/ai_server/models.py                # Data structures
AI/ai_server/main.py                  # Standalone processor
AI/ai_server/event_reporter.py        # Backend communication

# Keep all AI modules:
AI/ai_server/multi_vehicle_tracker.py
AI/ai_server/parking_monitor.py
AI/ai_server/illegal_classifier.py
AI/ai_server/license_plate_detector.py
AI/ai_server/ocr_reader.py
AI/ai_server/cctv_manager.py
AI/ai_server/analysis_pipeline.py
```

### Cleanup Commands:
```bash
cd AI/ai_server

# Remove FastAPI legacy files
rm -f response_models.py
rm -f visualization_manager.py
rm -f frame_processor.py

# Clean up any temporary test files
rm -rf __pycache__/
rm -rf test/__pycache__/
rm -rf .pytest_cache/

echo "Cleanup completed - FastAPI components removed"
```

## Production Deployment

### System Requirements:
- Python 3.8+
- CUDA-capable GPU (recommended)
- 8GB+ RAM
- OpenCV with GPU support
- Spring Boot backend running

### Deployment Steps:
1. Configure backend URL in `config/config.yaml`
2. Place AI models in `models/` directory
3. Set up CCTV stream configurations in `config/streams.yaml`
4. Run: `python main.py`

### Monitoring:
- Logs: `../data/outputs/ai_processor.log`
- Performance: `../data/outputs/performance.log`
- Status API: `GET /api/ai/v1/status`

## Support

For issues or questions:
1. Check logs in `../data/outputs/`
2. Run configuration tests: `python test/test_config.py`
3. Verify model files in `models/` directory
4. Test backend connectivity: `python test/integration_tester.py`
