package com.aivle.ParkingDetection.service;

/**
 * File Storage Service Interface
 * Handles Base64 image storage from AI processor
 */
public interface FileStorageService {
    
    /**
     * Store Base64 encoded image from AI processor
     * 
     * @param base64Image Base64 encoded image data
     * @param eventId AI event ID for file naming
     * @param streamId CCTV stream ID
     * @return URL path to stored image file
     */
    String storeBase64Image(String base64Image, String eventId, String streamId);
    
    /**
     * Store image bytes
     * 
     * @param imageBytes Raw image bytes
     * @param eventId AI event ID for file naming
     * @param streamId CCTV stream ID
     * @param fileExtension Image file extension (jpg, png, etc.)
     * @return URL path to stored image file
     */
    String storeImageBytes(byte[] imageBytes, String eventId, String streamId, String fileExtension);
    
    /**
     * Get full file path for stored image
     * 
     * @param imageUrl Stored image URL
     * @return Full file system path
     */
    String getFullImagePath(String imageUrl);
    
    /**
     * Delete stored image file
     * 
     * @param imageUrl Stored image URL
     * @return true if deletion successful
     */
    boolean deleteImage(String imageUrl);
    
    /**
     * Clean up old image files based on retention policy
     * 
     * @param retentionDays Number of days to retain files
     * @return Number of files cleaned up
     */
    int cleanupOldImages(int retentionDays);
}