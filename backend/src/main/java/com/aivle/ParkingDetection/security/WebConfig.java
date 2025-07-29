package com.aivle.ParkingDetection.security;

import org.springframework.context.annotation.Configuration;
import org.springframework.web.servlet.config.annotation.CorsRegistry;
import org.springframework.web.servlet.config.annotation.WebMvcConfigurer;
import org.springframework.web.servlet.config.annotation.ResourceHandlerRegistry;

import java.nio.file.Paths;
import java.nio.file.Path;

@Configuration
public class WebConfig implements WebMvcConfigurer {
    @Override
    public void addCorsMappings(CorsRegistry registry) {
        registry.addMapping("/**")
                .allowedOrigins("http://localhost:5173") // React 개발 서버 주소
                .allowedMethods("*")
                .allowedHeaders("*")
                .allowCredentials(true);
    }

    // ✅ 정적 리소스 핸들링 (이미지 등)
    @Override
    public void addResourceHandlers(ResourceHandlerRegistry registry) {
        // 운영체제에 따라 경로 생성
        String uploadPath = Paths.get("uploads").toAbsolutePath().toUri().toString();

        registry.addResourceHandler("/uploads/**")
                .addResourceLocations(uploadPath); // "file:/absolute/path/uploads/"
    }
}

