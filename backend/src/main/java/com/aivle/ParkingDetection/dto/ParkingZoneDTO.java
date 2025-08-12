package com.aivle.ParkingDetection.dto;

import java.util.ArrayList;
import java.util.List;

public class ParkingZoneDTO {
    private Long id;
    private String zoneName;
    private String allowedTime; // "HH:mm~HH:mm"
    private List<ParkingSectionDTO> sections = new ArrayList<>();

    public ParkingZoneDTO() {}
    public ParkingZoneDTO(Long id, String zoneName, String allowedTime, List<ParkingSectionDTO> sections) {
        this.id = id; this.zoneName = zoneName; this.allowedTime = allowedTime; this.sections = sections;
    }

    public Long getId() { return id; }
    public String getZoneName() { return zoneName; }
    public String getAllowedTime() { return allowedTime; }
    public List<ParkingSectionDTO> getSections() { return sections; }

    public void setId(Long id) { this.id = id; }
    public void setZoneName(String zoneName) { this.zoneName = zoneName; }
    public void setAllowedTime(String allowedTime) { this.allowedTime = allowedTime; }
    public void setSections(List<ParkingSectionDTO> sections) { this.sections = sections; }
}