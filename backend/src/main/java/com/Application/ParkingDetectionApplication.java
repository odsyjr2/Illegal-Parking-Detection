package com.aivle.parkingdetection;

import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.context.annotation.ComponentScan;
import org.springframework.data.jpa.repository.config.EnableJpaRepositories;
import org.springframework.boot.autoconfigure.domain.EntityScan;


@SpringBootApplication
@ComponentScan(basePackages = "com.aivle")
@EnableJpaRepositories(basePackages = "com.aivle.reports")
@EntityScan(basePackages = "com.aivle.reports")
public class ParkingDetectionApplication {
    public static void main(String[] args) {
        SpringApplication.run(ParkingDetectionApplication.class, args);
    }
}
