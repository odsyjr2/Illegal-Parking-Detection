package com.aivle.ParkingDetection.service;

import com.aivle.ParkingDetection.dto.ParkingZoneDTO;
import com.aivle.ParkingDetection.dto.ParkingZoneRequestDTO;

import java.util.List;

public interface ParkingZoneService {
    List<ParkingZoneDTO> listAll();
    ParkingZoneDTO getById(Long id);
    ParkingZoneDTO create(ParkingZoneRequestDTO req);
    ParkingZoneDTO update(Long id, ParkingZoneRequestDTO req);
    void delete(Long id);
}
