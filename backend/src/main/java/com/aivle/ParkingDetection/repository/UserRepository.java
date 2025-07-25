package com.aivle.ParkingDetection.repository;

import com.aivle.ParkingDetection.domain.User;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;

import java.util.Optional;

@Repository
public interface UserRepository extends JpaRepository<User, Long> {
    Optional<User> findByEmail(String email);
    boolean existsByEmail(String email);    // 회원가입 시, 이메일 중복 확인 -> 존재하면 true
}
