package com.aivle.ParkingDetection.jwt;

import com.aivle.ParkingDetection.security.CustomUserDetails;
import io.jsonwebtoken.*;
import io.jsonwebtoken.io.Decoders;
import io.jsonwebtoken.security.Keys;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.security.authentication.UsernamePasswordAuthenticationToken;
import org.springframework.security.core.Authentication;
import org.springframework.security.core.GrantedAuthority;
import org.springframework.security.core.authority.SimpleGrantedAuthority;
import org.springframework.security.core.userdetails.UserDetails;
import org.springframework.security.core.userdetails.UserDetailsService;
import org.springframework.stereotype.Component;

import java.nio.charset.StandardCharsets;
import java.security.Key;
import java.util.*;
import java.util.stream.Collectors;

@Slf4j
@Component
public class JwtTokenProvider {

    // === 설정값 ===
    private static final long ACCESS_TOKEN_VALIDITY = 1000L * 60 * 30;          // 30분
    private static final long REFRESH_TOKEN_VALIDITY = 1000L * 60 * 60 * 24 * 7;// 7일
    private static final long CLOCK_SKEW_SECONDS = 60L;                          // 시계 오차 허용

    // 권한 클레임 후보키 (혹시 나중에 roles/role로 바꿔도 동작하게)
    private static final List<String> ROLE_CLAIMS = List.of("auth", "roles", "role");

    private final Key key;
    private final JwtParser parser;
    private final UserDetailsService userDetailsService;

    public JwtTokenProvider(@Value("${jwt.secret}") String secretKey,
                            UserDetailsService userDetailsService) {
        // secretKey가 Base64 라고 가정 (application.yml)
        // 만약 그냥 평문이면: byte[] keyBytes = secretKey.getBytes(StandardCharsets.UTF_8);
        byte[] keyBytes = Decoders.BASE64.decode(secretKey);
        this.key = Keys.hmacShaKeyFor(keyBytes);

        this.parser = Jwts.parserBuilder()
                .setSigningKey(this.key)
                .setAllowedClockSkewSeconds(CLOCK_SKEW_SECONDS)
                .build();

        this.userDetailsService = userDetailsService;
    }

    // === Access Token 생성 ===
    public String generateAccessToken(Authentication authentication) {
        // GrantedAuthority → 문자열 권한 (ROLE_ 접두어 보장)
        String authorities = authentication.getAuthorities().stream()
                .map(GrantedAuthority::getAuthority)
                .map(r -> r.startsWith("ROLE_") ? r : "ROLE_" + r)
                .collect(Collectors.joining(","));

        Date now = new Date();
        Date exp = new Date(now.getTime() + ACCESS_TOKEN_VALIDITY);

        return Jwts.builder()
                .setSubject(authentication.getName()) // email/username
                .claim("auth", authorities)
                .setIssuedAt(now)
                .setExpiration(exp)
                .signWith(key, SignatureAlgorithm.HS256)
                .compact();
    }

    // === Refresh Token 생성 (권한 클레임 없음) ===
    public String generateRefreshToken(Authentication authentication) {
        CustomUserDetails principal = (CustomUserDetails) authentication.getPrincipal();
        Long userId = principal.getUserId();

        Date now = new Date();
        Date exp = new Date(now.getTime() + REFRESH_TOKEN_VALIDITY);

        return Jwts.builder()
                .setSubject(String.valueOf(userId))
                .setIssuedAt(now)
                .setExpiration(exp)
                .signWith(key, SignatureAlgorithm.HS256)
                .compact();
    }

    // === 토큰 유효성 검사 (액세스 토큰만 true) ===
    public boolean validateToken(String token) {
        try {
            Claims claims = parser.parseClaimsJws(token).getBody();

            // 액세스 토큰 판별: 권한 클레임 존재해야 함
            String rolesCsv = extractRolesCsv(claims);
            if (rolesCsv == null || rolesCsv.isBlank()) {
                log.warn("권한(auth/roles/role) 클레임 없음 → 액세스 토큰 아님(리프레시/무효).");
                return false;
            }
            return true;

        } catch (ExpiredJwtException e) {
            log.warn("만료된 JWT 토큰. exp={}", e.getClaims().getExpiration());
        } catch (io.jsonwebtoken.security.SecurityException e) {
            log.warn("서명/무결성 오류: {}", e.getMessage());
        } catch (MalformedJwtException e) {
            log.warn("잘못된 형식의 JWT 토큰: {}", e.getMessage());
        } catch (UnsupportedJwtException e) {
            log.warn("지원되지 않는 JWT 토큰: {}", e.getMessage());
        } catch (IllegalArgumentException e) {
            log.warn("비어 있거나 잘못된 JWT: {}", e.getMessage());
        }
        return false;
    }

    // === Authentication 추출 (SecurityContext에 올릴 객체) ===
    public Authentication getAuthentication(String token) {
        Claims claims = parseClaims(token);

        String username = claims.getSubject();
        if (username == null || username.isBlank()) {
            throw new IllegalArgumentException("JWT subject(username)이 없습니다.");
        }

        String rolesCsv = extractRolesCsv(claims);
        Collection<SimpleGrantedAuthority> authorities =
                (rolesCsv == null || rolesCsv.isBlank())
                        ? List.of()
                        : Arrays.stream(rolesCsv.split(","))
                        .map(String::trim)
                        .filter(s -> !s.isEmpty())
                        .map(r -> r.startsWith("ROLE_") ? r : "ROLE_" + r) // ROLE_ 강제
                        .map(SimpleGrantedAuthority::new)
                        .collect(Collectors.toList());

        // DB 재조회가 필요한 구조면 userDetailsService 사용
        UserDetails userDetails = userDetailsService.loadUserByUsername(username);
        return new UsernamePasswordAuthenticationToken(userDetails, null, authorities);
    }

    // === 공용 Claims 파서 (만료되어도 Claims 반환) ===
    public Claims parseClaims(String token) {
        try {
            return parser.parseClaimsJws(token).getBody();
        } catch (ExpiredJwtException e) {
            return e.getClaims();
        }
    }

    public long getRemainingExpiration(String token) {
        return parseClaims(token).getExpiration().getTime() - System.currentTimeMillis();
    }

    public String getSubject(String token) {
        return parseClaims(token).getSubject();
    }

    // ----- helpers -----
    @SuppressWarnings("unchecked")
    private String extractRolesCsv(Claims claims) {
        for (String key : ROLE_CLAIMS) {
            Object v = claims.get(key);
            if (v == null) continue;

            // 배열/리스트 형태도 지원
            if (v instanceof Collection<?> col) {
                return col.stream().map(Object::toString).collect(Collectors.joining(","));
            }
            return String.valueOf(v);
        }
        return null;
    }
}
