# Project: Illegal Parking Detection & Enforcement System

## 1. Project Overview

Illegal parking detection system with three-stage pipeline:
1. **Vehicle Tracking & Parking Detection** - YOLO-based real-time detection and duration monitoring
2. **Illegal Parking Verification** - AI classification + database validation via Spring backend
3. **Reporting & Data Provisioning** - OCR license plate recognition and violation report generation

**Architecture:** Standalone Python AI processor + Spring Boot backend + Frontend UI

## 2. Technical Stack

- **AI Processor:** Python, Ultralytics YOLO, EasyOCR (standalone daemon with two-phase processing)
- **Backend:** Spring Boot, H2 database (dev), JWT security
- **Frontend:** React with map interface
- **Integration:** REST API communication (AI → Backend via `POST /api/ai/v1/report-detection`)

## 3. ✅ IMPLEMENTATION STATUS

### 🎯 **AI PROCESSOR - COMPLETED**
**Status:** Production-ready standalone Python processor

**✅ Implemented Components:**
- **Two-Phase Architecture**: Lightweight monitoring + heavy analysis workers
- **AI Pipeline**: Vehicle tracking, parking detection, illegal classification, license plate detection, OCR
- **Configuration**: Multi-YAML system (`AI/config/`) with corrected paths
- **Testing Framework**: Visual testing, performance testing, integration testing
- **Backend Communication**: REST API integration with retry mechanisms (`event_reporter.py`)

**✅ Core Files Structure:**
```
AI/ai_server/
├── main.py                    # Standalone orchestrator
├── core/                      # Two-phase processing (monitoring.py, analysis.py)
├── workers/                   # Worker thread pool (analysis_worker.py)
├── utils/                     # Configuration & logging (config_loader.py, logger.py)
├── test/                      # Comprehensive testing framework
└── [AI modules]               # All AI components implemented
```

## 4. SYSTEM ARCHITECTURE

### 4.1. Python AI Processor (Standalone)
**Two-Phase Processing:**
1. **Phase 1 - Monitoring**: Lightweight CCTV stream monitoring, vehicle tracking, parking duration detection
2. **Phase 2 - Analysis**: Heavy AI processing (illegal classification, license plate detection, OCR)

**Communication**: Sends complete violation reports to Spring Backend via REST API with retry mechanisms

### 4.2. Spring Boot Backend (Central Orchestrator)  
**Core Logic**: `IF (AI_illegal_classification == true) AND (location/time NOT in legal_parking_zones) THEN confirmed_violation`

**Responsibilities:**
- Receive AI violation reports via `POST /api/ai/v1/report-detection`
- Final verification using database rules
- Data persistence and API service
- User/CCTV/parking zone management

## 5. 🚀 NEXT STEPS - BACKEND DEVELOPMENT

### 🎯 **IMMEDIATE PRIORITY: Spring Boot Backend Integration**  
**Focus:** Implement backend API functions, test AI-backend integration with H2 database, then migrate to production database.

### 5.1. Backend Implementation Blueprint

**Phase 1: Entity & Data Layer Updates**
- [ ] **Detection Entity Enhancement** (`Detection.java:15-24`)
  - Add fields: `String plateNumber`, `String reportType`, `String cctvId`, `Double latitude`, `Double longitude`
  - Update constructors, builder pattern, and DTOs accordingly
  - Ensure H2 database compatibility

**Phase 2: AI Integration Controller & Services**
- [ ] **AiReportController Creation**
  - Endpoint: `POST /api/ai/v1/report-detection`
  - Accept AI processor JSON payload (see Section 5.2)
  - Validation and routing to processing services
  
- [ ] **AiReportProcessingService Implementation**
  - Core business logic for AI violation report processing
  - Parking zone validation integration
  - Database persistence with enhanced Detection entity
  
- [ ] **FileStorageService Creation**
  - Handle Base64 image storage from AI processor
  - Image file management and retrieval APIs
  - Storage path configuration

