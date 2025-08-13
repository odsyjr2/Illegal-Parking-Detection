package com.aivle.ParkingDetection.mapper;

import com.aivle.ParkingDetection.domain.ParkingSection;
import com.aivle.ParkingDetection.domain.ParkingZone;
import com.aivle.ParkingDetection.dto.ParkingSectionDTO;
import com.aivle.ParkingDetection.dto.ParkingSectionRequestDTO;
import com.aivle.ParkingDetection.dto.ParkingZoneDTO;
import com.aivle.ParkingDetection.dto.ParkingZoneRequestDTO;

import java.time.LocalTime;
import java.time.format.DateTimeFormatter;
import java.util.List;
import java.util.stream.Collectors;

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

    // Request -> Entity (create)
    public static ParkingZone toZoneEntity(ParkingZoneRequestDTO req) {
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
    public static ParkingSection toSectionEntity(ParkingSectionRequestDTO req) {
        ParkingSection s = new ParkingSection();
        s.setOrigin(req.getOrigin());
        s.setDestination(req.getDestination());
        LocalTime[] r = parseRange(req.getTime());
        s.setTimeStart(r[0]);
        s.setTimeEnd(r[1]);
        s.setParkingAllowed(Boolean.TRUE.equals(req.getParkingAllowed()));
        return s;
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
    public static void applySectionUpdate(ParkingSection s, ParkingSectionRequestDTO req) {
        if (req.getOrigin() != null) s.setOrigin(req.getOrigin());
        if (req.getDestination() != null) s.setDestination(req.getDestination());
        if (req.getTime() != null) {
            LocalTime[] r = parseRange(req.getTime());
            s.setTimeStart(r[0]); s.setTimeEnd(r[1]);
        }
        if (req.getParkingAllowed() != null) s.setParkingAllowed(req.getParkingAllowed());
    }
}