package com.aivle.ParkingDetection.config;

import org.springframework.cache.CacheManager;
import org.springframework.cache.annotation.EnableCaching;
import org.springframework.cache.concurrent.ConcurrentMapCacheManager;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;

/**
 * 캐시 설정 클래스
 * 
 * VWorld API 지오코딩 결과 캐싱을 위한 Spring Cache 설정
 */
@Configuration
@EnableCaching
public class CacheConfig {

    /**
     * 캐시 매니저 설정
     * 
     * @return CacheManager
     */
    @Bean
    public CacheManager cacheManager() {
        // 단순한 인메모리 캐시 사용 (프로덕션에서는 Redis 등 고려)
        return new ConcurrentMapCacheManager(
                "geocoding",        // 지오코딩 결과 캐시
                "reverseGeocoding"  // 역지오코딩 결과 캐시
        );
    }
}