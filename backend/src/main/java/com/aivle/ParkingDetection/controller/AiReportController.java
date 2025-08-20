package com.aivle.ParkingDetection.controller;

import com.aivle.ParkingDetection.dto.AiReportResponse;
import com.aivle.ParkingDetection.dto.AiViolationEvent;
import com.aivle.ParkingDetection.service.AiReportProcessingService;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

@Slf4j
@RestController
@RequiredArgsConstructor
@RequestMapping("/api/ai/v1")
public class AiReportController {

    private final AiReportProcessingService aiReportProcessingService;

    /**
     * AI Processor Integration Endpoint
     * Receives violation reports from AI processor (event_reporter.py)
     *
     * @param aiEvent AI violation event from AI processor
     * @return Standardized response for AI processor retry mechanism
     */
    @PostMapping("/report-detection")
    public ResponseEntity<AiReportResponse> reportDetection(@RequestBody AiViolationEvent aiEvent) {
        try {
            log.info("Received AI violation report: eventId={}, streamId={}, eventType={}",
                    aiEvent.getEventId(), aiEvent.getStreamId(), aiEvent.getEventType());

            // AI INTEGRATION - PROCESS VIOLATION EVENT
            Long detectionId = aiReportProcessingService.processViolationEvent(aiEvent);

            // Log AI event details for debugging
            if (aiEvent.getData() != null && aiEvent.getData().getLicensePlate() != null) {
                log.info("License plate detected: {}, confidence: {}",
                        aiEvent.getData().getLicensePlate().getPlateText(),
                        aiEvent.getData().getLicensePlate().getConfidence());
            }

            if (aiEvent.getData() != null && aiEvent.getData().getViolation() != null) {
                log.info("Violation severity: {}, duration: {} seconds",
                        aiEvent.getData().getViolation().getViolationSeverity(),
                        aiEvent.getData().getViolation().getDuration());
            }

            AiReportResponse response = AiReportResponse.success(detectionId,
                    "Violation report processed successfully");

            return ResponseEntity.ok(response);

        } catch (IllegalArgumentException e) {
            log.error("Validation error processing AI violation report: {}", e.getMessage());
            AiReportResponse errorResponse = AiReportResponse.error("VALIDATION_ERROR", e.getMessage());
            return ResponseEntity.badRequest().body(errorResponse);

        } catch (Exception e) {
            log.error("Error processing AI violation report: {}", e.getMessage(), e);
            AiReportResponse errorResponse = AiReportResponse.error("PROCESSING_ERROR",
                    "Internal server error processing violation report");
            return ResponseEntity.status(HttpStatus.INTERNAL_SERVER_ERROR).body(errorResponse);
        }
    }

    /**
     * Health check endpoint for AI processor
     */
    @GetMapping("/health")
    public ResponseEntity<String> healthCheck() {
        return ResponseEntity.ok("AI Integration Service is running");
    }
}