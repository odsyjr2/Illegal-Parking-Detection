package com.aivle.ParkingDetection.service;

import com.aivle.ParkingDetection.dto.ParkingZoneDTO;
import com.aivle.ParkingDetection.dto.ParkingZoneRequestDTO;
import com.aivle.ParkingDetection.dto.ParkingSectionRequestDTO;

import java.util.List;

public interface ParkingZoneService {
    List<ParkingZoneDTO> findAll();
    ParkingZoneDTO findOne(Long id);
    ParkingZoneDTO create(ParkingZoneRequestDTO req);
    ParkingZoneDTO update(Long id, ParkingZoneRequestDTO req);
    void delete(Long id);

    // 섹션 개별 CRUD (옵션)
    ParkingZoneDTO addSection(Long zoneId, ParkingSectionRequestDTO req);
    ParkingZoneDTO updateSection(Long zoneId, Long sectionId, ParkingSectionRequestDTO req);
    ParkingZoneDTO removeSection(Long zoneId, Long sectionId);
}
