package com.aivle.ParkingDetection.service;

import com.aivle.ParkingDetection.dto.AiViolationEvent;
import com.aivle.ParkingDetection.dto.DetectionResponseDto;

/**
 * AI Report Processing Service Interface
 * Core business logic for processing AI processor violation reports
 */
public interface AiReportProcessingService {
    
    /**
     * Process AI violation event and create Detection record
     * 
     * @param aiEvent AI violation event from AI processor
     * @return Detection ID of created record
     * @throws IllegalArgumentException if validation fails
     */
    Long processViolationEvent(AiViolationEvent aiEvent);
    
    /**
     * Validate AI violation event structure and data
     * 
     * @param aiEvent AI violation event to validate
     * @throws IllegalArgumentException if validation fails
     */
    void validateAiEvent(AiViolationEvent aiEvent);
    
    /**
     * Transform AI violation event to Detection entity data
     * 
     * @param aiEvent AI violation event
     * @return DetectionResponseDto with transformed data
     */
    DetectionResponseDto transformAiEventToDetection(AiViolationEvent aiEvent);
}