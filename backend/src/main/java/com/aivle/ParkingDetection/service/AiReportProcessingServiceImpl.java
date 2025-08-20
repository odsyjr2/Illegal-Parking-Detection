package com.aivle.ParkingDetection.service;

import com.aivle.ParkingDetection.domain.Detection;
import com.aivle.ParkingDetection.dto.AiViolationEvent;
import com.aivle.ParkingDetection.dto.DetectionRequestDto;
import com.aivle.ParkingDetection.dto.DetectionResponseDto;
import com.aivle.ParkingDetection.repository.DetectionRepository;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.time.Instant;
import java.time.LocalDateTime;
import java.time.ZoneId;

@Slf4j
@Service
@RequiredArgsConstructor
@Transactional
public class AiReportProcessingServiceImpl implements AiReportProcessingService {

    private final DetectionRepository detectionRepository;
    private final DetectionService detectionService;
    private final ParkingZoneService parkingZoneService;
    private final FileStorageService fileStorageService;  // AI INTEGRATION - Image storage

    @Override
    public Long processViolationEvent(AiViolationEvent aiEvent) {
        log.info("Processing AI violation event: {}", aiEvent.getEventId());
        
        // Validate AI event structure (기존 구조적 검증 유지)
        validateAiEvent(aiEvent);
        
        // 1단계: AI 탐지 품질 검증 (임계값 기반)
        if (!validateAiDetection(aiEvent)) {
            log.info("AI detection quality insufficient: {}", aiEvent.getEventId());
            return null; // IGNORE 처리
        }
        
        // 2단계: 주차규칙 검증 (하이브리드 매칭)
        if (!validateParkingRules(aiEvent)) {
            log.info("Legal parking detected: {}", aiEvent.getEventId());
            return null; // LEGAL_PARKING 처리
        }
        
        // 3단계: OCR 품질 기반 분기 처리
        if (evaluateOcrQuality(aiEvent)) {
            return processAutoReport(aiEvent); // AUTO_REPORT
        } else {
            return processRouteRecommendation(aiEvent); // ROUTE_RECOMMENDATION  
        }
    }

    @Override
    public void validateAiEvent(AiViolationEvent aiEvent) {
        if (aiEvent == null) {
            throw new IllegalArgumentException("AI event cannot be null");
        }
        
        if (aiEvent.getEventId() == null || aiEvent.getEventId().trim().isEmpty()) {
            throw new IllegalArgumentException("Event ID is required");
        }
        
        if (aiEvent.getStreamId() == null || aiEvent.getStreamId().trim().isEmpty()) {
            throw new IllegalArgumentException("Stream ID is required");
        }
        
        if (aiEvent.getData() == null) {
            throw new IllegalArgumentException("Event data is required");
        }
        
        if (aiEvent.getData().getViolation() == null) {
            throw new IllegalArgumentException("Violation data is required");
        }
        
        // Validate violation severity
        AiViolationEvent.ViolationInfo violation = aiEvent.getData().getViolation();
        if (violation.getViolationSeverity() == null || 
            violation.getViolationSeverity() < 0.0 || 
            violation.getViolationSeverity() > 1.0) {
            throw new IllegalArgumentException("Violation severity must be between 0.0 and 1.0");
        }
        
        log.debug("AI event validation passed for event: {}", aiEvent.getEventId());
    }

    @Override
    public DetectionResponseDto transformAiEventToDetection(AiViolationEvent aiEvent) {
        // This method returns DetectionResponseDto as per interface
        // But we need DetectionRequestDto for saving - see private method below
        return null; // Not used in current implementation
    }
    
