package com.aivle.ParkingDetection.dto;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

/**
 * VWorld API 지오코딩 결과를 담는 DTO
 * 
 * 지오코딩(주소→좌표)과 역지오코딩(좌표→주소) 결과를 모두 처리할 수 있는 통합 DTO입니다.
 */
@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class GeocodingResult {
    
    /**
     * 지오코딩 성공 여부
     */
    private boolean success;
    
    /**
     * GPS 위도 좌표
     */
    private Double latitude;
    
    /**
     * GPS 경도 좌표
     */
    private Double longitude;
    
    /**
     * 도로명 주소 (VWorld API에서 정제된 주소)
     */
    private String roadAddress;
    
    /**
     * 원본 입력 주소 (지오코딩 요청시)
     */
    private String originalAddress;
    
    /**
     * 오류 메시지 (실패시)
     */
    private String errorMessage;
    
    /**
     * 지오코딩 소요 시간 (밀리초)
     */
    private Long processingTimeMs;
    
    /**
     * VWorld API 응답 상태
     */
    private String apiStatus;

    /**
     * 지오코딩 성공 결과 생성
     * 
     * @param latitude 위도
     * @param longitude 경도
     * @param roadAddress 도로명 주소
     * @return 성공 결과
     */
    public static GeocodingResult success(Double latitude, Double longitude, String roadAddress) {
        return GeocodingResult.builder()
                .success(true)
                .latitude(latitude)
                .longitude(longitude)
                .roadAddress(roadAddress)
                .build();
    }

    /**
     * 지오코딩 성공 결과 생성 (원본 주소 포함)
     * 
     * @param latitude 위도
     * @param longitude 경도
     * @param roadAddress 정제된 도로명 주소
     * @param originalAddress 원본 입력 주소
     * @return 성공 결과
     */
    public static GeocodingResult success(Double latitude, Double longitude, String roadAddress, String originalAddress) {
        return GeocodingResult.builder()
                .success(true)
                .latitude(latitude)
                .longitude(longitude)
                .roadAddress(roadAddress)
                .originalAddress(originalAddress)
                .build();
    }

    /**
     * 지오코딩 실패 결과 생성
     * 
     * @param errorMessage 오류 메시지
     * @return 실패 결과
     */
    public static GeocodingResult failure(String errorMessage) {
        return GeocodingResult.builder()
                .success(false)
                .errorMessage(errorMessage)
                .build();
    }

    /**
     * 지오코딩 실패 결과 생성 (원본 주소 포함)
     * 
     * @param errorMessage 오류 메시지
     * @param originalAddress 원본 입력 주소
     * @return 실패 결과
     */
    public static GeocodingResult failure(String errorMessage, String originalAddress) {
        return GeocodingResult.builder()
                .success(false)
                .errorMessage(errorMessage)
                .originalAddress(originalAddress)
                .build();
    }

    /**
     * GPS 좌표가 유효한지 확인
     * 
     * @return 좌표 유효성
     */
    public boolean hasValidCoordinates() {
        return success && latitude != null && longitude != null && 
               latitude >= -90 && latitude <= 90 && 
               longitude >= -180 && longitude <= 180;
    }

    /**
     * 도로명 주소가 유효한지 확인
     * 
     * @return 주소 유효성
     */
    public boolean hasValidAddress() {
        return success && roadAddress != null && !roadAddress.trim().isEmpty();
    }

    /**
     * 한국 영토 내 좌표인지 확인 (대략적 범위)
     * 
     * @return 한국 영토 내 여부
     */
    public boolean isWithinKorea() {
        if (!hasValidCoordinates()) {
            return false;
        }
        
        // 한국 대략적 범위: 33-39N, 124-132E
        return latitude >= 32.0 && latitude <= 40.0 && 
               longitude >= 123.0 && longitude <= 133.0;
    }

    /**
     * 도로명 주소 형식인지 확인
     * 
     * @return 도로명 주소 여부
     */
    public boolean isRoadAddress() {
        if (!hasValidAddress()) {
            return false;
        }
        
        // 도로명 주소 지시자 확인
        String[] roadIndicators = {"로", "길", "대로"};
        for (String indicator : roadIndicators) {
            if (roadAddress.contains(indicator)) {
                return true;
            }
        }
        
        return false;
    }

    /**
     * 결과 요약 문자열 반환
     * 
     * @return 결과 요약
     */
    public String getSummary() {
        if (success) {
            if (hasValidCoordinates() && hasValidAddress()) {
                return String.format("성공: %s ↔ (%.6f, %.6f)", roadAddress, latitude, longitude);
            } else if (hasValidCoordinates()) {
                return String.format("성공: (%.6f, %.6f)", latitude, longitude);
            } else if (hasValidAddress()) {
                return String.format("성공: %s", roadAddress);
            } else {
                return "성공: 데이터 없음";
            }
        } else {
            return String.format("실패: %s", errorMessage != null ? errorMessage : "알 수 없는 오류");
        }
    }
}