**Phase 3: Enhanced Service Layer**
- [ ] **DetectionServiceImpl Enhancement** (`DetectionServiceImpl.java:20-31`)
  - Update `saveDetection()` method for AI reports
  - Add violation processing with parking zone validation
  - Integration with AiReportProcessingService

### 5.2. AI Processor Output Analysis

**Based on `event_reporter.py` Analysis:**

**AI Processor Event Structure:**
```json
{
  "event_id": "violation_detected_stream1_1703845234",
  "event_type": "violation_detected",
  "priority": "urgent|high|normal|low",
  "timestamp": 1703845234.567,
  "timestamp_iso": "2023-12-29T10:33:54.567Z",
  "stream_id": "cctv_001",
  "correlation_id": "parking_event_12345",
  "data": {
    "violation": {
      "event_id": "parking_event_12345",
      "stream_id": "cctv_001",
      "start_time": 1703845234.567,
      "duration": 125.3,
      "violation_severity": 0.85,
      "is_confirmed": true,
      "vehicle_type": "car",
      "parking_zone_type": "no_parking"
    },
    "vehicle": {
      "track_id": "vehicle_456",
      "vehicle_type": "car",
      "confidence": 0.92,
      "bounding_box": [100, 150, 300, 400],
      "last_position": [125.4, 37.5]
    },
    "license_plate": {
      "plate_text": "ABC1234",
      "confidence": 0.88,
      "bounding_box": [180, 320, 280, 350],
      "is_valid_format": true
    },
    "ocr_result": {
      "recognized_text": "ABC1234",
      "confidence": 0.88,
      "is_valid_format": true
    },
    "stream_info": {
      "stream_id": "cctv_001",
      "location_name": "Main Street Intersection"
    }
  }
}
```

### 5.3. Backend API Endpoint Specifications

**Primary Endpoint: `POST /api/ai/v1/report-detection`**

**Request Headers:**
- `Content-Type: application/json`
- `X-API-Key: <api_key>` (if authentication required)

**Request Body:** AI processor event JSON (see Section 5.2)

**Response Format:**
```json
{
  "success": true,
  "detection_id": 12345,
  "message": "Violation report processed successfully",
  "timestamp": "2023-12-29T10:33:54.567Z"
}
```

**Error Response:**
```json
{
  "success": false,
  "error_code": "VALIDATION_ERROR",
  "message": "Invalid license plate format",
  "timestamp": "2023-12-29T10:33:54.567Z"
}
```

### 5.4. Integration Testing Scenarios

**Test Scenario 1: Valid Violation Report**
- AI processor sends complete violation with license plate
- Backend validates, processes, and stores in H2 database
- Verify Detection entity creation with all fields

**Test Scenario 2: Violation Without License Plate**
- AI processor sends violation without OCR data
- Backend processes and stores with null plateNumber
- Verify system handles missing optional data

**Test Scenario 3: Retry Mechanism Testing**
- Simulate backend unavailability
- Verify AI processor retry logic (from `event_reporter.py:234-270`)
- Test exponential backoff and max retry limits

**Test Scenario 4: Invalid Data Handling**
- Send malformed JSON payload
- Verify backend validation and error responses
- Test graceful error handling

**Test Scenario 5: High Volume Testing**
- Multiple concurrent violation reports
- Verify backend performance and H2 database handling
- Test event queue processing (from `event_reporter.py:431-450`)

## 6. KEY IMPLEMENTATION INSTRUCTIONS

### 6.1. **⚠️ IMPLEMENTATION PRIORITIES & CHECKLIST**

