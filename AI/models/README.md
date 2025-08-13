# Models Directory - AI Model Weights

## Purpose
This directory stores all trained machine learning model weights used by the illegal parking detection system. All models are centrally managed and referenced through the configuration system.

## Model Types

### YOLO Models (Ultralytics)
- **Vehicle Detection & Tracking** - General vehicle detection model for multi-object tracking
- **Illegal Parking Classifier** - Fine-tuned model to classify parking situations as legal/illegal
- **License Plate Detector** - Specialized model for detecting license plate regions in vehicle images

### OCR Models (EasyOCR)
- **License Plate OCR** - Custom fine-tuned EasyOCR model for reading Korean license plate text
- Optimized for various angles, lighting conditions, and plate formats

## File Organization
Models are organized by type and version:
```
models/
├── vehicle_detection/
│   └── yolo_vehicle_v1.pt
├── illegal_parking/
│   └── yolo_illegal_v1.pt
├── license_plate/
│   ├── yolo_plate_detector_v1.pt
│   └── easyocr_korean_plate_v1.pth
└── backup/
    └── [previous model versions]
```

## Configuration
All model paths are managed in `config/config.yaml`. Models should never be hardcoded in the application code.

## Usage Notes
- Models are loaded once at server startup for performance
- GPU acceleration is used when available
- Model versions can be easily swapped via configuration changes