package com.aivle.ParkingDetection.controller;

import com.aivle.ParkingDetection.dto.ParkingZoneDTO;
import com.aivle.ParkingDetection.service.ParkingZoneService;
import lombok.RequiredArgsConstructor;
import org.springframework.http.ResponseEntity;
import org.springframework.security.access.prepost.PreAuthorize;
import org.springframework.web.bind.annotation.*;

import java.util.List;

@RestController
@RequestMapping("/api/zones")
@RequiredArgsConstructor
public class ParkingZoneController {

    private final ParkingZoneService service;

    // 전체 목록 (ADMIN, INSPECTOR 모두)
    @GetMapping
    @PreAuthorize("hasAnyAuthority('ADMIN','INSPECTOR')")
    public ResponseEntity<List<ParkingZoneDTO>> list() {
        return ResponseEntity.ok(service.listAll());
    }

}
