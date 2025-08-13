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
    private static final String BEARER = "Bearer"; // 접두어만

    private final JwtTokenProvider jwtTokenProvider;

    @Override
    protected void doFilterInternal(HttpServletRequest request,
                                    HttpServletResponse response,
                                    FilterChain chain)
            throws ServletException, IOException {

        final String uri = request.getRequestURI();

        // 1) CORS preflight는 무조건 통과
        if ("OPTIONS".equalsIgnoreCase(request.getMethod())) {
            chain.doFilter(request, response);
            return;
        }

        // 2) 화이트리스트 경로 통과
        if (uri.startsWith("/api/users/login") || uri.startsWith("/api/users/signup")
                || uri.startsWith("/api/human-reports") || uri.startsWith("/uploads")) {
            chain.doFilter(request, response);
            return;
        }

        // 3) Authorization 파싱 (대소문자 무시 + 여분 공백 허용)
        String token = resolveToken(request);

        try {
            if (StringUtils.hasText(token)) {
                if (jwtTokenProvider.validateToken(token)) {
                    Authentication auth = jwtTokenProvider.getAuthentication(token);
                    SecurityContextHolder.getContext().setAuthentication(auth);
                    log.debug("✅ 인증 성공 user={}, uri={}", auth.getName(), uri);
                } else {
                    SecurityContextHolder.clearContext();
                    log.warn("❌ validateToken=false (액세스 토큰 아님/만료/무결성). uri={}", uri);
                }
            } else {
                log.debug("⛔ Authorization 헤더 없음. uri={}", uri);
            }
        } catch (io.jsonwebtoken.ExpiredJwtException e) {
            SecurityContextHolder.clearContext();
            log.warn("❌ 토큰 만료 exp={}, uri={}", e.getClaims().getExpiration(), uri);
        } catch (io.jsonwebtoken.security.SecurityException e) {
            SecurityContextHolder.clearContext();
            log.warn("❌ 서명/무결성 오류: {}, uri={}", e.getMessage(), uri);
        } catch (Exception e) {
            SecurityContextHolder.clearContext();
            log.error("❌ 토큰 처리 중 예외 uri={}", uri, e);
        }

        chain.doFilter(request, response);
    }

    private String resolveToken(HttpServletRequest request) {
        String auth = request.getHeader(AUTHORIZATION_HEADER);
        if (!StringUtils.hasText(auth)) return null;
        // Bearer 대소문자 무시 + 공백 허용
        if (auth.regionMatches(true, 0, BEARER, 0, BEARER.length())) {
            String t = auth.substring(BEARER.length()).trim();
            return t.isEmpty() ? null : t;
        }
        return null;
    }

}