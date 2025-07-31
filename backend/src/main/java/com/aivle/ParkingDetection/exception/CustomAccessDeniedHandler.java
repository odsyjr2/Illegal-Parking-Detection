package com.aivle.ParkingDetection.exception;

import com.fasterxml.jackson.databind.ObjectMapper;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import org.springframework.security.access.AccessDeniedException;
import org.springframework.security.web.access.AccessDeniedHandler;
import org.springframework.stereotype.Component;

import java.io.IOException;
import java.util.HashMap;
import java.util.Map;

@Component
public class CustomAccessDeniedHandler implements AccessDeniedHandler {

    private final ObjectMapper objectMapper = new ObjectMapper();

    @Override
    public void handle(HttpServletRequest request,
                       HttpServletResponse response,
                       AccessDeniedException accessDeniedException) throws IOException {

        response.setStatus(HttpServletResponse.SC_FORBIDDEN);
        response.setContentType("application/json;charset=UTF-8");

        String requestURI = request.getRequestURI();
        String method = request.getMethod();
        String message;

        if (requestURI.startsWith("/api/admin/users")) {
            message = "사용자는 회원 목록을 볼 권한이 없습니다.";
        } else if (requestURI.startsWith("/api/users") && "DELETE".equalsIgnoreCase(method)) {
            message = "사용자는 탈퇴 권한이 없습니다.";
        } else {
            message = "접근 권한이 없습니다.";
        }

        Map<String, Object> body = new HashMap<>();
        body.put("status", "ERROR");
        body.put("message", message);
        body.put("data", null);

        response.getWriter().write(objectMapper.writeValueAsString(body));
    }
}
