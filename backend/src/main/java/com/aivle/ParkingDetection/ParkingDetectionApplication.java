package com.aivle.ParkingDetection;

import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.context.ConfigurableApplicationContext;

@SpringBootApplication
public class ParkingDetectionApplication {

	public static void main(String[] args) {
		// AI Integration - Ensure proper cleanup on termination
		ConfigurableApplicationContext context = SpringApplication.run(ParkingDetectionApplication.class, args);
		
		// Add shutdown hook to ensure proper cleanup
		Runtime.getRuntime().addShutdownHook(new Thread(() -> {
			System.out.println("Shutting down Spring Boot application...");
			context.close();
			System.out.println("Application terminated cleanly.");
		}));
	}
}
