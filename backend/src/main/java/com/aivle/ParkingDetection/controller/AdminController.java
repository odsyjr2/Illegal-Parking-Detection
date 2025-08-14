package com.aivle.ParkingDetection.controller;

import com.aivle.ParkingDetection.dto.ParkingZoneDTO;
import com.aivle.ParkingDetection.dto.ParkingZoneRequestDTO;
import com.aivle.ParkingDetection.dto.UserDTO;
import com.aivle.ParkingDetection.service.ParkingZoneService;
import com.aivle.ParkingDetection.service.UserService;
import lombok.RequiredArgsConstructor;
import org.springframework.http.ResponseEntity;
import org.springframework.security.access.prepost.PreAuthorize;
import org.springframework.web.bind.annotation.*;

import java.util.List;

@RestController
@RequestMapping("/api/admin")
@RequiredArgsConstructor
public class AdminController {

    private final UserService userService;
    private final ParkingZoneService parkingZoneService;

    // ✅ 전체 회원 목록
    @PreAuthorize("hasRole('ADMIN')")
    @GetMapping("/users")
    public ResponseEntity<List<UserDTO>> getAllUsers() {
        List<UserDTO> users = userService.getAllUsers();
        return ResponseEntity.ok(users);
    }

    // ✅ 사용자 삭제 (ADMIN 권한만 가능)
    @DeleteMapping("/users/{id}")
    @PreAuthorize("hasRole('ADMIN')")  // ✅ ADMIN만 허용
    public ResponseEntity<?> deleteUser(@PathVariable Long id) {
        userService.deleteUserById(id);
        return ResponseEntity.ok("✅ 사용자 ID " + id + " 삭제 완료");
    }

//    // ✅ 구역 추가 (ADMIN)
//    @PostMapping("/zones")
//    @PreAuthorize("hasAuthority('ADMIN')")
//    public ResponseEntity<ParkingZoneDTO> createZone(@RequestBody ParkingZoneRequestDTO request) {
//        return ResponseEntity.ok(parkingZoneService.create(request));
//    }
//
//    // ✅ 구역 수정 (ADMIN)
//    @PatchMapping("/zones/{id}")
//    @PreAuthorize("hasAuthority('ADMIN')")
//    public ResponseEntity<ParkingZoneDTO> patchZone(
//            @PathVariable Long id,
//            @RequestBody ParkingZoneRequestDTO request
//    ) {
//        return ResponseEntity.ok(parkingZoneService.update(id, request));
//    }
//
//    // ✅ 구역 삭제 (ADMIN)
//    @DeleteMapping("/zones/{id}")
//    @PreAuthorize("hasAuthority('ADMIN')")
//    public ResponseEntity<String> deleteZone(@PathVariable Long id) {
//        parkingZoneService.delete(id);
//        return ResponseEntity.ok("구역이 삭제되었습니다. id=" + id);
//    }

}
