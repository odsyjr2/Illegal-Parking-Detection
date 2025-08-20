package com.aivle.ParkingDetection.controller;

import com.aivle.ParkingDetection.dto.*;
import com.aivle.ParkingDetection.service.DetectionService;
import com.aivle.ParkingDetection.service.FileStorageService;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.core.io.FileSystemResource;
import org.springframework.core.io.Resource;
import org.springframework.format.annotation.DateTimeFormat;
import org.springframework.http.HttpHeaders;
import org.springframework.http.HttpStatus;
import org.springframework.http.MediaType;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.io.File;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.time.LocalDateTime;
import java.util.List;

@Slf4j
@RestController
@RequiredArgsConstructor
@RequestMapping("/api/detections")
public class DetectionController {

    private final DetectionService service;
    private final FileStorageService fileStorageService;

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

    // AI INTEGRATION - IMAGE SERVING ENDPOINTS
    
    /**
     * Serve violation image by detection ID
     * GET /api/detections/{id}/image
     */
    @GetMapping("/{id}/image")
    public ResponseEntity<Resource> getDetectionImage(@PathVariable Long id) {
        try {
            log.info("Retrieving image for detection ID: {}", id);
            
            // Get detection to extract image URL
            DetectionResponseDto detection = service.getDetection(id);
            if (detection.getImageUrl() == null || detection.getImageUrl().isEmpty()) {
                log.warn("No image URL found for detection ID: {}", id);
                return ResponseEntity.notFound().build();
            }
            
            // Get full file path
            String fullPath = fileStorageService.getFullImagePath(detection.getImageUrl());
            if (fullPath == null) {
                log.warn("Invalid image URL for detection ID {}: {}", id, detection.getImageUrl());
                return ResponseEntity.notFound().build();
            }
            
            // Check if file exists
            Path filePath = Paths.get(fullPath);
            if (!Files.exists(filePath)) {
                log.warn("Image file not found for detection ID {}: {}", id, fullPath);
                return ResponseEntity.notFound().build();
            }
            
            // Create file resource
            Resource resource = new FileSystemResource(filePath.toFile());
            
            // Determine content type
            String contentType = determineContentType(filePath.toString());
            
            // Set response headers
            HttpHeaders headers = new HttpHeaders();
            headers.setContentType(MediaType.parseMediaType(contentType));
            headers.setCacheControl("max-age=3600"); // Cache for 1 hour
            
            log.info("Serving image for detection ID {}: {}", id, filePath.getFileName());
            return ResponseEntity.ok()
                    .headers(headers)
                    .body(resource);
                    
        } catch (Exception e) {
            log.error("Error retrieving image for detection ID {}: {}", id, e.getMessage());
            return ResponseEntity.status(HttpStatus.INTERNAL_SERVER_ERROR).build();
        }
    }
    
    
    /**
     * Determine content type based on file extension
     */
    private String determineContentType(String filename) {
        String lowerFilename = filename.toLowerCase();
        if (lowerFilename.endsWith(".jpg") || lowerFilename.endsWith(".jpeg")) {
            return "image/jpeg";
        } else if (lowerFilename.endsWith(".png")) {
            return "image/png";
        } else if (lowerFilename.endsWith(".gif")) {
            return "image/gif";
        } else if (lowerFilename.endsWith(".bmp")) {
            return "image/bmp";
        } else {
            return "application/octet-stream";
        }
    }
    
    /**
     * Security check to ensure file path is within allowed directory
     */
    private boolean isFilePathSecure(String fullPath) {
        try {
            Path filePath = Paths.get(fullPath).toRealPath();
            Path basePath = Paths.get("./storage/images").toRealPath();
            return filePath.startsWith(basePath);
        } catch (Exception e) {
            log.error("Error checking file path security: {}", e.getMessage());
            return false;
        }
    }
}
