package com.aivle.ParkingDetection.service;

import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Service;

import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.nio.file.StandardOpenOption;
import java.time.LocalDateTime;
import java.time.format.DateTimeFormatter;
import java.util.Base64;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

@Slf4j
@Service
public class FileStorageServiceImpl implements FileStorageService {

    @Value("${app.file-storage.base-path:./storage/images}")
    private String baseStoragePath;
    
    @Value("${app.file-storage.url-prefix:/api/images}")
    private String urlPrefix;
    
    private static final Pattern BASE64_PATTERN = Pattern.compile("data:image/(\\w+);base64,(.+)");
    
    @Override
    public String storeBase64Image(String base64Image, String eventId, String streamId) {
        try {
            // Parse Base64 image data
            Matcher matcher = BASE64_PATTERN.matcher(base64Image);
            String fileExtension = "jpg"; // Default
            String base64Data = base64Image;
            
            if (matcher.matches()) {
                fileExtension = matcher.group(1);
                base64Data = matcher.group(2);
            } else if (base64Image.startsWith("data:")) {
                throw new IllegalArgumentException("Invalid Base64 image format");
            }
            
            // Decode Base64 data
            byte[] imageBytes = Base64.getDecoder().decode(base64Data);
            
            return storeImageBytes(imageBytes, eventId, streamId, fileExtension);
            
        } catch (IllegalArgumentException e) {
            log.error("Error decoding Base64 image for event {}: {}", eventId, e.getMessage());
            throw new RuntimeException("Failed to decode Base64 image", e);
        }
    }

    @Override
    public String storeImageBytes(byte[] imageBytes, String eventId, String streamId, String fileExtension) {
        try {
            // Create directory structure: {baseStoragePath}/{streamId}/{date}/
            LocalDateTime now = LocalDateTime.now();
            String dateFolder = now.format(DateTimeFormatter.ofPattern("yyyy-MM-dd"));
            
            Path directoryPath = Paths.get(baseStoragePath, streamId, dateFolder);
            Files.createDirectories(directoryPath);
            
            // Generate filename: {timestamp}_{eventId}.{extension}
            String timestamp = now.format(DateTimeFormatter.ofPattern("HHmmss"));
            String filename = String.format("%s_%s.%s", timestamp, sanitizeEventId(eventId), fileExtension);
            
            Path filePath = directoryPath.resolve(filename);
            
            // Write image bytes to file
            Files.write(filePath, imageBytes, StandardOpenOption.CREATE, StandardOpenOption.WRITE);
            
            // Generate URL path
            String urlPath = String.format("%s/%s/%s/%s", urlPrefix, streamId, dateFolder, filename);
            
            log.info("Stored image file: {} for event: {}", filePath, eventId);
            return urlPath;
            
        } catch (IOException e) {
            log.error("Error storing image for event {}: {}", eventId, e.getMessage());
            throw new RuntimeException("Failed to store image file", e);
        }
    }

    @Override
    public String getFullImagePath(String imageUrl) {
        if (imageUrl == null || !imageUrl.startsWith(urlPrefix)) {
            return null;
        }
        
        // Convert URL path to file system path
        String relativePath = imageUrl.substring(urlPrefix.length());
        if (relativePath.startsWith("/")) {
            relativePath = relativePath.substring(1);
        }
        
        return Paths.get(baseStoragePath, relativePath).toString();
    }

    @Override
    public boolean deleteImage(String imageUrl) {
        try {
            String fullPath = getFullImagePath(imageUrl);
            if (fullPath == null) {
                log.warn("Invalid image URL for deletion: {}", imageUrl);
                return false;
            }
            
            Path filePath = Paths.get(fullPath);
            if (Files.exists(filePath)) {
                Files.delete(filePath);
                log.info("Deleted image file: {}", fullPath);
                return true;
            } else {
                log.warn("Image file not found for deletion: {}", fullPath);
                return false;
            }
            
        } catch (IOException e) {
            log.error("Error deleting image {}: {}", imageUrl, e.getMessage());
            return false;
        }
    }

    @Override
    public int cleanupOldImages(int retentionDays) {
        // TODO: Implement cleanup logic for old image files
        // This would involve:
        // 1. Walking through the storage directory structure
        // 2. Checking file modification dates
        // 3. Deleting files older than retention period
        // 4. Removing empty directories
        
        log.info("Image cleanup requested for retention period: {} days", retentionDays);
        return 0; // Placeholder
    }
    
    /**
     * Sanitize event ID for safe filename usage
     */
    private String sanitizeEventId(String eventId) {
        if (eventId == null) {
            return "unknown";
        }
        
        // Replace problematic characters with underscores
        return eventId.replaceAll("[^a-zA-Z0-9_-]", "_");
    }
}