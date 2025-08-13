package com.aivle.ParkingDetection.dto;

import com.fasterxml.jackson.annotation.JsonProperty;
import lombok.*;

import java.time.LocalDateTime;

@Getter @Setter
@NoArgsConstructor
@AllArgsConstructor
@Builder
public class AiReportResponse {
    private Boolean success;
    
    @JsonProperty("detection_id")
    private Long detectionId;
    
    private String message;
    
    @JsonProperty("error_code")
    private String errorCode;
    
    private String timestamp;
    
    // SUCCESS RESPONSE FACTORY METHOD
    public static AiReportResponse success(Long detectionId, String message) {
        return AiReportResponse.builder()
                .success(true)
                .detectionId(detectionId)
                .message(message)
                .timestamp(LocalDateTime.now().toString())
                .build();
    }
    
    // ERROR RESPONSE FACTORY METHOD
    public static AiReportResponse error(String errorCode, String message) {
        return AiReportResponse.builder()
                .success(false)
                .errorCode(errorCode)
                .message(message)
                .timestamp(LocalDateTime.now().toString())
                .build();
    }
}