**Implementation Order (Current Todo List):**
1. ✅ **Update CLAUDE.md with detailed AI-Backend integration blueprint**
2. ⏳ **Modify Detection entity** - Add `plateNumber`, `reportType`, `cctvId`, `latitude`, `longitude` fields
3. ⏳ **Create AiReportController** - Handle `POST /api/ai/v1/report-detection` endpoint  
4. ⏳ **Implement AiReportProcessingService** - Core AI report processing logic
5. ⏳ **Create FileStorageService** - Base64 image storage and retrieval
6. ⏳ **Enhance DetectionServiceImpl** - Process AI violation reports
7. ⏳ **Implement parking zone validation logic** - Backend services integration
8. ⏳ **Test AI → Backend communication** - Real violation data scenarios
9. ⏳ **Validate JSON payload format** - Matches AI processor output
10. ⏳ **Test error handling and retry mechanisms** - End-to-end validation

**Development Focus:**
1. **Backend API Development FIRST** - Implement all backend functions before database migration
2. **H2 Database for Testing** - Use H2 for integration testing, postpone production DB migration  
3. **No New File Creation** - Edit existing files, avoid creating new files unless absolutely necessary
4. **Follow User Blueprint** - Implementation order: Backend APIs → AI-Backend Integration Testing → Database Migration

**API Integration Requirements:**
- **AI Processor → Backend**: `POST /api/ai/v1/report-detection` endpoint (see Section 5.3)
- **JSON Payload Structure**: Matches `event_reporter.py` output format (see Section 5.2)
- **Retry Mechanisms**: Backend must handle AI processor retry logic (lines 234-270 in `event_reporter.py`)
- **H2 Database**: Use for all testing scenarios before production migration

### 6.2. **📁 CONFIGURATION FILES**

**Multi-YAML Configuration Structure:**
```
AI/config/
├── config.yaml              # Main application configuration  
├── models.yaml              # AI model paths (✅ corrected)
├── streams.yaml             # CCTV streams (✅ corrected)  
└── processing.yaml          # Processing parameters
```

**Key Configuration Points:**
- All model paths corrected to match directory structure
- 6 test video directories configured for testing
- Multi-YAML configuration loader implemented (`utils/config_loader.py`)

---

## 7. 🚀 FUTURE IMPLEMENTATION ROADMAP

### 7.1. **Frontend Development** (After Backend Complete)
- Real-time violation dashboard with map interface
- Admin panel for CCTV/parking zone management  
- Violation reporting and analytics features

### 7.2. **Production Deployment** (Final Phase)
- Docker containerization for AI processor and backend
- Production database migration (PostGIS for geospatial queries)
- Monitoring, logging, and alerting systems

### 7.3. **Performance Optimization**
- AI model quantization and batch processing optimization
- Horizontal scaling for multiple AI processor instances
- Database optimization for high-volume violation data

---

**🎯 CURRENT FOCUS: Backend API development and AI-Backend integration testing with H2 database**

---

## 📋 IMPLEMENTATION STATUS TRACKING

### ✅ **COMPLETED TASKS**
- [x] AI Processor development (Production-ready)
- [x] AI-Backend integration blueprint and detailed specifications
- [x] Analysis of AI processor output format (`event_reporter.py`)
- [x] JSON payload structure documentation
- [x] Integration testing scenarios definition

### 🔄 **IN PROGRESS**
- [ ] Backend API implementation for AI integration

### ⏭️ **NEXT IMMEDIATE STEPS**
1. **Test Current Backend Structure** - Verify Spring Boot + H2 database setup
2. **Modify Detection Entity** - Add required fields for AI integration
3. **Create AI Integration Controller** - Handle `POST /api/ai/v1/report-detection`
4. **Implement Processing Services** - Core logic for AI violation reports
- I want to know where does code modified. don't delete current codebase. If it's necessary to modify, just comment out current code and edit new one.
- todo : live cctv stream connection and test AI system., integrate frontend visualizing area-live cctv stream., frontend pop-up notification function when detection event occured in AI system.
- I want to test an integration test that includes all of the frontend, backend, AI. I'm going to unannotate the frontend-related features that I commented out for backend-AI feature test and integrate them with newely added code.