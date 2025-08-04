package com.aivle.ParkingDetection.exception;

import com.aivle.ParkingDetection.dto.ApiResponse;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

@RestControllerAdvice
public class GlobalExceptionHandler {

    @ExceptionHandler(UserExistsException.class)
    public ResponseEntity<ApiResponse<Object>> handleUserExists(UserExistsException ex) {
        return ResponseEntity
                .status(HttpStatus.BAD_REQUEST) // 400으로 지정
                .body(ApiResponse.error(ex.getMessage()));
    }

    @ExceptionHandler(RuntimeException.class)
    public ResponseEntity<ApiResponse<Object>> handleRuntimeException(RuntimeException ex) {
        return ResponseEntity.status(HttpStatus.UNAUTHORIZED)
                .body(ApiResponse.fail("실패: " + ex.getMessage()));
    }
}
