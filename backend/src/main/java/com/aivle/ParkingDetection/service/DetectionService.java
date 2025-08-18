package com.aivle.ParkingDetection.service;

import com.aivle.ParkingDetection.dto.*;
import java.time.LocalDateTime;
import java.util.List;

public interface DetectionService {
    // ORIGINAL METHODS - PRESERVED FOR BACKWARD COMPATIBILITY
    DetectionResponseDto saveDetection(DetectionRequestDto dto);
    List<DetectionResponseDto> getAllDetections();
    DetectionResponseDto getDetection(Long id);
    List<DetectionResponseDto> getDetectionsByTimeRange(LocalDateTime from, LocalDateTime to);
    
    // AI INTEGRATION - NEW METHODS
    /**
     * Save AI-processed detection with enhanced validation
     * @param dto Detection request with AI integration fields
     * @param aiProcessed Flag to indicate AI-processed data
     * @return Saved detection response
     */
    DetectionResponseDto saveAiDetection(DetectionRequestDto dto, boolean aiProcessed);
}
