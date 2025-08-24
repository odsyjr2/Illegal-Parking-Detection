package com.aivle.ParkingDetection.controller;

import com.aivle.ParkingDetection.dto.ApiResponse;
import com.aivle.ParkingDetection.dto.PatrolRouteDTO;
import com.aivle.ParkingDetection.dto.PatrolRouteUpdateDTO;
import com.aivle.ParkingDetection.service.PatrolRouteService;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

@Slf4j
@RestController
@RequestMapping("/api/patrol-routes")
@RequiredArgsConstructor
public class PatrolRouteController {

    private final PatrolRouteService patrolRouteService;

    /**
     * AI에서 계산된 순찰 경로 업데이트
     * POST /api/patrol-routes/update
     */
    @PostMapping("/update")
    public ResponseEntity<ApiResponse<String>> updatePatrolRoutes(
            @RequestBody PatrolRouteUpdateDTO updateDTO) {
        
        try {
            log.info("🚗 AI로부터 순찰 경로 업데이트 요청 수신");
            log.debug("경로 데이터: {} 대 차량", updateDTO.getRoutes() != null ? updateDTO.getRoutes().size() : 0);
            
            boolean success = patrolRouteService.updatePatrolRoutes(updateDTO);
            
            if (success) {
                return ResponseEntity.ok(ApiResponse.success("순찰 경로 업데이트 완료"));
            } else {
                return ResponseEntity.badRequest()
                        .body(ApiResponse.error("순찰 경로 업데이트 실패"));
            }
            
        } catch (Exception e) {
            log.error("순찰 경로 업데이트 중 오류", e);
            return ResponseEntity.internalServerError()
                    .body(ApiResponse.error("서버 오류: " + e.getMessage()));
        }
    }

    /**
     * 현재 순찰 경로 조회 (프론트엔드용)
     * GET /api/patrol-routes
     */
    @GetMapping
    public ResponseEntity<ApiResponse<PatrolRouteDTO>> getCurrentPatrolRoutes() {
        
        try {
            log.info("📋 프론트엔드로부터 순찰 경로 조회 요청");
            
            PatrolRouteDTO routes = patrolRouteService.getCurrentPatrolRoutes();
            
            return ResponseEntity.ok(ApiResponse.success("순찰 경로 조회 성공", routes));
            
        } catch (Exception e) {
            log.error("순찰 경로 조회 중 오류", e);
            return ResponseEntity.internalServerError()
                    .body(ApiResponse.error("서버 오류: " + e.getMessage()));
        }
    }

    /**
     * 순찰 경로 초기화 (관리자용)
     * DELETE /api/patrol-routes
     */
    @DeleteMapping
    public ResponseEntity<ApiResponse<String>> clearPatrolRoutes() {
        
        try {
            log.info("🗑️ 순찰 경로 초기화 요청");
            
            patrolRouteService.clearPatrolRoutes();
            
            return ResponseEntity.ok(ApiResponse.success("순찰 경로 초기화 완료"));
            
        } catch (Exception e) {
            log.error("순찰 경로 초기화 중 오류", e);
            return ResponseEntity.internalServerError()
                    .body(ApiResponse.error("서버 오류: " + e.getMessage()));
        }
    }
}
