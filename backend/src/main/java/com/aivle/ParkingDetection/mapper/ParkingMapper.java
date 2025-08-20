package com.aivle.ParkingDetection.mapper;

import com.aivle.ParkingDetection.domain.ParkingSection;
import com.aivle.ParkingDetection.domain.ParkingZone;
import com.aivle.ParkingDetection.dto.ParkingSectionDTO;
import com.aivle.ParkingDetection.dto.ParkingSectionRequestDTO;
import com.aivle.ParkingDetection.dto.ParkingZoneDTO;
import com.aivle.ParkingDetection.dto.ParkingZoneRequestDTO;
import com.aivle.ParkingDetection.dto.GeocodingResult;
import com.aivle.ParkingDetection.service.VWorldGeocodingService;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Component;

import java.time.LocalTime;
import java.time.format.DateTimeFormatter;
import java.util.List;
import java.util.stream.Collectors;

@Slf4j
@Component
public class ParkingMapper {

    private static final DateTimeFormatter FMT = DateTimeFormatter.ofPattern("HH:mm");

    // "HH:mm~HH:mm"
    public static LocalTime[] parseRange(String range) {
        if (range == null || !range.contains("~")) {
            throw new IllegalArgumentException("시간은 'HH:mm~HH:mm' 형식이어야 합니다.");
        }
        String[] p = range.split("~");
        return new LocalTime[]{ LocalTime.parse(p[0].trim()), LocalTime.parse(p[1].trim()) };
    }
    public static String formatRange(LocalTime s, LocalTime e) {
        return s.format(FMT) + "~" + e.format(FMT);
    }

    // Entity -> DTO
    public static ParkingSectionDTO toSectionDTO(ParkingSection s) {
        return new ParkingSectionDTO(
                s.getId(),
                s.getOrigin(),
                s.getDestination(),
                formatRange(s.getTimeStart(), s.getTimeEnd()),
                s.isParkingAllowed()
        );
    }
    public static ParkingZoneDTO toZoneDTO(ParkingZone z) {
        List<ParkingSectionDTO> sectionDTOs = z.getSections().stream()
                .map(ParkingMapper::toSectionDTO)
                .collect(Collectors.toList());
        return new ParkingZoneDTO(
                z.getId(),
                z.getZoneName(),
                formatRange(z.getAllowedStart(), z.getAllowedEnd()),
                sectionDTOs
        );
    }

    private final VWorldGeocodingService vWorldGeocodingService;

    public ParkingMapper(VWorldGeocodingService vWorldGeocodingService) {
        this.vWorldGeocodingService = vWorldGeocodingService;
    }

    // Request -> Entity (create)
    public ParkingZone toZoneEntity(ParkingZoneRequestDTO req) {
        ParkingZone z = new ParkingZone();
        z.setZoneName(req.getZoneName());
        LocalTime[] r = parseRange(req.getAllowedTime());
        z.setAllowedStart(r[0]);
        z.setAllowedEnd(r[1]);
        if (req.getSections() != null) {
            for (ParkingSectionRequestDTO sreq : req.getSections()) {
                z.addSection(toSectionEntity(sreq));
            }
        }
        return z;
    }
    
    public ParkingSection toSectionEntity(ParkingSectionRequestDTO req) {
        ParkingSection s = new ParkingSection();
        s.setOrigin(req.getOrigin());
        s.setDestination(req.getDestination());
        LocalTime[] r = parseRange(req.getTime());
        s.setTimeStart(r[0]);
        s.setTimeEnd(r[1]);
        s.setParkingAllowed(Boolean.TRUE.equals(req.getParkingAllowed()));
        
        // VWorld API를 통한 지오코딩: 주소 -> GPS 좌표
        geocodeAndSetCoordinates(s, req.getOrigin(), req.getDestination());
        
        return s;
    }
    
    /**
     * 출발지/도착지 주소를 GPS 좌표로 변환하여 설정
     */
    private void geocodeAndSetCoordinates(ParkingSection section, String origin, String destination) {
        try {
            // 출발지 지오코딩
            if (origin != null && !origin.trim().isEmpty()) {
                GeocodingResult originResult = vWorldGeocodingService.geocode(origin);
                if (originResult.isSuccess()) {
                    section.setOriginLatitude(originResult.getLatitude());
                    section.setOriginLongitude(originResult.getLongitude());
                    log.debug("출발지 지오코딩 성공: {} -> ({}, {})", origin, 
                             originResult.getLatitude(), originResult.getLongitude());
                } else {
                    log.warn("출발지 지오코딩 실패: {} - {}", origin, originResult.getErrorMessage());
                }
            }
            
            // 도착지 지오코딩
            if (destination != null && !destination.trim().isEmpty()) {
                GeocodingResult destResult = vWorldGeocodingService.geocode(destination);
                if (destResult.isSuccess()) {
                    section.setDestinationLatitude(destResult.getLatitude());
                    section.setDestinationLongitude(destResult.getLongitude());
                    log.debug("도착지 지오코딩 성공: {} -> ({}, {})", destination, 
                             destResult.getLatitude(), destResult.getLongitude());
                } else {
                    log.warn("도착지 지오코딩 실패: {} - {}", destination, destResult.getErrorMessage());
                }
            }
            
        } catch (Exception e) {
            log.error("지오코딩 처리 중 오류 발생: {}", e.getMessage(), e);
        }
    }

    // Update
    public static void applyZoneUpdate(ParkingZone zone, ParkingZoneRequestDTO req) {
        if (req.getZoneName() != null) zone.setZoneName(req.getZoneName());
        if (req.getAllowedTime() != null) {
            LocalTime[] r = parseRange(req.getAllowedTime());
            zone.setAllowedStart(r[0]);
            zone.setAllowedEnd(r[1]);
        }
    }
    
    public void applySectionUpdate(ParkingSection s, ParkingSectionRequestDTO req) {
        boolean addressChanged = false;
        
        if (req.getOrigin() != null) {
            s.setOrigin(req.getOrigin());
            addressChanged = true;
        }
        if (req.getDestination() != null) {
            s.setDestination(req.getDestination());
            addressChanged = true;
        }
        if (req.getTime() != null) {
            LocalTime[] r = parseRange(req.getTime());
            s.setTimeStart(r[0]); s.setTimeEnd(r[1]);
        }
        if (req.getParkingAllowed() != null) s.setParkingAllowed(req.getParkingAllowed());
        
        // 주소가 변경된 경우 지오코딩 재수행
        if (addressChanged) {
            geocodeAndSetCoordinates(s, s.getOrigin(), s.getDestination());
        }
    }
}