    /**
     * Transform AI violation event to DetectionRequestDto for saving
     */
    private DetectionRequestDto transformAiEventToDetectionRequest(AiViolationEvent aiEvent) {
        AiViolationEvent.ViolationData data = aiEvent.getData();
        AiViolationEvent.ViolationInfo violation = data.getViolation();
        
        // Extract license plate information
        String plateNumber = null;
        if (data.getLicensePlate() != null && data.getLicensePlate().getPlateText() != null) {
            plateNumber = data.getLicensePlate().getPlateText();
        } else if (data.getOcrResult() != null && data.getOcrResult().getRecognizedText() != null) {
            plateNumber = data.getOcrResult().getRecognizedText();
        }
        
        // Extract location information
        String location = data.getStreamInfo() != null ? 
                data.getStreamInfo().getLocationName() : "Unknown Location";
        
        // Phase 2: AI 역지오코딩 연동 - 주소 정보 추출
        String address = null;
        String formattedAddress = null;
        Double latitude = null;
        Double longitude = null;
        
        if (data.getStreamInfo() != null) {
            // 역지오코딩된 주소 정보 추출
            address = data.getStreamInfo().getAddress();
            formattedAddress = data.getStreamInfo().getFormattedAddress();
            latitude = data.getStreamInfo().getLatitude();
            longitude = data.getStreamInfo().getLongitude();
            
            log.debug("Geocoded address for event {}: {}", aiEvent.getEventId(), formattedAddress);
        }
        
        // Fallback: 새 좌표 정보가 없으면 기존 vehicle 위치 사용
        if (latitude == null || longitude == null) {
            if (data.getVehicle() != null && data.getVehicle().getLastPosition() != null 
                && data.getVehicle().getLastPosition().length >= 2) {
                longitude = data.getVehicle().getLastPosition()[0]; // Usually [longitude, latitude]
                latitude = data.getVehicle().getLastPosition()[1];
                log.debug("Using fallback coordinates from vehicle position for event {}", aiEvent.getEventId());
            }
        }
        
        // Convert timestamp to LocalDateTime
        LocalDateTime detectedAt = LocalDateTime.now(); // Default to now
        if (violation.getStartTime() != null) {
            detectedAt = LocalDateTime.ofInstant(
                    Instant.ofEpochSecond(violation.getStartTime().longValue()),
                    ZoneId.systemDefault()
            );
        }
        
        // AI INTEGRATION - Handle Base64 image storage
        String imageUrl = "";
        if (data.getVehicleImage() != null && !data.getVehicleImage().trim().isEmpty()) {
            try {
                imageUrl = fileStorageService.storeBase64Image(
                    data.getVehicleImage(), 
                    aiEvent.getEventId(), 
                    aiEvent.getStreamId()
                );
                log.info("Stored violation image for event {}: {}", aiEvent.getEventId(), imageUrl);
            } catch (Exception e) {
                log.error("Failed to store violation image for event {}: {}", aiEvent.getEventId(), e.getMessage());
                // Continue processing without image - image storage failure shouldn't block violation recording
            }
        } else {
            log.debug("No vehicle image provided for event {}", aiEvent.getEventId());
        }
        
        return DetectionRequestDto.builder()
                // Original fields
                .imageUrl(imageUrl)  // AI INTEGRATION - Set stored image URL
                .location(location)
                .detectedAt(detectedAt)
                .vehicleType(violation.getVehicleType())
                // illegal 필드 제거: 모든 Detection은 불법주정차 확정
                // AI integration fields
                .plateNumber(plateNumber)
                .reportType(aiEvent.getEventType())
                .cctvId(aiEvent.getStreamId())
                .latitude(latitude)
                .longitude(longitude)
                .correlationId(aiEvent.getCorrelationId())
                .violationSeverity(violation.getViolationSeverity())
                // Phase 2: AI 역지오코딩 연동 - 주소 정보 추가
                .address(address)
                .formattedAddress(formattedAddress)
                .build();
    }
    
    /**
     * 1단계: AI 탐지 품질 검증 (임계값 기반)
     */
    private boolean validateAiDetection(AiViolationEvent aiEvent) {
        AiViolationEvent.ViolationInfo violation = aiEvent.getData().getViolation();
        
        // AI 확신도 임계값 검증 (0.7 이상)
        if (violation.getViolationSeverity() == null || 
            violation.getViolationSeverity() < 0.7) {
            log.debug("AI violation severity {} below threshold 0.7 for event {}", 
                     violation.getViolationSeverity(), aiEvent.getEventId());
            return false;
        }
        
        // AI 확정 여부 체크
        if (!Boolean.TRUE.equals(violation.getIsConfirmed())) {
            log.debug("AI violation not confirmed: {} for event {}", 
                     violation.getIsConfirmed(), aiEvent.getEventId());
            return false;
        }
        
        log.debug("AI detection validation passed for event: {}", aiEvent.getEventId());
        return true;
    }
    
