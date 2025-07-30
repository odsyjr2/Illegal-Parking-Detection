package com.aivle.ParkingDetection.controller;

import com.aivle.ParkingDetection.service.UserService;
import lombok.RequiredArgsConstructor;
import org.springframework.http.ResponseEntity;
import org.springframework.security.access.prepost.PreAuthorize;
import org.springframework.web.bind.annotation.*;

@RestController
@RequestMapping("/api/admin")
@RequiredArgsConstructor
public class AdminController {

    private final UserService userService;

    // ✅ 사용자 삭제 (ADMIN 권한만 가능)
    @DeleteMapping("/users/{id}")
    @PreAuthorize("hasAuthority('ADMIN')") // ✅ ADMIN만 허용
    public ResponseEntity<?> deleteUser(@PathVariable Long id) {
        userService.deleteUserById(id);
        return ResponseEntity.ok("✅ 사용자 ID " + id + " 삭제 완료");
    }

}
