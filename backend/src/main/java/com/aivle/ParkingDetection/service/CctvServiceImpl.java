package com.aivle.ParkingDetection.service;

import com.aivle.ParkingDetection.domain.Cctv;
import com.aivle.ParkingDetection.dto.*;
import com.aivle.ParkingDetection.repository.CctvRepository;
import lombok.RequiredArgsConstructor;
import org.springframework.stereotype.Service;

import java.util.List;
import java.util.stream.Collectors;

@Service
@RequiredArgsConstructor
public class CctvServiceImpl implements CctvService {

    private final CctvRepository cctvRepository;

    @Override
    public CctvDTO createCctv(CctvCreateRequestDTO dto) {
        Cctv cctv = Cctv.builder()
                .location(dto.getLocation())
                .ipAddress(dto.getIpAddress())
                .active(dto.isActive())
                .description(dto.getDescription())
                .latitude(dto.getLatitude())
                .longitude(dto.getLongitude())
                .installationDate(dto.getInstallationDate())
                .build();
        Cctv saved = cctvRepository.save(cctv);
        return toDTO(saved);
    }

    @Override
    public CctvDTO updateCctv(Long id, CctvUpdateRequestDTO dto) {
        Cctv cctv = cctvRepository.findById(id)
                .orElseThrow(() -> new RuntimeException("CCTV not found"));
        cctv.setLocation(dto.getLocation());
        cctv.setIpAddress(dto.getIpAddress());
        cctv.setActive(dto.isActive());
        cctv.setDescription(dto.getDescription());
        cctv.setLatitude(dto.getLatitude());
        cctv.setLongitude(dto.getLongitude());
        cctv.setInstallationDate(dto.getInstallationDate());
        return toDTO(cctvRepository.save(cctv));
    }

    @Override
    public void deleteCctv(Long id) {
        cctvRepository.deleteById(id);
    }

    @Override
    public CctvDTO getCctv(Long id) {
        return cctvRepository.findById(id)
                .map(this::toDTO)
                .orElseThrow(() -> new RuntimeException("CCTV not found"));
    }

    @Override
    public List<CctvDTO> getAllCctvs() {
        return cctvRepository.findAll().stream()
                .map(this::toDTO)
                .collect(Collectors.toList());
    }

    private CctvDTO toDTO(Cctv cctv) {
        return CctvDTO.builder()
                .id(cctv.getId())
                .location(cctv.getLocation())
                .ipAddress(cctv.getIpAddress())
                .active(cctv.isActive())
                .description(cctv.getDescription())
                .latitude(cctv.getLatitude())
                .longitude(cctv.getLongitude())
                .installationDate(cctv.getInstallationDate())
                .build();
    }
    @Override
    public List<CctvDTO> findNearestCctvs(Double latitude, Double longitude, Double radius) {
        // 임시로 전체 반환 (차후 거리 계산 로직 필요)
        return cctvRepository.findAll().stream()
                .map(this::toDTO)
                .collect(Collectors.toList());
}
    
}
