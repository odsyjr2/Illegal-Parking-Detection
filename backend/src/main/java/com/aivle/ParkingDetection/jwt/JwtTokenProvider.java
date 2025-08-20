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
    private static final long ACCESS_TOKEN_VALIDITY = 1000L * 60 * 30;           // 30분
    private static final long REFRESH_TOKEN_VALIDITY = 1000L * 60 * 60 * 24 * 7; // 7일
    private static final long CLOCK_SKEW_SECONDS = 60L;                           // 시계 오차 허용

    // 권한 클레임 후보키 (호환용)
    private static final List<String> ROLE_CLAIMS = List.of("auth", "roles", "role");

    private final Key key;
    private final JwtParser parser;
    private final UserDetailsService userDetailsService;

    public JwtTokenProvider(@Value("${jwt.secret}") String secretKey,
                            UserDetailsService userDetailsService) {
        // ✅ Base64/평문 둘 다 지원
        byte[] keyBytes = decodeSecretLenient(secretKey);
        this.key = Keys.hmacShaKeyFor(keyBytes);

        this.parser = Jwts.parserBuilder()
                .setSigningKey(this.key)
                .setAllowedClockSkewSeconds(CLOCK_SKEW_SECONDS)
                .build();

        this.userDetailsService = userDetailsService;
    }

    // === Access Token 생성 ===
    public String generateAccessToken(Authentication authentication) {
        // ✅ GrantedAuthority → 문자열 권한 (항상 ROLE_ 접두어)
        String authorities = authentication.getAuthorities().stream()
                .map(GrantedAuthority::getAuthority)              // e.g. ADMIN or ROLE_ADMIN
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

    // === 토큰 유효성 검사 (액세스 토큰에만 true) ===
    public boolean validateToken(String token) {
        try {
            Claims claims = parser.parseClaimsJws(token).getBody();

            // ✅ 액세스 토큰 판별: 권한 클레임이 있어야 함
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

    // === Authentication 추출 ===
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
                        .map(r -> r.startsWith("ROLE_") ? r : "ROLE_" + r) // ✅ ROLE_ 강제
                        .map(SimpleGrantedAuthority::new)
                        .collect(Collectors.toList());

        // DB 재조회(권장): 계정 상태/비밀번호 변경 반영 가능
        UserDetails userDetails = userDetailsService.loadUserByUsername(username);

        return new UsernamePasswordAuthenticationToken(userDetails, null, authorities);
    }

    // === 만료여도 Claims 반환 ===
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
    private static byte[] decodeSecretLenient(String secretKey) {
        try {
            // Base64로 정상 디코딩되면 그대로 사용
            return Decoders.BASE64.decode(secretKey);
        } catch (IllegalArgumentException ex) {
            // Base64가 아니면 평문으로 간주
            return secretKey.getBytes(StandardCharsets.UTF_8);
        }
    }

    @SuppressWarnings("unchecked")
    private String extractRolesCsv(Claims claims) {
        for (String key : ROLE_CLAIMS) {
            Object v = claims.get(key);
            if (v == null) continue;

            if (v instanceof Collection<?> col) {
                return col.stream().map(Object::toString).collect(Collectors.joining(","));
            }
            return String.valueOf(v);
        }
        return null;
    }
}
