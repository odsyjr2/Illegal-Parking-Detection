package com.aivle.ParkingDetection.domain;

import jakarta.persistence.*;
import lombok.*;
import java.time.LocalDate;

@Entity
@Getter @Setter
@NoArgsConstructor
@AllArgsConstructor
@Builder
public class Cctv {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    private String location;         // 위치
    private String ipAddress;        // CCTV IP 주소
    private boolean active;          // 작동 여부
    private String description;      // 설명

    private Double latitude;         // 위도
    private Double longitude;        // 경도

    private LocalDate installationDate;  //  설치일
}
