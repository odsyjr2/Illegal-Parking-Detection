package com.aivle.ParkingDetection.domain;

import jakarta.persistence.*;
import lombok.*;
import java.time.LocalTime;

@Entity
@Table(name = "parking_zones")
@Data
@NoArgsConstructor @AllArgsConstructor @Builder
public class ParkingZone {

    @Id @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(nullable = false)
    private String zoneName;         // 구역명

    private String origin;           // 출발지

    private String destination;      // 도착지

    @Column(nullable = false)
    private Boolean parkingAllowed;  // 주정차 허용 여부

    @Column(nullable = false)
    private LocalTime allowedStart;  // 허용 시작 시간 (예: 09:00)

    @Column(nullable = false)
    private LocalTime allowedEnd;    // 허용 종료 시간 (예: 18:00)
}
