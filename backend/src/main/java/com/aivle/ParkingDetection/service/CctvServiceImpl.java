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
                .streamUrl(dto.getStreamUrl() != null ? dto.getStreamUrl() : dto.getIpAddress())  // Map ipAddress to streamUrl for backward compatibility
                .streamName(dto.getStreamName() != null ? dto.getStreamName() : dto.getDescription())  // Map description to streamName
                .streamSource("manual")  // Manual CCTVs are marked as manual source
                .active(dto.isActive())
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
        cctv.setStreamUrl(dto.getIpAddress());  // Map ipAddress to streamUrl for backward compatibility
        cctv.setStreamName(dto.getDescription());  // Map description to streamName
        cctv.setActive(dto.isActive());
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
                // Legacy fields for backward compatibility
                .ipAddress(cctv.getIpAddress())  // Returns streamUrl via @Transient method
                .description(cctv.getDescription())  // Returns streamName via @Transient method
                // Stream fields
                .streamUrl(cctv.getStreamUrl())
                .streamId(cctv.getStreamId())
                .streamName(cctv.getStreamName())
                .streamSource(cctv.getStreamSource())
                .active(cctv.isActive())
                .latitude(cctv.getLatitude())
                .longitude(cctv.getLongitude())
                .installationDate(cctv.getInstallationDate())
                .lastUpdated(cctv.getLastUpdated())
                .build();
    }

    @Override
    public List<CctvDTO> findNearestCctvs(Double latitude, Double longitude, Double radius) {
        // 임시로 전체 반환 (차후 거리 계산 로직이 필요)
        return cctvRepository.findAll().stream()
                .map(this::toDTO)
                .collect(Collectors.toList());
    }

    // Stream sync methods for AI integration
    @Override
    public void syncStreamsFromAI(List<StreamSyncDto> streams) {
        for (StreamSyncDto streamDto : streams) {
            // Check if stream already exists
            if (cctvRepository.existsByStreamId(streamDto.getStreamId())) {
                // Update existing stream
                Cctv existingCctv = cctvRepository.findByStreamId(streamDto.getStreamId())
                        .orElseThrow(() -> new RuntimeException("Stream not found: " + streamDto.getStreamId()));
                
                existingCctv.setStreamUrl(streamDto.getStreamUrl());
                existingCctv.setStreamName(streamDto.getStreamName());
                existingCctv.setLocation(streamDto.getLocation());
                existingCctv.setLatitude(streamDto.getLatitude());
                existingCctv.setLongitude(streamDto.getLongitude());
                existingCctv.setActive(streamDto.isActive());
                existingCctv.setLastUpdated(streamDto.getDiscoveredAt());
                
                cctvRepository.save(existingCctv);
            } else {
                // Create new stream entry
                Cctv newCctv = Cctv.builder()
                        .streamId(streamDto.getStreamId())
                        .streamName(streamDto.getStreamName())
                        .streamUrl(streamDto.getStreamUrl())
                        .streamSource(streamDto.getStreamSource())
                        .location(streamDto.getLocation())
                        .latitude(streamDto.getLatitude())
                        .longitude(streamDto.getLongitude())
                        .active(streamDto.isActive())
                        .lastUpdated(streamDto.getDiscoveredAt())
                        .build();
                
                cctvRepository.save(newCctv);
            }
        }
    }

    @Override
    public CctvDTO getStreamByStreamId(String streamId) {
        return cctvRepository.findByStreamId(streamId)
                .map(this::toDTO)
                .orElseThrow(() -> new RuntimeException("Stream not found with streamId: " + streamId));
    }

    @Override
    public List<CctvDTO> getActiveStreams() {
        return cctvRepository.findActiveStreams().stream()
                .map(this::toDTO)
                .collect(Collectors.toList());
    }

    @Override
    public List<CctvDTO> getStreamsBySource(String source) {
        return cctvRepository.findByStreamSource(source).stream()
                .map(this::toDTO)
                .collect(Collectors.toList());
    }
}
