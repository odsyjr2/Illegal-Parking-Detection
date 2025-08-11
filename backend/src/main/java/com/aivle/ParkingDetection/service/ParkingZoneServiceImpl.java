package com.aivle.ParkingDetection.service;

import com.aivle.ParkingDetection.domain.ParkingZone;
import com.aivle.ParkingDetection.dto.ParkingZoneDTO;
import com.aivle.ParkingDetection.dto.ParkingZoneRequestDTO;
import com.aivle.ParkingDetection.repository.ParkingZoneRepository;
import lombok.RequiredArgsConstructor;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.util.List;

import static java.util.stream.Collectors.toList;

@Service
@RequiredArgsConstructor
@Transactional
public class ParkingZoneServiceImpl implements ParkingZoneService {

    private final ParkingZoneRepository repository;

    @Transactional(readOnly = true)
    @Override
    public List<ParkingZoneDTO> listAll() {
        return repository.findAll().stream().map(this::toDTO).collect(toList());
    }

    @Transactional(readOnly = true)
    @Override
    public ParkingZoneDTO getById(Long id) {
        ParkingZone zone = repository.findById(id)
                .orElseThrow(() -> new IllegalArgumentException("구역을 찾을 수 없습니다. id=" + id));
        return toDTO(zone);
    }

    @Override
    public ParkingZoneDTO create(ParkingZoneRequestDTO req) {
//        if (repository.existsByZoneName(req.getZoneName())) {
//            throw new IllegalArgumentException("이미 존재하는 구역명입니다: " + req.getZoneName());
//        }
        ParkingZone zone = ParkingZone.builder()
                .zoneName(req.getZoneName())
                .origin(req.getOrigin())
                .destination(req.getDestination())
                .parkingAllowed(Boolean.TRUE.equals(req.getParkingAllowed()))
                .allowedStart(req.getAllowedStart())
                .allowedEnd(req.getAllowedEnd())
                .build();
        return toDTO(repository.save(zone));
    }

    @Override
    @org.springframework.transaction.annotation.Transactional
    public ParkingZoneDTO update(Long id, ParkingZoneRequestDTO req) {
        ParkingZone zone = repository.findById(id)
                .orElseThrow(() -> new IllegalArgumentException("구역을 찾을 수 없습니다. id=" + id));

        // ✅ 구역명 중복 허용: 값이 왔을 때만 세팅 (중복 체크 없음)
        if (req.getZoneName() != null) {
            zone.setZoneName(req.getZoneName());
        }

        // ✅ 나머지도 값이 온 것만 반영 (부분 수정)
        if (req.getOrigin() != null)         zone.setOrigin(req.getOrigin());
        if (req.getDestination() != null)    zone.setDestination(req.getDestination());
        if (req.getParkingAllowed() != null) zone.setParkingAllowed(req.getParkingAllowed());
        if (req.getAllowedStart() != null)   zone.setAllowedStart(req.getAllowedStart());
        if (req.getAllowedEnd() != null)     zone.setAllowedEnd(req.getAllowedEnd());

        // JPA 더티체킹으로 자동 반영됨 (save 불필요)
        return toDTO(zone);
    }


    @Override
    public void delete(Long id) {
        if (!repository.existsById(id)) {
            throw new IllegalArgumentException("구역을 찾을 수 없습니다. id=" + id);
        }
        repository.deleteById(id);
    }

    private ParkingZoneDTO toDTO(ParkingZone z) {
        return ParkingZoneDTO.builder()
                .id(z.getId())
                .zoneName(z.getZoneName())
                .origin(z.getOrigin())
                .destination(z.getDestination())
                .parkingAllowed(z.getParkingAllowed())
                .allowedStart(z.getAllowedStart())
                .allowedEnd(z.getAllowedEnd())
                .build();
    }
}
