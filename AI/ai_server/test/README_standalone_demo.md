# Standalone AI Demo Usage Guide

## Overview
The standalone demo script provides comprehensive testing of the AI pipeline with customizable device and stream configurations.

## Basic Usage
```bash
# Run with default settings (auto device, 3 streams)
python standalone_demo.py

# Show help
python standalone_demo.py --help

# List available video streams
python standalone_demo.py --list-streams
```

## Device Configuration

### Available Device Options
- `auto` - Automatically detect best available device (default)
- `cpu` - Force CPU usage for all models
- `cuda` - Use default CUDA GPU
- `cuda:0` - Use specific GPU (0, 1, 2, etc.)

### Examples
```bash
# Use CPU for all models
python standalone_demo.py --device cpu

# Use specific GPU
python standalone_demo.py --device cuda:0

# Auto-detect (default)
python standalone_demo.py --device auto
```

## Stream Configuration

### Number of Streams
- Range: 1-6 streams
- Automatically discovers available test video directories
- Windows positioned in optimal grid layout

### Examples
```bash
# Test with single stream
python standalone_demo.py --streams 1

# Test with all 6 streams
python standalone_demo.py --streams 6

# Default 3 streams
python standalone_demo.py --streams 3
```

## Window Configuration

### Window Size
- Format: `WIDTHxHEIGHT`
- Default: `640x480`

```bash
# Larger windows
python standalone_demo.py --window-size 800x600

# Smaller windows for many streams
python standalone_demo.py --streams 6 --window-size 480x320
```

## Performance Tuning

### Frame Delay
- Milliseconds between frame updates
- Lower = faster processing, higher CPU usage
- Higher = slower processing, lower CPU usage

```bash
# Faster processing (50ms delay)
python standalone_demo.py --frame-delay 50

# Slower processing (200ms delay)  
python standalone_demo.py --frame-delay 200
```

## Complete Examples

### CPU Testing with All Streams
```bash
python standalone_demo.py --device cpu --streams 6 --frame-delay 150
```

### GPU Performance Testing
```bash
python standalone_demo.py --device cuda:0 --streams 6 --frame-delay 50
```

### Single Stream Debug Mode
```bash
python standalone_demo.py --streams 1 --window-size 1024x768 --frame-delay 500
```

## Controls During Demo

- **Q** or **q**: Quit application
- **Space**: Pause/Resume processing
- **S** or **s**: Save screenshots (feature in development)

## Output Information

### Console Output
- Model loading status and device information
- Stream discovery and configuration
- Real-time API payloads for detected violations
- Performance and processing information

### Visual Output
- Multiple OpenCV windows showing live processing
- Vehicle detection with bounding boxes
- Illegal parking classification results
- Korean license plate recognition
- Processing timestamps and device info

## Troubleshooting

### Common Issues

1. **Models not found**: Ensure model files exist in `models/` directory
2. **CUDA errors**: Try `--device cpu` to test with CPU only
3. **Video not found**: Use `--list-streams` to see available streams
4. **Window positioning**: Adjust `--window-size` for your screen resolution

### Performance Tips

1. **For testing accuracy**: Use fewer streams with higher delay
2. **For performance testing**: Use more streams with lower delay
3. **For CPU systems**: Use `--device cpu --streams 2 --frame-delay 200`
4. **For GPU systems**: Use `--device cuda --streams 6 --frame-delay 50`

## API Payload Testing

The demo prints actual JSON payloads that would be sent to the backend API. This allows you to:

1. Validate API format without backend connection
2. Test Korean license plate recognition
3. Verify confidence scores and detection results
4. Debug AI pipeline processing

Example API payload:
```json
{
  "cctvId": 1,
  "timestamp": "2025-08-12T14:30:00.000Z",
  "location": {
    "latitude": 37.6158,
    "longitude": 126.8441
  },
  "vehicleImage": "data:image/jpeg;base64,...",
  "aiAnalysis": {
    "isIllegalByModel": true,
    "modelConfidence": 0.87,
    "vehicleType": "car",
    "licensePlateDetected": true,
    "licensePlateText": "123가4567",
    "plateConfidence": 0.92
  }
}
```

## Technical Details

### AI Models Used
- Vehicle Detection: Ultralytics YOLO (yolo_vehicle_v1.pt)
- Illegal Parking Classification: Ultralytics YOLO (yolo_illegal_v1.pt)  
- License Plate Detection: Ultralytics YOLO (yolo_plate_detector_v1.pt)
- OCR Recognition: EasyOCR with custom Korean model (custom_example)

### Window Layout
- 1 stream: Center position
- 2 streams: Side by side
- 3 streams: Horizontal row
- 4 streams: 2x2 grid
- 5 streams: 2 top, 3 bottom
- 6 streams: 2x3 grid