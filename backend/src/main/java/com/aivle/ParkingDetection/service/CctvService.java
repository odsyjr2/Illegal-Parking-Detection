package com.aivle.ParkingDetection.service;

import com.aivle.ParkingDetection.dto.*;

import java.util.List;

public interface CctvService {
    // Legacy CCTV management methods
    CctvDTO createCctv(CctvCreateRequestDTO dto);
    CctvDTO updateCctv(Long id, CctvUpdateRequestDTO dto);
    void deleteCctv(Long id);
    CctvDTO getCctv(Long id);
    List<CctvDTO> getAllCctvs();
    List<CctvDTO> findNearestCctvs(Double latitude, Double longitude, Double distance);

    // Stream sync methods for AI integration
    void syncStreamsFromAI(List<StreamSyncDto> streams);
    CctvDTO getStreamByStreamId(String streamId);
    List<CctvDTO> getActiveStreams();
    List<CctvDTO> getStreamsBySource(String source);
}