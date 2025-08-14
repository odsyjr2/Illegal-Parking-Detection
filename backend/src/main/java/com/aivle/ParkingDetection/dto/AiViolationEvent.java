package com.aivle.ParkingDetection.dto;

import com.fasterxml.jackson.annotation.JsonProperty;
import lombok.*;

import java.time.LocalDateTime;

@Getter @Setter
@NoArgsConstructor
@AllArgsConstructor
@Builder
public class AiViolationEvent {
    @JsonProperty("event_id")
    private String eventId;
    
    @JsonProperty("event_type")
    private String eventType;
    
    private String priority;
    
    private Double timestamp;
    
    @JsonProperty("timestamp_iso")
    private String timestampIso;
    
    @JsonProperty("stream_id")
    private String streamId;
    
    @JsonProperty("correlation_id")
    private String correlationId;
    
    private ViolationData data;
    
    @Getter @Setter
    @NoArgsConstructor
    @AllArgsConstructor
    @Builder
    public static class ViolationData {
        private ViolationInfo violation;
        private VehicleInfo vehicle;
        
        @JsonProperty("license_plate")
        private LicensePlateInfo licensePlate;
        
        @JsonProperty("ocr_result")
        private OcrResult ocrResult;
        
        @JsonProperty("stream_info")
        private StreamInfo streamInfo;
        
        // AI INTEGRATION - IMAGE SUPPORT
        @JsonProperty("vehicle_image")
        private String vehicleImage;  // Base64 encoded violation image from AI processor
    }
    
    @Getter @Setter
    @NoArgsConstructor
    @AllArgsConstructor
    @Builder
    public static class ViolationInfo {
        @JsonProperty("event_id")
        private String eventId;
        
        @JsonProperty("stream_id")
        private String streamId;
        
        @JsonProperty("start_time")
        private Double startTime;
        
        private Double duration;
        
        @JsonProperty("violation_severity")
        private Double violationSeverity;
        
        @JsonProperty("is_confirmed")
        private Boolean isConfirmed;
        
        @JsonProperty("vehicle_type")
        private String vehicleType;
        
        @JsonProperty("parking_zone_type")
        private String parkingZoneType;
    }
    
    @Getter @Setter
    @NoArgsConstructor
    @AllArgsConstructor
    @Builder
    public static class VehicleInfo {
        @JsonProperty("track_id")
        private String trackId;
        
        @JsonProperty("vehicle_type")
        private String vehicleType;
        
        private Double confidence;
        
        @JsonProperty("bounding_box")
        private Double[] boundingBox;
        
        @JsonProperty("last_position")
        private Double[] lastPosition;
    }
    
    @Getter @Setter
    @NoArgsConstructor
    @AllArgsConstructor
    @Builder
    public static class LicensePlateInfo {
        @JsonProperty("plate_text")
        private String plateText;
        
        private Double confidence;
        
        @JsonProperty("bounding_box")
        private Double[] boundingBox;
        
        @JsonProperty("is_valid_format")
        private Boolean isValidFormat;
    }
    
    @Getter @Setter
    @NoArgsConstructor
    @AllArgsConstructor
    @Builder
    public static class OcrResult {
        @JsonProperty("recognized_text")
        private String recognizedText;
        
        private Double confidence;
        
        @JsonProperty("is_valid_format")
        private Boolean isValidFormat;
    }
    
    @Getter @Setter
    @NoArgsConstructor
    @AllArgsConstructor
    @Builder
    public static class StreamInfo {
        @JsonProperty("stream_id")
        private String streamId;
        
        @JsonProperty("location_name")
        private String locationName;
    }
}