    /**
     * 2단계: 주차규칙 검증 (하이브리드 매칭)
     */
    private boolean validateParkingRules(AiViolationEvent aiEvent) {
        // 탐지 시간 추출
        LocalDateTime detectionTime = extractDetectionTime(aiEvent);
        
        // GPS 좌표 추출 (Phase 2: 역지오코딩 연동 좌표 우선)
        Double latitude = extractLatitude(aiEvent);
        Double longitude = extractLongitude(aiEvent);
        
        if (latitude == null || longitude == null) {
            log.warn("GPS coordinates missing for violation validation: {}", aiEvent.getEventId());
            return true; // 좌표 없으면 기본적으로 위반으로 처리
        }
        
        // ParkingZoneService를 통한 하이브리드 매칭
        boolean isViolation = parkingZoneService.validateViolationByRules(
                aiEvent.getStreamId(), detectionTime, latitude, longitude);
        
        log.debug("Parking rule validation for event {}: coordinates=({}, {}), violation={}", 
                 aiEvent.getEventId(), latitude, longitude, isViolation);
        
        return isViolation;
    }
    
    /**
     * 3단계: OCR 품질 평가
     */
    private boolean evaluateOcrQuality(AiViolationEvent aiEvent) {
        // 번호판 정보 추출
        String plateText = extractPlateNumber(aiEvent);
        Double confidence = extractOcrConfidence(aiEvent);
        Boolean isValidFormat = extractOcrValidFormat(aiEvent);
        
        // 고품질 OCR 조건: 텍스트 존재 + 신뢰도 0.8 이상 + 유효한 형식
        boolean isHighQuality = plateText != null && 
                               !plateText.trim().isEmpty() &&
                               confidence != null && 
                               confidence >= 0.8 && 
                               Boolean.TRUE.equals(isValidFormat);
        
        log.debug("OCR quality assessment for {}: text={}, confidence={}, valid={}, result={}", 
                 aiEvent.getEventId(), plateText, confidence, isValidFormat, isHighQuality);
        
        return isHighQuality;
    }
    
    /**
     * 자동 신고 처리 (고품질 OCR)
     */
    private Long processAutoReport(AiViolationEvent aiEvent) {
        log.info("Processing auto report for high-quality OCR: {}", aiEvent.getEventId());
        
        // 기존 transformAiEventToDetectionRequest 재사용
        DetectionRequestDto detectionRequest = transformAiEventToDetectionRequest(aiEvent);
        
        // 자동 신고용 설정 (isIllegal 필드 제거됨 - 모든 Detection은 불법주정차 확정)
        
        // Detection 저장 (기존 로직 재사용)
        DetectionResponseDto savedDetection = detectionService.saveAiDetection(detectionRequest, true);
        
        // 자동 신고 리포트 생성
        generateAutoReportIfNeeded(savedDetection, aiEvent);
        
        log.info("Auto report completed for violation: {}, Detection ID: {}", 
                 aiEvent.getEventId(), savedDetection.getId());
        
        return savedDetection.getId();
    }
    
    /**
     * 경로 추천 처리 (저품질 OCR)
     */
    private Long processRouteRecommendation(AiViolationEvent aiEvent) {
        log.info("Processing route recommendation for low-quality OCR: {}", aiEvent.getEventId());
        
        // 기존 transformAiEventToDetectionRequest 재사용
        DetectionRequestDto detectionRequest = transformAiEventToDetectionRequest(aiEvent);
        
        // 경로 추천용 설정 (isIllegal 필드 제거됨 - 모든 Detection은 불법주정차 확정)
        detectionRequest.setPlateNumber(null); // OCR 실패로 번호판 정보 없음
        
        // Detection 저장 (단속 필요 표시)
        DetectionResponseDto savedDetection = detectionService.saveAiDetection(detectionRequest, true);
        
        // 경로 추천 정보 제공
        provideRouteRecommendationIfNeeded(savedDetection, aiEvent);
        
        log.info("Route recommendation completed for violation: {}, Detection ID: {}", 
                 aiEvent.getEventId(), savedDetection.getId());
        
        return savedDetection.getId();
    }
    
