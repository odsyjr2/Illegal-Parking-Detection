package com.aivle.ParkingDetection.jwt;

import jakarta.servlet.FilterChain;
import jakarta.servlet.ServletException;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.security.core.Authentication;
import org.springframework.security.core.context.SecurityContextHolder;
import org.springframework.stereotype.Component;
import org.springframework.util.StringUtils;
import org.springframework.web.filter.OncePerRequestFilter;

import java.io.IOException;

@Slf4j
@RequiredArgsConstructor
@Component
public class JwtAuthenticationFilter extends OncePerRequestFilter {

    public static final String AUTHORIZATION_HEADER = "Authorization";
    public static final String BEARER_PREFIX = "Bearer ";

    private final JwtTokenProvider jwtTokenProvider;

    @Override
    protected void doFilterInternal(HttpServletRequest request,
                                    HttpServletResponse response,
                                    FilterChain filterChain)
            throws ServletException, IOException {

        String requestURI = request.getRequestURI();

        // ✅ 로그인과 회원가입 요청은 필터 적용 제외
        if (requestURI.startsWith("/api/users/login") || requestURI.startsWith("/api/users/signup")) {
            filterChain.doFilter(request, response);
            return;
        }
        // ** 임시 uploads 파일 필터 적용 제외 //  // ** 임시 report 필터 적용 제외 //
        if (requestURI.startsWith("/api/human-reports") || requestURI.startsWith("/uploads")) {
            filterChain.doFilter(request, response);
            return;
        }


        // ** 임시 uploads 파일 필터 적용 제외 //  // ** 임시 report 필터 적용 제외 //
        if (requestURI.startsWith("/api/human-reports") || requestURI.startsWith("/uploads")) {
            filterChain.doFilter(request, response);
            return;
        }

        String token = resolveToken(request);

        // ✅ 토큰 존재 및 유효성 검사
        if (StringUtils.hasText(token) && jwtTokenProvider.validateToken(token)) {

            // ✅ 인증 객체 설정 (Redis 검사 제거됨)
            Authentication authentication = jwtTokenProvider.getAuthentication(token);
            SecurityContextHolder.getContext().setAuthentication(authentication);
            log.debug("✅ 인증 성공: '{}' → {}", authentication.getName(), requestURI);

        } else {
            if (StringUtils.hasText(token)) {
                log.warn("❌ 유효하지 않은 토큰. URI: {}", requestURI);
            } else {
                log.debug("⛔ 토큰 없음. URI: {}", requestURI);
            }
        }

        filterChain.doFilter(request, response);
    }

    // ✅ 요청 헤더에서 JWT 추출
    private String resolveToken(HttpServletRequest request) {
        String bearerToken = request.getHeader(AUTHORIZATION_HEADER);
        if (StringUtils.hasText(bearerToken) && bearerToken.startsWith(BEARER_PREFIX)) {
            return bearerToken.substring(BEARER_PREFIX.length());
        }
        return null;
    }
}