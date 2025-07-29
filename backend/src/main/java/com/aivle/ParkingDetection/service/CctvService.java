package com.aivle.ParkingDetection.service;

import com.aivle.ParkingDetection.dto.*;

import java.util.List;

public interface CctvService {
    CctvDTO createCctv(CctvCreateRequestDTO dto);
    CctvDTO updateCctv(Long id, CctvUpdateRequestDTO dto);
    void deleteCctv(Long id);
    CctvDTO getCctv(Long id);
    List<CctvDTO> getAllCctvs();
}
