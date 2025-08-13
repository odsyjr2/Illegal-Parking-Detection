package com.aivle.ParkingDetection.service;

import com.aivle.ParkingDetection.domain.ParkingSection;
import com.aivle.ParkingDetection.domain.ParkingZone;
import com.aivle.ParkingDetection.dto.ParkingSectionRequestDTO;
import com.aivle.ParkingDetection.dto.ParkingZoneDTO;
import com.aivle.ParkingDetection.dto.ParkingZoneRequestDTO;
import com.aivle.ParkingDetection.mapper.ParkingMapper;
import com.aivle.ParkingDetection.repository.ParkingSectionRepository;
import com.aivle.ParkingDetection.repository.ParkingZoneRepository;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.util.*;
import java.util.stream.Collectors;

@Service
@Transactional
public class ParkingZoneServiceImpl implements ParkingZoneService {

    private final ParkingZoneRepository zoneRepo;
    private final ParkingSectionRepository sectionRepo;

    public ParkingZoneServiceImpl(ParkingZoneRepository zoneRepo, ParkingSectionRepository sectionRepo) {
        this.zoneRepo = zoneRepo;
        this.sectionRepo = sectionRepo;
    }

    @Override @Transactional(readOnly = true)
    public List<ParkingZoneDTO> findAll() {
        return zoneRepo.findAll().stream()
                .map(ParkingMapper::toZoneDTO)
                .collect(Collectors.toList());
    }

    @Override @Transactional(readOnly = true)
    public ParkingZoneDTO findOne(Long id) {
        ParkingZone z = zoneRepo.findById(id)
                .orElseThrow(() -> new NoSuchElementException("존재하지 않는 구역 id=" + id));
        return ParkingMapper.toZoneDTO(z);
    }

    @Override
    public ParkingZoneDTO create(ParkingZoneRequestDTO req) {
        if (req.getZoneName() == null)
            throw new IllegalArgumentException("zoneName은 필수입니다.");

        // 1) 같은 zoneName 있으면 그 ZONE 재사용, 없으면 새로 생성
        ParkingZone zone = zoneRepo.findTopByZoneNameOrderByIdAsc(req.getZoneName())
                .orElseGet(() -> {
                    // 새 Zone 생성
                    ParkingZone z = new ParkingZone();
                    z.setZoneName(req.getZoneName());

                    // 새로 만들 때는 allowedTime이 꼭 있어야 함
                    if (req.getAllowedTime() == null) {
                        throw new IllegalArgumentException("새 Zone을 만들 때는 allowedTime이 필요합니다. (예: 08:00~20:00)");
                    }
                    var r = ParkingMapper.parseRange(req.getAllowedTime());
                    z.setAllowedStart(r[0]);
                    z.setAllowedEnd(r[1]);
                    return zoneRepo.save(z);
                });

        // 2) 기존 Zone에 대한 allowedTime이 요청에 있으면 업데이트(선택)
        if (req.getAllowedTime() != null) {
            var r = ParkingMapper.parseRange(req.getAllowedTime());
            zone.setAllowedStart(r[0]);
            zone.setAllowedEnd(r[1]);
        }

        // 3) 섹션 추가 (요청에 있으면)
        if (req.getSections() != null) {
            for (var sreq : req.getSections()) {
                ParkingSection s = ParkingMapper.toSectionEntity(sreq);
                s.setZone(zone);
                zone.addSection(s);          // 연관관계 설정
                sectionRepo.save(s);         // Cascade 설정에 따라 생략 가능하지만 안전하게 저장
            }
        }

        return ParkingMapper.toZoneDTO(zone);
    }



    @Override
    public ParkingZoneDTO update(Long id, ParkingZoneRequestDTO req) {
        ParkingZone zone = zoneRepo.findById(id)
                .orElseThrow(() -> new NoSuchElementException("존재하지 않는 구역 id=" + id));

        // ✅ zoneName은 그냥 부분 수정 (중복 허용)
        if (req.getZoneName() != null) {
            zone.setZoneName(req.getZoneName());
        }

        // allowedTime 부분 수정
        if (req.getAllowedTime() != null) {
            var r = ParkingMapper.parseRange(req.getAllowedTime());
            zone.setAllowedStart(r[0]);
            zone.setAllowedEnd(r[1]);
        }

        // sections 부분 수정(기존 로직 유지: 전달된 것만 업데이트/추가, 나머지는 보존)
        if (req.getSections() != null) {
            Map<Long, ParkingSection> current = zone.getSections().stream()
                    .filter(s -> s.getId() != null)
                    .collect(Collectors.toMap(ParkingSection::getId, s -> s));

            for (var sreq : req.getSections()) {
                if (sreq.getId() != null) {
                    ParkingSection exist = current.get(sreq.getId());
                    if (exist == null) throw new NoSuchElementException("존재하지 않는 섹션 id=" + sreq.getId());
                    ParkingMapper.applySectionUpdate(exist, sreq);
                } else {
                    ParkingSection created = ParkingMapper.toSectionEntity(sreq);
                    created.setZone(zone);
                    zone.addSection(created);
                    sectionRepo.save(created);
                }
            }
        }
        return ParkingMapper.toZoneDTO(zone);
    }



    @Override
    public void delete(Long id) {
        ParkingZone z = zoneRepo.findById(id)
                .orElseThrow(() -> new NoSuchElementException("존재하지 않는 구역 id=" + id));
        zoneRepo.delete(z); // 섹션은 orphanRemoval로 함께 삭제
    }

    @Override
    public ParkingZoneDTO addSection(Long zoneId, ParkingSectionRequestDTO req) {
        ParkingZone z = zoneRepo.findById(zoneId)
                .orElseThrow(() -> new NoSuchElementException("존재하지 않는 구역 id=" + zoneId));
        ParkingSection s = ParkingMapper.toSectionEntity(req);
        z.addSection(s);
        return ParkingMapper.toZoneDTO(z);
    }

    @Override
    public ParkingZoneDTO updateSection(Long zoneId, Long sectionId, ParkingSectionRequestDTO req) {
        ParkingZone z = zoneRepo.findById(zoneId)
                .orElseThrow(() -> new NoSuchElementException("존재하지 않는 구역 id=" + zoneId));
        ParkingSection target = z.getSections().stream()
                .filter(s -> Objects.equals(s.getId(), sectionId))
                .findFirst()
                .orElseThrow(() -> new NoSuchElementException("존재하지 않는 섹션 id=" + sectionId));
        ParkingMapper.applySectionUpdate(target, req);
        return ParkingMapper.toZoneDTO(z);
    }

    @Override
    public ParkingZoneDTO removeSection(Long zoneId, Long sectionId) {
        ParkingZone z = zoneRepo.findById(zoneId)
                .orElseThrow(() -> new NoSuchElementException("존재하지 않는 구역 id=" + zoneId));
        ParkingSection target = z.getSections().stream()
                .filter(s -> Objects.equals(s.getId(), sectionId))
                .findFirst()
                .orElseThrow(() -> new NoSuchElementException("존재하지 않는 섹션 id=" + sectionId));
        z.removeSection(target);
        sectionRepo.delete(target);
        return ParkingMapper.toZoneDTO(z);
    }
}
