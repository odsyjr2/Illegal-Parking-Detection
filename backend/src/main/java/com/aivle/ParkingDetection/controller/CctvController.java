package com.aivle.ParkingDetection.controller;

import com.aivle.ParkingDetection.dto.*;
import com.aivle.ParkingDetection.service.CctvService;
import lombok.RequiredArgsConstructor;
import org.springframework.web.bind.annotation.*;

import java.util.List;

@RestController
@RequestMapping("/api/cctvs")
@RequiredArgsConstructor
public class CctvController {

    private final CctvService cctvService;

    @PostMapping
    public CctvDTO create(@RequestBody CctvCreateRequestDTO dto) {
        return cctvService.createCctv(dto);
    }

    @PutMapping("/{id}")
    public CctvDTO update(@PathVariable Long id, @RequestBody CctvUpdateRequestDTO dto) {
        return cctvService.updateCctv(id, dto);
    }

    @DeleteMapping("/{id}")
    public void delete(@PathVariable Long id) {
        cctvService.deleteCctv(id);
    }

    @GetMapping("/{id}")
    public CctvDTO getOne(@PathVariable Long id) {
        return cctvService.getCctv(id);
    }

    @GetMapping
    public List<CctvDTO> getAll() {
        return cctvService.getAllCctvs();
    }
}
