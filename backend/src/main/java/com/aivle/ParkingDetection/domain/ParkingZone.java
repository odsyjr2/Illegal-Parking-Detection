package com.aivle.ParkingDetection.domain;

import jakarta.persistence.*;
import lombok.Data;

import java.time.LocalTime;
import java.util.ArrayList;
import java.util.List;

@Entity
@Data
@Table(name = "parking_zone")
public class ParkingZone {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(nullable = false, length = 100)
    private String zoneName;

    @Column(nullable = false)
    private LocalTime allowedStart;

    @Column(nullable = false)
    private LocalTime allowedEnd;

    @OneToMany(mappedBy = "zone",
            cascade = CascadeType.ALL,
            orphanRemoval = true,
            fetch = FetchType.LAZY)
    private List<ParkingSection> sections = new ArrayList<>();

    // 연관관계 편의 메서드
    public void addSection(ParkingSection s) {
        s.setZone(this);
        sections.add(s);
    }

    public void removeSection(ParkingSection s) {
        s.setZone(null);
        sections.remove(s);
    }
}