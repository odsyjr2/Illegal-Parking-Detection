package com.aivle.ParkingDetection.config;

import com.aivle.ParkingDetection.exception.CustomAccessDeniedHandler;
import com.aivle.ParkingDetection.jwt.JwtAuthenticationFilter;
import com.aivle.ParkingDetection.jwt.JwtTokenProvider;
import lombok.RequiredArgsConstructor;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.data.redis.core.RedisTemplate;
import org.springframework.security.config.annotation.authentication.builders.AuthenticationManagerBuilder;
import org.springframework.security.config.annotation.web.configuration.EnableWebSecurity;
import org.springframework.security.config.annotation.web.builders.HttpSecurity;
import org.springframework.security.web.SecurityFilterChain;
import org.springframework.security.config.http.SessionCreationPolicy;
import org.springframework.security.crypto.bcrypt.BCryptPasswordEncoder;
import org.springframework.security.crypto.password.PasswordEncoder;
import org.springframework.security.web.authentication.UsernamePasswordAuthenticationFilter;


@Configuration
@EnableWebSecurity
@RequiredArgsConstructor
public class SecurityConfig {

    private final JwtTokenProvider jwtTokenProvider;
    private final RedisTemplate<String, Object> redisTemplate;
    private final CustomAccessDeniedHandler accessDeniedHandler;

    @Bean
    public SecurityFilterChain filterChain(HttpSecurity http) throws Exception {
        JwtAuthenticationFilter jwtAuthenticationFilter =
                new JwtAuthenticationFilter(jwtTokenProvider, redisTemplate); // ✅ 두 인자 전달

        http
                .csrf(csrf -> csrf.disable())
                .headers(headers -> headers.frameOptions(frameOptions -> frameOptions.disable()))

                .authorizeHttpRequests(auth -> auth
                        // ✅ public endpoints
                        .requestMatchers(
                                "/api/users/signup",
                                "/api/users/register",
                                "/api/users/login",
                                "/api/users/logout",
                                "/api/human-reports/**",    // 여기 추가 임시 허용
                                "/uploads/**",              // 여기 추가 임시 허용                            
                                "/h2-console/**",
                                "/api/cctvs",          // GET /api/cctvs
                                "/api/cctvs/*",         // GET /api/cctvs/{id}                                
                                "/api/cctvs/**"
                        ).permitAll()

                        // ✅ 관리자 전용 endpoint 보호
                        .requestMatchers("/api/admin/**").hasAuthority("ADMIN")

                        // ✅ 나머지는 인증만 되면 접근 가능
                        .anyRequest().authenticated()
                )
                .exceptionHandling(ex -> ex.accessDeniedHandler(accessDeniedHandler))
                // ✅ 세션 사용 안 함
                .sessionManagement(sess -> sess.sessionCreationPolicy(SessionCreationPolicy.STATELESS))

                // ✅ JWT 필터 추가
                .addFilterBefore(jwtAuthenticationFilter, UsernamePasswordAuthenticationFilter.class);

        return http.build();
    }

    @Bean
    public PasswordEncoder passwordEncoder() {
        return new BCryptPasswordEncoder();
    }
}

