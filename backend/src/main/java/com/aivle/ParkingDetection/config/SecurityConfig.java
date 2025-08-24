package com.aivle.ParkingDetection.config;

import com.aivle.ParkingDetection.exception.CustomAccessDeniedHandler;
import com.aivle.ParkingDetection.jwt.JwtAuthenticationFilter;
import com.aivle.ParkingDetection.jwt.JwtTokenProvider;
import lombok.RequiredArgsConstructor;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.http.HttpMethod;
import org.springframework.security.config.annotation.method.configuration.EnableMethodSecurity;
import org.springframework.security.config.annotation.web.configuration.EnableWebSecurity;
import org.springframework.security.config.annotation.web.builders.HttpSecurity;
import org.springframework.security.web.SecurityFilterChain;
import org.springframework.security.config.http.SessionCreationPolicy;
import org.springframework.security.crypto.bcrypt.BCryptPasswordEncoder;
import org.springframework.security.crypto.password.PasswordEncoder;
import org.springframework.security.web.authentication.UsernamePasswordAuthenticationFilter;
import org.springframework.security.web.authentication.HttpStatusEntryPoint;
import org.springframework.http.HttpStatus;

import static org.springframework.security.config.Customizer.withDefaults;
import java.util.List;
import org.springframework.web.cors.CorsConfiguration;
import org.springframework.web.cors.CorsConfigurationSource;
import org.springframework.web.cors.UrlBasedCorsConfigurationSource;

@Configuration
@EnableWebSecurity
@EnableMethodSecurity(prePostEnabled = true)
@RequiredArgsConstructor
public class SecurityConfig {

    private final JwtTokenProvider jwtTokenProvider;
    private final CustomAccessDeniedHandler accessDeniedHandler;

    @Bean
    public SecurityFilterChain filterChain(HttpSecurity http) throws Exception {
        JwtAuthenticationFilter jwtAuthenticationFilter =
                new JwtAuthenticationFilter(jwtTokenProvider);

        http
                .cors(withDefaults())
                .csrf(csrf -> csrf.disable())
                .headers(h -> h.frameOptions(f -> f.disable()))
                .sessionManagement(sm -> sm.sessionCreationPolicy(SessionCreationPolicy.STATELESS))
                .authorizeHttpRequests(auth -> auth
                        // Preflight
                        .requestMatchers(HttpMethod.OPTIONS, "/**").permitAll()

                        // 공개 엔드포인트
                        .requestMatchers(
                                "/api/users/check-email",
                                "/api/users/signup",
                                "/api/users/register",
                                "/api/users/login",
                                "/api/users/logout",
                                "/api/human-reports/**",
                                "/uploads/**",
                                "/h2-console/**",
                                "/api/cctvs",
                                "/api/cctvs/*",
                                "/api/cctvs/**",
                                "/api/ai/v1/**",  // AI INTEGRATION - Allow AI processor endpoints
                                "/api/patrol-routes",  // AI PATROL ROUTES - Allow patrol route endpoints
                                "/api/patrol-routes/**"
                        ).permitAll()

                        // 관리자 전용
                        .requestMatchers("/api/admin/**").hasRole("ADMIN")

                        // ===== zones 권한 분리 =====
                        // 조회: INSPECTOR, ADMIN
                        .requestMatchers(HttpMethod.GET, "/api/zones", "/api/zones/**")
                        .hasAnyRole("ADMIN", "INSPECTOR")
                        // 생성/수정/삭제: ADMIN만
                        .requestMatchers(HttpMethod.POST, "/api/zones", "/api/zones/**")
                        .hasRole("ADMIN")
                        .requestMatchers(HttpMethod.PUT, "/api/zones", "/api/zones/**")
                        .hasRole("ADMIN")
                        .requestMatchers(HttpMethod.PATCH, "/api/zones", "/api/zones/**")
                        .hasRole("ADMIN")
                        .requestMatchers(HttpMethod.DELETE, "/api/zones", "/api/zones/**")
                        .hasRole("ADMIN")

                        // 그 외는 인증 필요
                        .anyRequest().authenticated()
                )
                .exceptionHandling(ex -> ex
                        .authenticationEntryPoint(new HttpStatusEntryPoint(HttpStatus.UNAUTHORIZED)) // 인증X -> 401
                        .accessDeniedHandler(accessDeniedHandler)                                    // 인증O 권한X -> 403
                )
                .addFilterBefore(jwtAuthenticationFilter, UsernamePasswordAuthenticationFilter.class);

        return http.build();
    }

    @Bean
    public PasswordEncoder passwordEncoder() { return new BCryptPasswordEncoder(); }

    @Bean
    public CorsConfigurationSource corsConfigurationSource() {
        CorsConfiguration config = new CorsConfiguration();
        config.setAllowedOriginPatterns(List.of("http://localhost:5173"));
        config.setAllowedMethods(List.of("GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"));

        config.setAllowedHeaders(List.of(
                "Authorization", "Content-Type", "Accept", "X-Requested-With",
                "Origin", "User-Agent", "Referer", "Cache-Control", "Pragma"
        ));
        config.setExposedHeaders(List.of("Authorization"));
        config.setAllowCredentials(true);

        UrlBasedCorsConfigurationSource source = new UrlBasedCorsConfigurationSource();
        source.registerCorsConfiguration("/**", config);
        return source;
    }
}