    // === 헬퍼 메서드들 ===
    
    private LocalDateTime extractDetectionTime(AiViolationEvent aiEvent) {
        AiViolationEvent.ViolationInfo violation = aiEvent.getData().getViolation();
        
        if (violation.getStartTime() != null) {
            return LocalDateTime.ofInstant(
                    Instant.ofEpochSecond(violation.getStartTime().longValue()),
                    ZoneId.systemDefault()
            );
        }
        
        return LocalDateTime.now();
    }
    
    private Double extractLatitude(AiViolationEvent aiEvent) {
        // 우선: StreamInfo에서 역지오코딩된 좌표 사용
        if (aiEvent.getData().getStreamInfo() != null) {
            return aiEvent.getData().getStreamInfo().getLatitude();
        }
        
        // Fallback: 기존 vehicle 위치 사용
        if (aiEvent.getData().getVehicle() != null && 
            aiEvent.getData().getVehicle().getLastPosition() != null &&
            aiEvent.getData().getVehicle().getLastPosition().length >= 2) {
            return aiEvent.getData().getVehicle().getLastPosition()[1]; // latitude
        }
        
        return null;
    }
    
    private Double extractLongitude(AiViolationEvent aiEvent) {
        // 우선: StreamInfo에서 역지오코딩된 좌표 사용
        if (aiEvent.getData().getStreamInfo() != null) {
            return aiEvent.getData().getStreamInfo().getLongitude();
        }
        
        // Fallback: 기존 vehicle 위치 사용
        if (aiEvent.getData().getVehicle() != null && 
            aiEvent.getData().getVehicle().getLastPosition() != null &&
            aiEvent.getData().getVehicle().getLastPosition().length >= 2) {
            return aiEvent.getData().getVehicle().getLastPosition()[0]; // longitude
        }
        
        return null;
    }
    
    private String extractPlateNumber(AiViolationEvent aiEvent) {
        // 우선순위: LicensePlateInfo > OcrResult
        if (aiEvent.getData().getLicensePlate() != null && 
            aiEvent.getData().getLicensePlate().getPlateText() != null) {
            return aiEvent.getData().getLicensePlate().getPlateText();
        }
        
        if (aiEvent.getData().getOcrResult() != null &&
            aiEvent.getData().getOcrResult().getRecognizedText() != null) {
            return aiEvent.getData().getOcrResult().getRecognizedText();
        }
        
        return null;
    }
    
    private Double extractOcrConfidence(AiViolationEvent aiEvent) {
        if (aiEvent.getData().getLicensePlate() != null) {
            return aiEvent.getData().getLicensePlate().getConfidence();
        }
        
        if (aiEvent.getData().getOcrResult() != null) {
            return aiEvent.getData().getOcrResult().getConfidence();
        }
        
        return null;
    }
    
    private Boolean extractOcrValidFormat(AiViolationEvent aiEvent) {
        if (aiEvent.getData().getLicensePlate() != null) {
            return aiEvent.getData().getLicensePlate().getIsValidFormat();
        }
        
        if (aiEvent.getData().getOcrResult() != null) {
            return aiEvent.getData().getOcrResult().getIsValidFormat();
        }
        
        return null;
    }
    
    private void generateAutoReportIfNeeded(DetectionResponseDto detection, AiViolationEvent aiEvent) {
        // 자동 신고 리포트 생성 로직 (현재는 로그만)
        log.info("Auto report generated: Detection ID {}, Plate: {}", 
                 detection.getId(), detection.getPlateNumber());
        // TODO: 실제 신고 시스템 연동 구현
    }
    
    private void provideRouteRecommendationIfNeeded(DetectionResponseDto detection, AiViolationEvent aiEvent) {
        // 경로 추천 정보 제공 로직 (현재는 로그만)
        log.info("Route recommendation provided: Detection ID {}, Location: ({}, {})", 
                 detection.getId(), detection.getLatitude(), detection.getLongitude());
        // TODO: 경로 추천 시스템 연동 구현
    }
}