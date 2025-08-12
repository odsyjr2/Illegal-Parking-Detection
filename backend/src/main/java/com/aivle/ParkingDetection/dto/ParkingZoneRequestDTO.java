package com.aivle.ParkingDetection.dto;

import java.util.ArrayList;
import java.util.List;

public class ParkingZoneRequestDTO {
    private String zoneName;    // 예: "관악구"
    private String allowedTime; // 예: "08:00~20:00"
    private List<ParkingSectionRequestDTO> sections = new ArrayList<>();

    public String getZoneName() { return zoneName; }
    public String getAllowedTime() { return allowedTime; }
    public List<ParkingSectionRequestDTO> getSections() { return sections; }

    public void setZoneName(String zoneName) { this.zoneName = zoneName; }
    public void setAllowedTime(String allowedTime) { this.allowedTime = allowedTime; }
    public void setSections(List<ParkingSectionRequestDTO> sections) { this.sections = sections; }
}