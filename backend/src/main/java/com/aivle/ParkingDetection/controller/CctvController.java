package com.aivle.ParkingDetection.controller;

import com.aivle.ParkingDetection.dto.*;
import com.aivle.ParkingDetection.service.CctvService;
import lombok.RequiredArgsConstructor;
import org.springframework.web.bind.annotation.*;
import org.springframework.http.ResponseEntity;


import java.util.List;
import java.util.Map;

@RestController
@RequestMapping("/api/cctvs")
@RequiredArgsConstructor
public class CctvController {

    private final CctvService cctvService;

    // CCTV 생성
    @PostMapping
    public CctvDTO create(@RequestBody CctvCreateRequestDTO dto) {
        return cctvService.createCctv(dto);
    }

    // CCTV 정보 수정
    @PutMapping("/{id}")
    public CctvDTO update(@PathVariable Long id, @RequestBody CctvUpdateRequestDTO dto) {
        return cctvService.updateCctv(id, dto);
    }

    // 단일 CCTV 조회 (설치일 포함)
    @GetMapping("/{id}")
    public CctvDTO getOne(@PathVariable Long id) {
        return cctvService.getCctv(id);  // Service에서 installedAt 포함 DTO로 반환
    }

    // 전체 CCTV 목록 조회 (설치일 포함)
    @GetMapping
    public List<CctvDTO> getAll() {
        return cctvService.getAllCctvs();  // Service에서 설치일 포함 리스트 반환
    }

    // CCTV 삭제
    @DeleteMapping("/{id}")
    public ResponseEntity<?> delete(@PathVariable Long id) {
        cctvService.deleteCctv(id);
        return ResponseEntity.ok().body(Map.of("message", "삭제 완료"));
    }

    // Stream sync endpoint for AI integration
    @PostMapping("/sync")
    public ResponseEntity<?> syncStreams(@RequestBody List<StreamSyncDto> streams) {
        try {
            cctvService.syncStreamsFromAI(streams);
            return ResponseEntity.ok().body(Map.of(
                "message", "Stream sync completed successfully",
                "syncedCount", streams.size()
            ));
        } catch (Exception e) {
            return ResponseEntity.badRequest().body(Map.of(
                "error", "Stream sync failed: " + e.getMessage()
            ));
        }
    }

    // Get stream by streamId (for AI and frontend use)
    @GetMapping("/stream/{streamId}")
    public CctvDTO getStreamByStreamId(@PathVariable String streamId) {
        return cctvService.getStreamByStreamId(streamId);
    }

    // Get active streams only (for frontend stream selection)
    @GetMapping("/active")
    public List<CctvDTO> getActiveStreams() {
        return cctvService.getActiveStreams();
    }

    // Get streams by source type (e.g., "korean_its_api")
    @GetMapping("/source/{source}")
    public List<CctvDTO> getStreamsBySource(@PathVariable String source) {
        return cctvService.getStreamsBySource(source);
    }
}