package com.aivle.parkingdetection.controller;

import com.aivle.parkingdetection.dto.*;
import com.aivle.parkingdetection.service.DetectionService;
import lombok.RequiredArgsConstructor;
import org.springframework.format.annotation.DateTimeFormat;
import org.springframework.web.bind.annotation.*;

import java.time.LocalDateTime;
import java.util.List;

@RestController
@RequiredArgsConstructor
@RequestMapping("/api/detections")
public class DetectionController {

    private final DetectionService service;

    @PostMapping
    public DetectionResponseDto uploadDetection(@RequestBody DetectionRequestDto dto) {
        return service.saveDetection(dto);
    }

    @GetMapping
    public List<DetectionResponseDto> getDetections(
            @RequestParam(required = false) @DateTimeFormat(iso = DateTimeFormat.ISO.DATE_TIME) LocalDateTime from,
            @RequestParam(required = false) @DateTimeFormat(iso = DateTimeFormat.ISO.DATE_TIME) LocalDateTime to
    ) {
        if (from != null && to != null) {
            return service.getDetectionsByTimeRange(from, to);
        }
        return service.getAllDetections();
    }

    @GetMapping("/{id}")
    public DetectionResponseDto getDetection(@PathVariable Long id) {
        return service.getDetection(id);
    }
}
