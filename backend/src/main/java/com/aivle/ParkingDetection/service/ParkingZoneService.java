package com.aivle.ParkingDetection.service;

import com.aivle.ParkingDetection.dto.ParkingZoneDTO;
import com.aivle.ParkingDetection.dto.ParkingZoneRequestDTO;
import com.aivle.ParkingDetection.dto.ParkingSectionRequestDTO;

import java.time.LocalDateTime;
import java.util.List;

public interface ParkingZoneService {
    // ORIGINAL METHODS - PRESERVED FOR BACKWARD COMPATIBILITY
    List<ParkingZoneDTO> findAll();
    ParkingZoneDTO findOne(Long id);
    ParkingZoneDTO create(ParkingZoneRequestDTO req);
    ParkingZoneDTO update(Long id, ParkingZoneRequestDTO req);
    void delete(Long id);

    // 섹션 개별 CRUD (옵션)
    ParkingZoneDTO addSection(Long zoneId, ParkingSectionRequestDTO req);
    ParkingZoneDTO updateSection(Long zoneId, Long sectionId, ParkingSectionRequestDTO req);
    ParkingZoneDTO removeSection(Long zoneId, Long sectionId);
    
    // AI INTEGRATION - NEW METHODS FOR VIOLATION VALIDATION
    /**
     * Check if parking is legally allowed at specific CCTV location and time
     * @param cctvId CCTV stream identifier
     * @param detectionTime Time of detection
     * @return true if parking is legally allowed, false if violation
     */
    boolean isLegalParkingAllowed(String cctvId, LocalDateTime detectionTime);
    
    /**
     * Get parking zone information by geographic coordinates
     * @param latitude GPS latitude
     * @param longitude GPS longitude
     * @return ParkingZoneDTO if found, null otherwise
     */
    ParkingZoneDTO findParkingZoneByCoordinates(Double latitude, Double longitude);
    
    /**
     * Validate if AI-detected violation should be confirmed based on parking rules
     * @param cctvId CCTV stream identifier
     * @param detectionTime Time of detection
     * @param latitude GPS latitude (optional)
     * @param longitude GPS longitude (optional)
     * @return true if violation should be confirmed, false otherwise
     */
    boolean validateViolationByRules(String cctvId, LocalDateTime detectionTime, 
                                   Double latitude, Double longitude);
}
