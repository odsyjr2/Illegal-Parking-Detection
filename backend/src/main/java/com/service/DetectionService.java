package com.aivle.parkingdetection.service;

import com.aivle.parkingdetection.dto.*;
import java.time.LocalDateTime;
import java.util.List;

public interface DetectionService {
    DetectionResponseDto saveDetection(DetectionRequestDto dto);
    List<DetectionResponseDto> getAllDetections();
    DetectionResponseDto getDetection(Long id);
    List<DetectionResponseDto> getDetectionsByTimeRange(LocalDateTime from, LocalDateTime to);
}
