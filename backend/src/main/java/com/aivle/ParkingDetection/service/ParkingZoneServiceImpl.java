package com.aivle.ParkingDetection.service;

import com.aivle.ParkingDetection.domain.ParkingSection;
import com.aivle.ParkingDetection.domain.ParkingZone;
import com.aivle.ParkingDetection.dto.GeocodingResult;
import com.aivle.ParkingDetection.dto.ParkingSectionRequestDTO;
import com.aivle.ParkingDetection.dto.ParkingZoneDTO;
import com.aivle.ParkingDetection.dto.ParkingZoneRequestDTO;
import com.aivle.ParkingDetection.mapper.ParkingMapper;
import com.aivle.ParkingDetection.repository.ParkingSectionRepository;
import com.aivle.ParkingDetection.repository.ParkingZoneRepository;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.time.LocalDateTime;
import java.time.LocalTime;
import java.util.*;
import java.util.stream.Collectors;

@Slf4j
@Service
@Transactional
public class ParkingZoneServiceImpl implements ParkingZoneService {

    private final ParkingZoneRepository zoneRepo;
    private final ParkingSectionRepository sectionRepo;
    private final VWorldGeocodingService vWorldGeocodingService;

    public ParkingZoneServiceImpl(ParkingZoneRepository zoneRepo, ParkingSectionRepository sectionRepo,
                                VWorldGeocodingService vWorldGeocodingService) {
        this.zoneRepo = zoneRepo;
        this.sectionRepo = sectionRepo;
        this.vWorldGeocodingService = vWorldGeocodingService;
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
    @Transactional // readOnly=false 보장
    public ParkingZoneDTO create(ParkingZoneRequestDTO req) {
        // 0) zoneName 검증 + 트림
        String zoneName = Optional.ofNullable(req.getZoneName()).map(String::trim)
                .orElseThrow(() -> new IllegalArgumentException("zoneName은 필수입니다."));
        if (zoneName.isEmpty()) {
            throw new IllegalArgumentException("zoneName은 필수입니다.");
        }

        // 1) 같은 zoneName 있으면 재사용, 없으면 새로 생성(+즉시 INSERT)
        ParkingZone zone = zoneRepo.findTopByZoneNameOrderByIdAsc(zoneName)
                .orElseGet(() -> {
                    String at = Optional.ofNullable(req.getAllowedTime()).map(String::trim)
                            .orElseThrow(() -> new IllegalArgumentException("새 Zone을 만들 때는 allowedTime이 필요합니다. (예: 08:00~20:00)"));
                    if (at.isEmpty()) {
                        throw new IllegalArgumentException("새 Zone을 만들 때는 allowedTime이 필요합니다. (예: 08:00~20:00)");
                    }
                    var r = ParkingMapper.parseRange(at);
                    ParkingZone z = new ParkingZone();
                    z.setZoneName(zoneName);
                    z.setAllowedStart(r[0]);
                    z.setAllowedEnd(r[1]);
                    return zoneRepo.saveAndFlush(z); // ✅ 즉시 INSERT
                });

        // 2) 기존 Zone이라도 allowedTime이 비어있지 않게 들어오면 업데이트(+즉시 UPDATE)
        if (req.getAllowedTime() != null && !req.getAllowedTime().trim().isEmpty()) {
            var r = ParkingMapper.parseRange(req.getAllowedTime().trim());
            zone.setAllowedStart(r[0]);
            zone.setAllowedEnd(r[1]);
            zoneRepo.saveAndFlush(zone); // ✅ 즉시 UPDATE
        }

        // 3) 섹션 추가 (요청에 있으면) — 필수값 검증 + 즉시 INSERT
        if (req.getSections() != null && !req.getSections().isEmpty()) {
            for (var sreq : req.getSections()) {
                // 필수값 검증: 빈 문자열/누락 방지
                if (sreq.getOrigin() == null || sreq.getOrigin().isBlank()
                        || sreq.getDestination() == null || sreq.getDestination().isBlank()
                        || sreq.getTime() == null || sreq.getTime().isBlank()
                        || sreq.getParkingAllowed() == null) {
                    throw new IllegalArgumentException("section의 필수값(origin, destination, time, parkingAllowed)이 누락되었습니다.");
                }

                ParkingSection s = ParkingMapper.toSectionEntity(sreq); // 내부에서 time 파싱 검증
                s.setZone(zone);          // FK 세팅
                zone.addSection(s);       // 양방향 연결
                sectionRepo.saveAndFlush(s); // ✅ 즉시 INSERT
            }
        }

        // 4) 부모/자식 상태 동기화 보장
        zoneRepo.flush();

        return ParkingMapper.toZoneDTO(zone);
    }


//    @Override
//    @Transactional
//    public ParkingZoneDTO create(ParkingZoneRequestDTO req) {
//        if (req.getZoneName() == null)
//            throw new IllegalArgumentException("zoneName은 필수입니다.");
//
//        // 1) 같은 zoneName 있으면 그 ZONE 재사용, 없으면 새로 생성
//        ParkingZone zone = zoneRepo.findTopByZoneNameOrderByIdAsc(req.getZoneName())
//                .orElseGet(() -> {
//                    // 새 Zone 생성
//                    ParkingZone z = new ParkingZone();
//                    z.setZoneName(req.getZoneName());
//
//                    // 새로 만들 때는 allowedTime이 꼭 있어야 함
//                    if (req.getAllowedTime() == null) {
//                        throw new IllegalArgumentException("새 Zone을 만들 때는 allowedTime이 필요합니다. (예: 08:00~20:00)");
//                    }
//                    var r = ParkingMapper.parseRange(req.getAllowedTime());
//                    z.setAllowedStart(r[0]);
//                    z.setAllowedEnd(r[1]);
//                    return zoneRepo.save(z);
//                });
//
//        // 2) 기존 Zone에 대한 allowedTime이 요청에 있으면 업데이트(선택)
//        if (req.getAllowedTime() != null) {
//            var r = ParkingMapper.parseRange(req.getAllowedTime());
//            zone.setAllowedStart(r[0]);
//            zone.setAllowedEnd(r[1]);
//        }
//
//        // 3) 섹션 추가 (요청에 있으면)
//        if (req.getSections() != null) {
//            for (var sreq : req.getSections()) {
//                ParkingSection s = ParkingMapper.toSectionEntity(sreq);
//                s.setZone(zone);
//                zone.addSection(s);          // 연관관계 설정
//                sectionRepo.save(s);         // Cascade 설정에 따라 생략 가능하지만 안전하게 저장
//            }
//        }
//
//        return ParkingMapper.toZoneDTO(zone);
//    }



    @Override
    @Transactional
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
    @Transactional
    public void delete(Long id) {
        ParkingZone z = zoneRepo.findById(id)
                .orElseThrow(() -> new NoSuchElementException("존재하지 않는 구역 id=" + id));
        zoneRepo.delete(z); // 섹션은 orphanRemoval로 함께 삭제
    }

    @Override
    @Transactional
    public ParkingZoneDTO addSection(Long zoneId, ParkingSectionRequestDTO req) {
        ParkingZone z = zoneRepo.findById(zoneId)
                .orElseThrow(() -> new NoSuchElementException("존재하지 않는 구역 id=" + zoneId));

        ParkingSection s = ParkingMapper.toSectionEntity(req);

        // 양방향 연관관계 확실히 유지
        s.setZone(z);
        z.getSections().add(s);

        // ✅ 명시적으로 저장(자식 저장 보장). 또는 zoneRepo.save(z)도 가능
        sectionRepo.save(s);

        // 필요하면 즉시 flush 해서 DB 반영 확인
        // sectionRepo.flush();

        return ParkingMapper.toZoneDTO(z);
    }

    @Override
    @Transactional
    public ParkingZoneDTO updateSection(Long zoneId, Long sectionId, ParkingSectionRequestDTO req) {
        ParkingZone z = zoneRepo.findById(zoneId)
                .orElseThrow(() -> new NoSuchElementException("존재하지 않는 구역 id=" + zoneId));
        ParkingSection target = z.getSections().stream()
                .filter(s -> Objects.equals(s.getId(), sectionId))
                .findFirst()
                .orElseThrow(() -> new NoSuchElementException("존재하지 않는 섹션 id=" + sectionId));

        // 섹션-존 매칭 방지(다른 구역 섹션을 잘못 수정하는 실수 차단)
        if (!Objects.equals(target.getZone().getId(), zoneId)) {
            throw new IllegalArgumentException("섹션이 해당 구역에 속하지 않습니다. sectionId=" + sectionId);
        }

        ParkingMapper.applySectionUpdate(target, req);
        // 필요 시 명시 저장으로 디버깅 편의 ↑
        // sectionRepo.save(target);
        return ParkingMapper.toZoneDTO(z);
    }


    @Override
    @Transactional
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

    // AI INTEGRATION - NEW METHODS FOR VIOLATION VALIDATION

    @Override
    public boolean isLegalParkingAllowed(String cctvId, LocalDateTime detectionTime) {
        log.debug("Checking legal parking for CCTV: {} at time: {}", cctvId, detectionTime);

        // TODO: Implement CCTV to ParkingZone mapping
        // For now, implement basic time-based validation

        // Example business rule: No parking allowed between 7AM-9AM and 5PM-7PM (rush hours)
        LocalTime detectionTimeOnly = detectionTime.toLocalTime();
        LocalTime morningRushStart = LocalTime.of(7, 0);
        LocalTime morningRushEnd = LocalTime.of(9, 0);
        LocalTime eveningRushStart = LocalTime.of(17, 0);
        LocalTime eveningRushEnd = LocalTime.of(19, 0);

        boolean isMorningRush = !detectionTimeOnly.isBefore(morningRushStart) &&
                               detectionTimeOnly.isBefore(morningRushEnd);
        boolean isEveningRush = !detectionTimeOnly.isBefore(eveningRushStart) &&
                               detectionTimeOnly.isBefore(eveningRushEnd);

        boolean isRushHour = isMorningRush || isEveningRush;

        log.debug("CCTV {} - Rush hour parking restriction: {}", cctvId, isRushHour);
        return !isRushHour; // Parking is allowed if NOT in rush hour
    }

    @Override
    public ParkingZoneDTO findParkingZoneByCoordinates(Double latitude, Double longitude) {
        log.debug("Finding parking zone by coordinates: lat={}, lng={}", latitude, longitude);

        if (latitude == null || longitude == null) {
            log.debug("Coordinates are null, cannot find parking zone");
            return null;
        }

        // TODO: Implement geospatial queries to find parking zone by coordinates
        // This would require:
        // 1. Database support for spatial queries (PostGIS for PostgreSQL)
        // 2. Spatial data types in ParkingZone entity
        // 3. Spatial repository methods

        // For now, return null - will be implemented in production database phase
        log.debug("Geospatial query not implemented yet - returning null");
        return null;
    }

    @Override
    public boolean validateViolationByRules(String cctvId, LocalDateTime detectionTime,
                                          Double latitude, Double longitude) {
        log.info("Validating violation by rules - CCTV: {}, Time: {}, Coordinates: [{}, {}]",
                cctvId, detectionTime, latitude, longitude);

        if (latitude == null || longitude == null) {
            log.warn("GPS coordinates missing for violation validation - assuming violation");
            return true; // 좌표 없으면 기본적으로 위반으로 처리
        }

        // 1. GPS 기반 직접 매칭 (50m 반경)
        List<ParkingSection> gpsMatches = findParkingSectionsByGPS(latitude, longitude, 50.0);

        // 2. VWorld API 주소 기반 매칭
        List<ParkingSection> addressMatches = findParkingSectionsByAddress(latitude, longitude);

        // 3. 하이브리드 매칭 결과 통합
        Set<ParkingSection> allMatches = new HashSet<>();
        allMatches.addAll(gpsMatches);
        allMatches.addAll(addressMatches);

        log.debug("Parking section matches: GPS={}, Address={}, Total={}",
                 gpsMatches.size(), addressMatches.size(), allMatches.size());

        // 4. 매칭된 구역에서 시간대별 주차 규칙 확인
        boolean parkingAllowed = allMatches.stream()
            .anyMatch(section -> isParkingAllowedAtTime(section, detectionTime));

        // 5. 주차 허용이면 위반 아님 (false), 금지면 위반임 (true)
        boolean isViolation = !parkingAllowed;

        log.info("Violation validation result: coordinates=({}, {}), matches={}, allowed={}, violation={}",
                latitude, longitude, allMatches.size(), parkingAllowed, isViolation);

        return isViolation;
    }

    /**
     * GPS 좌표 기반 주차구역 매칭 (Haversine 거리 계산)
     */
    private List<ParkingSection> findParkingSectionsByGPS(Double latitude, Double longitude, Double radiusMeters) {
        // GPS 좌표가 설정된 구간만 조회 (성능 최적화)
        List<ParkingSection> sectionsWithGps = sectionRepo.findAllWithGpsCoordinates();
        List<ParkingSection> matches = new ArrayList<>();

        for (ParkingSection section : sectionsWithGps) {
            // 구간 내 포함 여부 또는 가까운 거리 확인
            if (isLocationWithinSection(latitude, longitude, section, radiusMeters)) {
                matches.add(section);
                log.debug("GPS match found: Section {} at distance within {}m", section.getId(), radiusMeters);
            }
        }

        return matches;
    }

    /**
     * VWorld API를 통한 주소 기반 매칭
     */
    private List<ParkingSection> findParkingSectionsByAddress(Double latitude, Double longitude) {
        try {
            // VWorld API로 역지오코딩
            GeocodingResult result = vWorldGeocodingService.reverseGeocode(latitude, longitude);

            if (result.isSuccess() && result.getRoadAddress() != null) {
                String roadAddress = result.getRoadAddress();
                log.debug("Reverse geocoding result: {}", roadAddress);

                // 도로명 주소 부분 매칭으로 주차구역 검색
                List<ParkingSection> matches = sectionRepo.findByOriginContainingOrDestinationContaining(
                    roadAddress, roadAddress);

                log.debug("Address-based matches found: {} for address: {}", matches.size(), roadAddress);
                return matches;
            }
        } catch (Exception e) {
            log.warn("Address-based matching failed: {}", e.getMessage());
        }

        return Collections.emptyList();
    }

    /**
     * 지점이 주차구역 내에 포함되는지 확인 (선형 보간 포함)
     */
    private boolean isLocationWithinSection(Double lat, Double lng, ParkingSection section, Double radiusMeters) {
        Double originLat = section.getOriginLatitude();
        Double originLng = section.getOriginLongitude();
        Double destLat = section.getDestinationLatitude();
        Double destLng = section.getDestinationLongitude();

        // 1. 시작점과의 거리 확인
        double distanceToOrigin = calculateHaversineDistance(lat, lng, originLat, originLng);
        if (distanceToOrigin <= radiusMeters) {
            return true;
        }

        // 2. 종료점과의 거리 확인
        double distanceToDestination = calculateHaversineDistance(lat, lng, destLat, destLng);
        if (distanceToDestination <= radiusMeters) {
            return true;
        }

        // 3. 선형 보간을 통한 구간 내 포함 여부 확인
        return isPointOnLineSegment(lat, lng, originLat, originLng, destLat, destLng, radiusMeters);
    }

    /**
     * Haversine 공식을 이용한 GPS 거리 계산 (미터 단위)
     */
    private double calculateHaversineDistance(Double lat1, Double lng1, Double lat2, Double lng2) {
        final double R = 6371000; // 지구 반지름 (미터)

        double dLat = Math.toRadians(lat2 - lat1);
        double dLng = Math.toRadians(lng2 - lng1);

        double a = Math.sin(dLat / 2) * Math.sin(dLat / 2) +
                   Math.cos(Math.toRadians(lat1)) * Math.cos(Math.toRadians(lat2)) *
                   Math.sin(dLng / 2) * Math.sin(dLng / 2);

        double c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));

