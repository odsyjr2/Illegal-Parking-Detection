# Configuration Directory

## Purpose
This directory contains all configuration files for the AI system. All paths, parameters, and settings are centrally managed here to ensure easy maintenance and deployment flexibility.

## Configuration Files

### config.yaml
The main configuration file containing:

#### Model Configuration
- Paths to all YOLO and OCR model weights
- Model-specific parameters (confidence thresholds, NMS settings)
- GPU/CPU processing preferences

#### CCTV Stream Configuration
- Multiple CCTV stream definitions (local/live)
- Stream-specific parameters (resolution, FPS, coordinates)
- Location mappings (latitude/longitude per camera)

#### Processing Parameters
- Vehicle tracking settings (max tracking distance, timeout)
- Parking duration thresholds (how long = "parked too long")
- Analysis intervals and batch processing settings

#### API Configuration
- FastAPI server settings (host, port, CORS)
- Endpoint configurations and rate limiting
- Integration settings for Spring backend communication

#### Visualization Options
- Enable/disable real-time tracking windows
- Display settings and window configurations
- Logging and debug visualization options

## Usage
All application modules read from `config.yaml` at startup. No hardcoded paths or parameters should exist in the codebase.

## Environment-Specific Configs
- `config.yaml` - Development/local testing
- `config_prod.yaml` - Production deployment (planned)
- `config_test.yaml` - Unit testing configuration (planned)