package com.aivle.ParkingDetection.service;

import com.aivle.ParkingDetection.dto.GeocodingResult;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.cache.annotation.Cacheable;
import org.springframework.http.ResponseEntity;
import org.springframework.stereotype.Service;
import org.springframework.web.client.RestTemplate;
import org.springframework.web.client.ResourceAccessException;
import org.springframework.web.client.HttpClientErrorException;
import org.springframework.web.util.UriComponentsBuilder;
import org.springframework.boot.web.client.RestTemplateBuilder;

import java.time.Duration;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;

import jakarta.annotation.PostConstruct;
import java.net.URI;
import java.util.concurrent.TimeUnit;

/**
 * VWorld Open API 기반 지오코딩 서비스
 * 
 * 국토교통부 VWorld Open API를 사용하여 한국 도로명 주소와 GPS 좌표 간 변환을 제공합니다.
 * - 지오코딩: 도로명 주소 → GPS 좌표
 * - 역지오코딩: GPS 좌표 → 도로명 주소 (AI에서 담당)
 * - 캐싱을 통한 성능 최적화
 * - 재시도 및 에러 처리
 */
@Service
@Slf4j
public class VWorldGeocodingService {

    private static final String VWORLD_BASE_URL = "https://api.vworld.kr/req/address";
    private static final String GEOCODING_REQUEST = "getcoord";
    private static final String REVERSE_GEOCODING_REQUEST = "getAddress";
    private static final String VERSION = "2.0";
    private static final String FORMAT = "json";
    private static final String ADDRESS_TYPE = "ROAD"; // 도로명 주소만 처리
    private static final String COORDINATE_SYSTEM = "epsg:4326"; // WGS84

    @Value("${vworld.api.key:}")
    private String apiKey;

    @Value("${vworld.api.timeout:5000}")
    private int timeoutMs;

    @Value("${vworld.api.max-retries:3}")
    private int maxRetries;

    private final RestTemplate restTemplate;
    private final ObjectMapper objectMapper;

    public VWorldGeocodingService(RestTemplateBuilder restTemplateBuilder) {
        this.restTemplate = restTemplateBuilder.build();
        this.objectMapper = new ObjectMapper();
    }

    @PostConstruct
    private void validateConfiguration() {
        if (apiKey == null || apiKey.trim().isEmpty()) {
            log.warn("VWorld API key not configured. Geocoding service will be disabled.");
        } else {
            log.info("VWorld geocoding service initialized with API key");
            // Test API connectivity
            testApiConnectivity();
        }
    }

    /**
     * API 연결 상태 테스트 (서울시청 좌표 사용)
     */
    private void testApiConnectivity() {
        try {
            GeocodingResult testResult = reverseGeocode(37.566535, 126.977969);
            if (testResult.isSuccess()) {
                log.info("VWorld API connectivity test successful");
            } else {
                log.warn("VWorld API connectivity test failed: {}", testResult.getErrorMessage());
            }
        } catch (Exception e) {
            log.warn("VWorld API connectivity test error: {}", e.getMessage());
        }
    }

