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
        
        // Step 1: Validate AI event structure
        validateAiEvent(aiEvent);
        
        // Step 2: Apply business logic validation
        boolean isConfirmedViolation = applyBusinessRules(aiEvent);
        
        if (!isConfirmedViolation) {
            log.info("AI violation event {} not confirmed by business rules", aiEvent.getEventId());
            return null; // Or throw exception based on requirements
        }
        
        // Step 3: Transform AI event to Detection
        DetectionRequestDto detectionRequest = transformAiEventToDetectionRequest(aiEvent);
        
        // Step 4: Save detection using AI-specific service method
        DetectionResponseDto savedDetection = detectionService.saveAiDetection(detectionRequest, true);
        
        log.info("AI violation event {} processed successfully, detection ID: {}", 
                aiEvent.getEventId(), savedDetection.getId());
        
        return savedDetection.getId();
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
        
        // Convert timestamp to LocalDateTime
        LocalDateTime detectedAt = LocalDateTime.now(); // Default to now
        if (violation.getStartTime() != null) {
            detectedAt = LocalDateTime.ofInstant(
                    Instant.ofEpochSecond(violation.getStartTime().longValue()),
                    ZoneId.systemDefault()
            );
        }
        
        // Extract vehicle position for coordinates
        Double latitude = null;
        Double longitude = null;
        if (data.getVehicle() != null && data.getVehicle().getLastPosition() != null 
            && data.getVehicle().getLastPosition().length >= 2) {
            longitude = data.getVehicle().getLastPosition()[0]; // Usually [longitude, latitude]
            latitude = data.getVehicle().getLastPosition()[1];
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
                .illegal(violation.getIsConfirmed() != null ? violation.getIsConfirmed() : true)
                // AI integration fields
                .plateNumber(plateNumber)
                .reportType(aiEvent.getEventType())
                .cctvId(aiEvent.getStreamId())
                .latitude(latitude)
                .longitude(longitude)
                .correlationId(aiEvent.getCorrelationId())
                .violationSeverity(violation.getViolationSeverity())
                .build();
    }
    
    /**
     * Apply business rules for violation confirmation
     * Core Logic: IF (AI_illegal_classification == true) AND (location/time NOT in legal_parking_zones) 
     *            THEN confirmed_violation
     */
    private boolean applyBusinessRules(AiViolationEvent aiEvent) {
        AiViolationEvent.ViolationInfo violation = aiEvent.getData().getViolation();
        
        // Rule 1: AI must confirm the violation
        if (violation.getIsConfirmed() == null || !violation.getIsConfirmed()) {
            log.debug("Business rule failed: AI did not confirm violation for event {}", 
                    aiEvent.getEventId());
            return false;
        }
        
        // Rule 2: Violation severity must meet minimum threshold
        double minimumSeverity = 0.7; // Configurable threshold
        if (violation.getViolationSeverity() < minimumSeverity) {
            log.debug("Business rule failed: Violation severity {} below threshold {} for event {}", 
                    violation.getViolationSeverity(), minimumSeverity, aiEvent.getEventId());
            return false;
        }
        
        // Rule 3: Check parking zone rules using integrated service
        LocalDateTime detectionTime = LocalDateTime.now();
        if (violation.getStartTime() != null) {
            detectionTime = LocalDateTime.ofInstant(
                    Instant.ofEpochSecond(violation.getStartTime().longValue()),
                    ZoneId.systemDefault()
            );
        }
        
        // Extract coordinates for validation
        Double latitude = null;
        Double longitude = null;
        if (aiEvent.getData().getVehicle() != null && 
            aiEvent.getData().getVehicle().getLastPosition() != null &&
            aiEvent.getData().getVehicle().getLastPosition().length >= 2) {
            longitude = aiEvent.getData().getVehicle().getLastPosition()[0];
            latitude = aiEvent.getData().getVehicle().getLastPosition()[1];
        }
        
        boolean violationConfirmed = parkingZoneService.validateViolationByRules(
                aiEvent.getStreamId(), detectionTime, latitude, longitude);
        
        if (!violationConfirmed) {
            log.debug("Business rule failed: Parking zone validation rejected violation for event {}", 
                    aiEvent.getEventId());
            return false;
        }
        
        log.debug("Business rules passed for AI violation event: {}", aiEvent.getEventId());
        return true;
    }
}