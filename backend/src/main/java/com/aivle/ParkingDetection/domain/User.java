package com.aivle.ParkingDetection.domain;

import jakarta.persistence.*;
import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

@Entity
@Table(name = "users")
@Data
@NoArgsConstructor
@AllArgsConstructor
@Builder
public class User {
    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(nullable = false)
    private String name; // 사용자 이름

    @Column(nullable = false, unique = true)
    private String email; // 로그인 ID (중복 금지)

    @Column(nullable = false)
    private String password; // 인코딩된 비밀번호

    @Column(nullable = true)
    private String adminCode;// 관리자 코드 -> 0000

    @Enumerated(EnumType.STRING)
    @Column(name = "role", nullable = false)
    private Role role;// 관리자 코드 -> AAAA / 단속 담당자 코드 -> BBBB

}