    /**
     * 도로명 주소를 GPS 좌표로 변환 (지오코딩)
     * 
     * @param roadAddress 한국 도로명 주소
     * @return GeocodingResult GPS 좌표 및 정제된 주소 정보
     */
    @Cacheable(value = "geocoding", key = "#roadAddress", unless = "#result == null or !#result.success")
    public GeocodingResult geocode(String roadAddress) {
        if (roadAddress == null || roadAddress.trim().isEmpty()) {
            return GeocodingResult.failure("주소가 비어있습니다");
        }

        if (!isServiceAvailable()) {
            return GeocodingResult.failure("VWorld API 키가 설정되지 않았습니다");
        }

        // 재시도 로직
        Exception lastException = null;
        for (int attempt = 0; attempt <= maxRetries; attempt++) {
            try {
                log.debug("VWorld 지오코딩 시도 {}/{}: {}", attempt + 1, maxRetries + 1, roadAddress);
                
                GeocodingResult result = performGeocodingRequest(roadAddress);
                if (result.isSuccess()) {
                    log.debug("지오코딩 성공: {} → ({}, {})", 
                            roadAddress, result.getLatitude(), result.getLongitude());
                    return result;
                }
                
                lastException = new RuntimeException(result.getErrorMessage());
                
                // 재시도 전 대기 (지수 백오프)
                if (attempt < maxRetries) {
                    Thread.sleep(1000 * (attempt + 1));
                }
                
            } catch (Exception e) {
                lastException = e;
                log.warn("지오코딩 시도 실패 ({}/{}): {}", attempt + 1, maxRetries + 1, e.getMessage());
                
                if (attempt < maxRetries) {
                    try {
                        Thread.sleep(1000 * (attempt + 1));
                    } catch (InterruptedException ie) {
                        Thread.currentThread().interrupt();
                        break;
                    }
                }
            }
        }

        String errorMessage = lastException != null ? lastException.getMessage() : "알 수 없는 오류";
        return GeocodingResult.failure("지오코딩 실패 (재시도 완료): " + errorMessage);
    }

    /**
     * GPS 좌표를 도로명 주소로 변환 (역지오코딩)
     * 주로 테스트 목적으로 사용 - 실제로는 AI 시스템에서 처리
     * 
     * @param latitude 위도
     * @param longitude 경도
     * @return GeocodingResult 도로명 주소 정보
     */
    @Cacheable(value = "reverseGeocoding", key = "#latitude + ',' + #longitude", unless = "#result == null or !#result.success")
    public GeocodingResult reverseGeocode(double latitude, double longitude) {
        if (!isValidCoordinates(latitude, longitude)) {
            return GeocodingResult.failure("유효하지 않은 좌표입니다");
        }

        if (!isServiceAvailable()) {
            return GeocodingResult.failure("VWorld API 키가 설정되지 않았습니다");
        }

        try {
            return performReverseGeocodingRequest(latitude, longitude);
        } catch (Exception e) {
            log.error("역지오코딩 오류: lat={}, lon={}, error={}", latitude, longitude, e.getMessage());
            return GeocodingResult.failure("역지오코딩 실패: " + e.getMessage());
        }
    }

    /**
     * 실제 지오코딩 API 요청 수행
     */
    private GeocodingResult performGeocodingRequest(String roadAddress) {
        try {
            URI uri = UriComponentsBuilder.fromHttpUrl(VWORLD_BASE_URL)
                    .queryParam("service", "address")
                    .queryParam("request", GEOCODING_REQUEST)
                    .queryParam("version", VERSION)
                    .queryParam("crs", COORDINATE_SYSTEM)
                    .queryParam("address", roadAddress)
                    .queryParam("format", FORMAT)
                    .queryParam("type", ADDRESS_TYPE)
                    .queryParam("key", apiKey)
                    .build()
                    .toUri();

            ResponseEntity<String> response = restTemplate.getForEntity(uri, String.class);
            
            if (!response.getStatusCode().is2xxSuccessful()) {
                return GeocodingResult.failure("HTTP 오류: " + response.getStatusCode());
            }

            return parseGeocodingResponse(response.getBody(), roadAddress);

        } catch (HttpClientErrorException e) {
            return GeocodingResult.failure("HTTP 클라이언트 오류: " + e.getMessage());
        } catch (ResourceAccessException e) {
            return GeocodingResult.failure("네트워크 연결 오류: " + e.getMessage());
        } catch (Exception e) {
            return GeocodingResult.failure("지오코딩 요청 실패: " + e.getMessage());
        }
    }

