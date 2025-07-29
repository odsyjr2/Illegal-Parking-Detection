package com.aivle.ParkingDetection.service;

import java.time.LocalDateTime;
import com.aivle.ParkingDetection.dto.*;
import com.aivle.ParkingDetection.domain.Detection;
import com.aivle.ParkingDetection.repository.DetectionRepository;
import lombok.RequiredArgsConstructor;
import org.springframework.stereotype.Service;

import java.util.List;
import java.util.stream.Collectors;

@Service
@RequiredArgsConstructor
public class DetectionServiceImpl implements DetectionService {

    private final DetectionRepository repository;

    @Override
    public DetectionResponseDto saveDetection(DetectionRequestDto dto) {
        Detection saved = repository.save(
                Detection.builder()
                        .imageUrl(dto.getImageUrl())
                        .location(dto.getLocation())
                        .detectedAt(dto.getDetectedAt())
                        .vehicleType(dto.getVehicleType())
                        .isIllegal(dto.isIllegal())
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

    private DetectionResponseDto toDto(Detection detection) {
        return DetectionResponseDto.builder()
                .id(detection.getId())
                .imageUrl(detection.getImageUrl())
                .location(detection.getLocation())
                .detectedAt(detection.getDetectedAt())
                .vehicleType(detection.getVehicleType())
                .illegal(detection.isIllegal())
                .build();
    }
}
