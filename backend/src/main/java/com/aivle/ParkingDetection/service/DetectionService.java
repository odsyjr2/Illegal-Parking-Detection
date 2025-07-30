package com.aivle.ParkingDetection.service;

import com.aivle.ParkingDetection.dto.*;
import java.time.LocalDateTime;
import java.util.List;

public interface DetectionService {
    DetectionResponseDto saveDetection(DetectionRequestDto dto);
    List<DetectionResponseDto> getAllDetections();
    DetectionResponseDto getDetection(Long id);
    List<DetectionResponseDto> getDetectionsByTimeRange(LocalDateTime from, LocalDateTime to);
}
