package com.aivle.ParkingDetection.dto;

public class ParkingSectionRequestDTO {
    private Long id; // 업데이트 시 존재, 생성 시 null
    private String origin;
    private String destination;
    private String time; // "HH:mm~HH:mm"
    private Boolean parkingAllowed;

    public Long getId() { return id; }
    public String getOrigin() { return origin; }
    public String getDestination() { return destination; }
    public String getTime() { return time; }
    public Boolean getParkingAllowed() { return parkingAllowed; }

    public void setId(Long id) { this.id = id; }
    public void setOrigin(String origin) { this.origin = origin; }
    public void setDestination(String destination) { this.destination = destination; }
    public void setTime(String time) { this.time = time; }
    public void setParkingAllowed(Boolean parkingAllowed) { this.parkingAllowed = parkingAllowed; }
}
