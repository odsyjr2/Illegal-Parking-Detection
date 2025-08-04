package com.aivle.ParkingDetection.dto;

import lombok.AllArgsConstructor;
import lombok.Data;
import lombok.NoArgsConstructor;

@Data
@NoArgsConstructor
@AllArgsConstructor(staticName = "of") // of() 메소드로 인스턴스 생성
public class ApiResponse<T> {
    private String status;
    private String message;
    private T data;

    // 성공 응답 (데이터 포함)
    public static <T> ApiResponse<T> success(String message, T data) {
        return ApiResponse.of("SUCCESS", message, data);
    }

    // 성공 응답 (데이터 없음)
    public static <T> ApiResponse<T> success(String message) {
        return ApiResponse.of("success", message, null);
    }

    // 에러 응답
    public static <T> ApiResponse<T> error(String message) {
        return ApiResponse.of("error", message, null);
    }

    public static <T> ApiResponse<T> fail(String message) {
        return new ApiResponse<>("FAIL", message, null);
    }

    public static <T> ApiResponse<T> fail(String message, T data) {
        return ApiResponse.of("FAIL", message, data);
    }
}
