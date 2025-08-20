package com.aivle.ParkingDetection.controller;

import com.aivle.ParkingDetection.service.FileStorageService;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.core.io.FileSystemResource;
import org.springframework.core.io.Resource;
import org.springframework.http.HttpHeaders;
import org.springframework.http.HttpStatus;
import org.springframework.http.MediaType;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;

/**
 * Controller for serving stored violation images from AI processor
 * Handles image delivery for frontend consumption after AI detection processing
 */
@Slf4j
@RestController
@RequiredArgsConstructor
@RequestMapping("/api/images")
public class ImageController {

    private final FileStorageService fileStorageService;

    /**
     * Serve violation image directly by image path
     * GET /api/images/{streamId}/{date}/{filename}
     * 
     * This endpoint serves images stored by the AI processor in the format:
     * /api/images/{streamId}/{date}/{timestamp}_{eventId}.{extension}
     * 
     * @param streamId CCTV stream identifier (e.g., "cctv_001")
     * @param date Date folder in YYYY-MM-DD format (e.g., "2023-12-29")
     * @param filename Image filename with timestamp and event ID
     * @return ResponseEntity with image resource or error status
     */
    @GetMapping("/{streamId}/{date}/{filename:.+}")
    public ResponseEntity<Resource> getImageByPath(
            @PathVariable String streamId,
            @PathVariable String date,
            @PathVariable String filename) {
        try {
            log.info("Retrieving image: streamId={}, date={}, filename={}", streamId, date, filename);
            
            // Construct image URL path as expected by FileStorageService
            String imageUrl = String.format("/api/images/%s/%s/%s", streamId, date, filename);
            
            // Get full file path
            String fullPath = fileStorageService.getFullImagePath(imageUrl);
            if (fullPath == null) {
                log.warn("Invalid image path: {}", imageUrl);
                return ResponseEntity.notFound().build();
            }
            
            // Check if file exists
            Path filePath = Paths.get(fullPath);
            if (!Files.exists(filePath)) {
                log.warn("Image file not found: {}", fullPath);
                return ResponseEntity.notFound().build();
            }
            
            // Validate file is within allowed directory (security check)
            if (!isFilePathSecure(fullPath)) {
                log.warn("Security violation: Attempt to access file outside allowed directory: {}", fullPath);
                return ResponseEntity.status(HttpStatus.FORBIDDEN).build();
            }
            
            // Create file resource
            Resource resource = new FileSystemResource(filePath.toFile());
            
            // Determine content type
            String contentType = determineContentType(filename);
            
            // Set response headers with UTF-8 support for Korean filenames
            HttpHeaders headers = new HttpHeaders();
            headers.setContentType(MediaType.parseMediaType(contentType));
            headers.setCacheControl("max-age=3600"); // Cache for 1 hour
            
            // Handle Korean filename encoding properly
            try {
                String encodedFilename = java.net.URLEncoder.encode(filename, "UTF-8")
                        .replaceAll("\\+", "%20");
                headers.add(HttpHeaders.CONTENT_DISPOSITION, 
                        "inline; filename*=UTF-8''" + encodedFilename);
            } catch (Exception e) {
                // Fallback to simple filename
                headers.add(HttpHeaders.CONTENT_DISPOSITION, "inline; filename=\"" + filename + "\"");
            }
            
            log.info("Serving image file: {}", filePath.getFileName());
            return ResponseEntity.ok()
                    .headers(headers)
                    .body(resource);
                    
        } catch (Exception e) {
            log.error("Error retrieving image file streamId={}, date={}, filename={}: {}", 
                    streamId, date, filename, e.getMessage());
            return ResponseEntity.status(HttpStatus.INTERNAL_SERVER_ERROR).build();
        }
    }
    
    /**
     * Health check endpoint for image service
     * GET /api/images/health
     */
    @GetMapping("/health")
    public ResponseEntity<String> healthCheck() {
        return ResponseEntity.ok("Image Service is running");
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
     * Prevents directory traversal attacks by validating the resolved path
     */
    private boolean isFilePathSecure(String fullPath) {
        try {
            // Resolve and normalize the file path
            Path filePath = Paths.get(fullPath).normalize().toAbsolutePath();
            
            // Resolve and normalize the base path
            Path basePath = Paths.get("./storage/images").normalize().toAbsolutePath();
            
            // Check if file exists first (toRealPath requires file existence)
            if (!Files.exists(filePath)) {
                log.warn("File does not exist: {}", filePath);
                return false;
            }
            
            // Get real path and check if it starts with base path
            Path realFilePath = filePath.toRealPath();
            Path realBasePath = basePath.toRealPath();
            
            boolean isSecure = realFilePath.startsWith(realBasePath);
            
            if (!isSecure) {
                log.warn("Security violation: File path {} is outside allowed directory {}", 
                        realFilePath, realBasePath);
            }
            
            return isSecure;
            
        } catch (Exception e) {
            log.error("Error checking file path security for {}: {}", fullPath, e.getMessage());
            return false;
        }
    }
}