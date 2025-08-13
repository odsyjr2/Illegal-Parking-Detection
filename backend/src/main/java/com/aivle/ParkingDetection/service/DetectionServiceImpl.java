package com.aivle.ParkingDetection.service;

import java.time.LocalDateTime;
import com.aivle.ParkingDetection.dto.*;
import com.aivle.ParkingDetection.domain.Detection;
import com.aivle.ParkingDetection.repository.DetectionRepository;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Service;

import java.util.List;
import java.util.stream.Collectors;

@Slf4j
@Service
@RequiredArgsConstructor
public class DetectionServiceImpl implements DetectionService {

    private final DetectionRepository repository;

    // ORIGINAL CODE - PRESERVED FOR BACKWARD COMPATIBILITY
    // @Override
    // public DetectionResponseDto saveDetection(DetectionRequestDto dto) {
    //     Detection saved = repository.save(
    //             Detection.builder()
    //                     .imageUrl(dto.getImageUrl())
    //                     .location(dto.getLocation())
    //                     .detectedAt(dto.getDetectedAt())
    //                     .vehicleType(dto.getVehicleType())
    //                     .isIllegal(dto.isIllegal())
    //                     .build()
    //     );
    //     return toDto(saved);
    // }

    // AI INTEGRATION - ENHANCED IMPLEMENTATION
    @Override
    public DetectionResponseDto saveDetection(DetectionRequestDto dto) {
        Detection saved = repository.save(
                Detection.builder()
                        // Original fields
                        .imageUrl(dto.getImageUrl())
                        .location(dto.getLocation())
                        .detectedAt(dto.getDetectedAt())
                        .vehicleType(dto.getVehicleType())
                        .isIllegal(dto.isIllegal())
                        // AI integration fields
                        .plateNumber(dto.getPlateNumber())
                        .reportType(dto.getReportType())
                        .cctvId(dto.getCctvId())
                        .latitude(dto.getLatitude())
                        .longitude(dto.getLongitude())
                        .correlationId(dto.getCorrelationId())
                        .violationSeverity(dto.getViolationSeverity())
                        .build()
        );
        return toDto(saved);
    }

    @Override
    public List<DetectionResponseDto> getAllDetections() {
        return repository.findAll().stream().map(this::toDto).collect(Collectors.toList());
    }

    @Override
    public DetectionResponseDto getDetection(Long id) {
        Detection detection = repository.findById(id).orElseThrow();
        return toDto(detection);
    }

    @Override
    public List<DetectionResponseDto> getDetectionsByTimeRange(LocalDateTime from, LocalDateTime to) {
        return repository.findByDetectedAtBetween(from, to)
                .stream().map(this::toDto).collect(Collectors.toList());
    }

    // ORIGINAL CODE - PRESERVED FOR REFERENCE
    // private DetectionResponseDto toDto(Detection detection) {
    //     return DetectionResponseDto.builder()
    //             .id(detection.getId())
    //             .imageUrl(detection.getImageUrl())
    //             .location(detection.getLocation())
    //             .detectedAt(detection.getDetectedAt())
    //             .vehicleType(detection.getVehicleType())
    //             .illegal(detection.isIllegal())
    //             .build();
    // }

    // AI INTEGRATION - ENHANCED MAPPING
    private DetectionResponseDto toDto(Detection detection) {
        return DetectionResponseDto.builder()
                // Original fields
                .id(detection.getId())
                .imageUrl(detection.getImageUrl())
                .location(detection.getLocation())
                .detectedAt(detection.getDetectedAt())
                .vehicleType(detection.getVehicleType())
                .illegal(detection.isIllegal())
                // AI integration fields
                .plateNumber(detection.getPlateNumber())
                .reportType(detection.getReportType())
                .cctvId(detection.getCctvId())
                .latitude(detection.getLatitude())
                .longitude(detection.getLongitude())
                .correlationId(detection.getCorrelationId())
                .violationSeverity(detection.getViolationSeverity())
                .build();
    }

    // AI INTEGRATION - NEW METHOD IMPLEMENTATION
    @Override
    public DetectionResponseDto saveAiDetection(DetectionRequestDto dto, boolean aiProcessed) {
        // Additional validation for AI-processed detections
        if (aiProcessed) {
            validateAiDetectionData(dto);
        }
        
        // Use existing saveDetection method which now handles AI fields
        DetectionResponseDto result = saveDetection(dto);
        
        if (aiProcessed) {
            log.info("AI detection saved successfully: ID={}, EventID={}, PlateNumber={}", 
                    result.getId(), result.getCorrelationId(), result.getPlateNumber());
        }
        
        return result;
    }
    
    /**
     * Validate AI-specific detection data
     */
    private void validateAiDetectionData(DetectionRequestDto dto) {
        // Validate CCTV ID
        if (dto.getCctvId() == null || dto.getCctvId().trim().isEmpty()) {
            throw new IllegalArgumentException("CCTV ID is required for AI detections");
        }
        
        // Validate report type
        if (dto.getReportType() == null || dto.getReportType().trim().isEmpty()) {
            throw new IllegalArgumentException("Report type is required for AI detections");
        }
        
        // Validate violation severity
        if (dto.getViolationSeverity() != null && 
            (dto.getViolationSeverity() < 0.0 || dto.getViolationSeverity() > 1.0)) {
            throw new IllegalArgumentException("Violation severity must be between 0.0 and 1.0");
        }
        
        // Log validation success
        log.debug("AI detection validation passed for CCTV: {}, Report Type: {}", 
                dto.getCctvId(), dto.getReportType());
    }
}
