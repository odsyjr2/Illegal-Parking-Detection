package com.aivle.reports;

import jakarta.persistence.*;
import lombok.*;
import org.hibernate.annotations.CreationTimestamp;
import java.sql.Timestamp;

@Entity
@Table(name = "humanDetectionReports")
@Data
@NoArgsConstructor
@AllArgsConstructor
public class HumanDetectionReport {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    // @Column(nullable = false)
    private String userID;

    private String imageURL;

    private Double latitude;

    private Double longitude;

    private String vehicleNumber;

    @Column(columnDefinition = "TEXT")
    private String reason;

    @Column(nullable = false)
    private String status = "접수"; // ex: "접수", "진행중", "완료"

    @CreationTimestamp
    private Timestamp createdAt;

    private String region; // 선택 사항, 예: "강남"

    private String location; // 선택 사항, 상세주소

    private String title; // 선택 사항, 신고 제목
}
