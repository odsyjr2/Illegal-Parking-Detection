package com.aivle.ParkingDetection.controller;

import com.aivle.ParkingDetection.dto.ParkingSectionRequestDTO;
import com.aivle.ParkingDetection.dto.ParkingZoneDTO;
import com.aivle.ParkingDetection.dto.ParkingZoneRequestDTO;
import com.aivle.ParkingDetection.service.ParkingZoneService;
import org.springframework.http.ResponseEntity;
import org.springframework.security.access.prepost.PreAuthorize;
import org.springframework.web.bind.annotation.*;

import java.net.URI;
import java.util.List;

@RestController
@RequestMapping("/api/zones")
public class ParkingZoneController {

    private final ParkingZoneService service;
    public ParkingZoneController(ParkingZoneService service) { this.service = service; }

    // ===== 조회: INSPECTOR, ADMIN =====
    @GetMapping
    @PreAuthorize("hasAnyRole('INSPECTOR','ADMIN')")
    public ResponseEntity<List<ParkingZoneDTO>> getAll() {
        return ResponseEntity.ok(service.findAll());
    }

//    @GetMapping("/{id}")
//    @PreAuthorize("hasAnyRole('INSPECTOR','ADMIN')")
//    public ResponseEntity<ParkingZoneDTO> getOne(@PathVariable Long id) {
//        return ResponseEntity.ok(service.findOne(id));
//    }

    // ===== 생성/수정/삭제: ADMIN만 =====
    @PostMapping
    @PreAuthorize("hasRole('ADMIN')")
    public ResponseEntity<ParkingZoneDTO> create(@RequestBody ParkingZoneRequestDTO req) {
        ParkingZoneDTO created = service.create(req);
        return ResponseEntity.created(URI.create("/api/zones/" + created.getId())).body(created);
    }

    @PatchMapping("/{zoneId}/sections/{sectionId}")
    @PreAuthorize("hasRole('ADMIN')")
    public ResponseEntity<ParkingZoneDTO> updateSection(
            @PathVariable Long zoneId,
            @PathVariable Long sectionId,
            @RequestBody ParkingSectionRequestDTO req
    ) {
        return ResponseEntity.ok(service.updateSection(zoneId, sectionId, req));
    }

    @DeleteMapping("/{zoneId}/sections/{sectionId}")
    @PreAuthorize("hasRole('ADMIN')")
    public ResponseEntity<Void> deleteSection(
            @PathVariable Long zoneId,
            @PathVariable Long sectionId
    ) {
        // 서비스가 ParkingZoneDTO를 리턴하더라도, 여기선 결과를 사용하지 않고 삭제만 수행
        service.removeSection(zoneId, sectionId);
        return ResponseEntity.noContent().build(); // 204
    }

    @DeleteMapping("/{zoneId}")
    @PreAuthorize("hasRole('ADMIN')")
    public ResponseEntity<Void> deleteZone(@PathVariable Long zoneId) {
        service.delete(zoneId);
        return ResponseEntity.noContent().build(); // 204
    }

}