    /**
     * 실제 역지오코딩 API 요청 수행
     */
    private GeocodingResult performReverseGeocodingRequest(double latitude, double longitude) {
        try {
            String point = longitude + "," + latitude; // VWorld API는 x,y 순서 (경도,위도)
            
            URI uri = UriComponentsBuilder.fromHttpUrl(VWORLD_BASE_URL)
                    .queryParam("service", "address")
                    .queryParam("request", REVERSE_GEOCODING_REQUEST)
                    .queryParam("version", VERSION)
                    .queryParam("crs", COORDINATE_SYSTEM)
                    .queryParam("point", point)
                    .queryParam("format", FORMAT)
                    .queryParam("type", ADDRESS_TYPE)
                    .queryParam("key", apiKey)
                    .build()
                    .toUri();

            ResponseEntity<String> response = restTemplate.getForEntity(uri, String.class);
            
            if (!response.getStatusCode().is2xxSuccessful()) {
                return GeocodingResult.failure("HTTP 오류: " + response.getStatusCode());
            }

            return parseReverseGeocodingResponse(response.getBody(), latitude, longitude);

        } catch (Exception e) {
            return GeocodingResult.failure("역지오코딩 요청 실패: " + e.getMessage());
        }
    }

    /**
     * 지오코딩 응답 파싱
     */
    private GeocodingResult parseGeocodingResponse(String responseBody, String originalAddress) {
        try {
            JsonNode root = objectMapper.readTree(responseBody);
            JsonNode response = root.path("response");
            
            if (!"OK".equals(response.path("status").asText())) {
                String status = response.path("status").asText();
                return GeocodingResult.failure("VWorld API 오류: " + status);
            }

            JsonNode result = response.path("result");
            if (result.isMissingNode() || !result.has("point")) {
                return GeocodingResult.failure("주소를 찾을 수 없습니다: " + originalAddress);
            }

            JsonNode point = result.path("point");
            double longitude = point.path("x").asDouble();
            double latitude = point.path("y").asDouble();
            String refinedAddress = result.path("text").asText(originalAddress);

            return GeocodingResult.success(latitude, longitude, refinedAddress);

        } catch (Exception e) {
            return GeocodingResult.failure("응답 파싱 실패: " + e.getMessage());
        }
    }

    /**
     * 역지오코딩 응답 파싱
     */
    private GeocodingResult parseReverseGeocodingResponse(String responseBody, double latitude, double longitude) {
        try {
            JsonNode root = objectMapper.readTree(responseBody);
            JsonNode response = root.path("response");
            
            if (!"OK".equals(response.path("status").asText())) {
                String status = response.path("status").asText();
                return GeocodingResult.failure("VWorld API 오류: " + status);
            }

            JsonNode results = response.path("result");
            if (results.isMissingNode() || !results.isArray() || results.size() == 0) {
                return GeocodingResult.failure("좌표에 해당하는 주소를 찾을 수 없습니다");
            }

            // 첫 번째 결과 사용
            JsonNode firstResult = results.get(0);
            String roadAddress = firstResult.path("text").asText();

            if (roadAddress.isEmpty()) {
                return GeocodingResult.failure("유효한 도로명 주소를 찾을 수 없습니다");
            }

            return GeocodingResult.success(latitude, longitude, roadAddress);

        } catch (Exception e) {
            return GeocodingResult.failure("응답 파싱 실패: " + e.getMessage());
        }
    }

    /**
     * 좌표 유효성 검사
     */
    private boolean isValidCoordinates(double latitude, double longitude) {
        // 기본 좌표 범위 검사
        if (latitude < -90 || latitude > 90 || longitude < -180 || longitude > 180) {
            return false;
        }

        // 한국 영토 대략적 범위 (33-39N, 124-132E)
        if (latitude < 32.0 || latitude > 40.0 || longitude < 123.0 || longitude > 133.0) {
            log.debug("좌표가 한국 영역을 벗어남: lat={}, lon={}", latitude, longitude);
            // 경고만 하고 처리는 계속 (해외 좌표 가능성)
        }

        return true;
    }

    /**
     * 서비스 이용 가능 여부 확인
     */
    public boolean isServiceAvailable() {
        return apiKey != null && !apiKey.trim().isEmpty();
    }

    /**
     * 서비스 통계 정보 반환
     */
    public String getServiceInfo() {
        return String.format("VWorld Geocoding Service - API Key: %s, Timeout: %dms, Max Retries: %d",
                isServiceAvailable() ? "configured" : "not configured",
                timeoutMs,
                maxRetries);
    }
}