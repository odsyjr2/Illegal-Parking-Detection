package com.aivle.ParkingDetection.config;

import com.zaxxer.hikari.HikariDataSource;
import org.springframework.boot.ApplicationRunner;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.core.env.Environment;

import javax.sql.DataSource;
import java.util.Arrays;

@Configuration
public class DebugConfig {
    @Bean
    ApplicationRunner dsLogger(DataSource ds, Environment env) {
        return args -> {
            String url = (ds instanceof HikariDataSource h) ? h.getJdbcUrl() : ds.toString();
            System.out.println("=== DEBUG: ACTIVE PROFILES = " + Arrays.toString(env.getActiveProfiles()));
            System.out.println("=== DEBUG: DATASOURCE URL = " + url);
        };
    }
}