        return R * c;
    }

    /**
     * 점이 선분 위에 있는지 확인 (선형 보간)
     */
    private boolean isPointOnLineSegment(Double pointLat, Double pointLng,
                                       Double startLat, Double startLng,
                                       Double endLat, Double endLng,
                                       Double toleranceMeters) {
        // 선분의 길이
        double segmentLength = calculateHaversineDistance(startLat, startLng, endLat, endLng);

        if (segmentLength < 1.0) { // 1미터 미만이면 점으로 처리
            return calculateHaversineDistance(pointLat, pointLng, startLat, startLng) <= toleranceMeters;
        }

        // 점에서 선분으로의 최단거리 계산
        // 벡터를 이용한 근사 계산
        double A = pointLat - startLat;
        double B = pointLng - startLng;
        double C = endLat - startLat;
        double D = endLng - startLng;

        double dot = A * C + B * D;
        double lenSq = C * C + D * D;

        if (lenSq < 1e-10) { // 길이가 0에 가까우면
            return calculateHaversineDistance(pointLat, pointLng, startLat, startLng) <= toleranceMeters;
        }

        double param = dot / lenSq;

        double nearestLat, nearestLng;
        if (param < 0) {
            nearestLat = startLat;
            nearestLng = startLng;
        } else if (param > 1) {
            nearestLat = endLat;
            nearestLng = endLng;
        } else {
            nearestLat = startLat + param * C;
            nearestLng = startLng + param * D;
        }

        double distance = calculateHaversineDistance(pointLat, pointLng, nearestLat, nearestLng);
        return distance <= toleranceMeters;
    }

    /**
     * 주차구역의 시간대별 주차 허용 여부 확인
     */
    private boolean isParkingAllowedAtTime(ParkingSection section, LocalDateTime detectionTime) {
        if (section.getTimeStart() == null || section.getTimeEnd() == null) {
            // 시간 제한이 없으면 항상 허용된 것으로 처리
            return true;
        }

        try {
            LocalTime startTime = section.getTimeStart();
            LocalTime endTime = section.getTimeEnd();
            LocalTime currentTime = detectionTime.toLocalTime();

            // 시간 범위 확인
            boolean isInTimeRange;
            if (endTime.isAfter(startTime)) {
                // 같은 날 범위 (예: 09:00~18:00)
                isInTimeRange = !currentTime.isBefore(startTime) && currentTime.isBefore(endTime);
            } else {
                // 자정을 넘는 범위 (예: 22:00~06:00)
                isInTimeRange = !currentTime.isBefore(startTime) || currentTime.isBefore(endTime);
            }

            // parkingAllowed 필드에 따른 허용/금지 판별
            boolean parkingAllowed = section.isParkingAllowed();
            boolean finalAllowed = parkingAllowed ? isInTimeRange : !isInTimeRange;

            log.debug("Time validation for section {}: timeRange={}~{}, current={}, inRange={}, allowed={}, result={}",
                     section.getId(), startTime, endTime, currentTime, isInTimeRange, parkingAllowed, finalAllowed);

            return finalAllowed;

        } catch (Exception e) {
            log.warn("Error validating time for section {}: {}", section.getId(), e.getMessage());
            return true; // 검증 실패시 허용으로 처리
        }
    }
}
