package com.aivle.ParkingDetection.dto;

public class ParkingSectionDTO {
    private Long id;
    private String origin;
    private String destination;
    private String time; // "HH:mm~HH:mm"
    private boolean parkingAllowed;

    public ParkingSectionDTO() {}
    public ParkingSectionDTO(Long id, String origin, String destination, String time, boolean parkingAllowed) {
        this.id = id; this.origin = origin; this.destination = destination; this.time = time; this.parkingAllowed = parkingAllowed;
    }

    public Long getId() { return id; }
    public String getOrigin() { return origin; }
    public String getDestination() { return destination; }
    public String getTime() { return time; }
    public boolean isParkingAllowed() { return parkingAllowed; }

    public void setId(Long id) { this.id = id; }
    public void setOrigin(String origin) { this.origin = origin; }
    public void setDestination(String destination) { this.destination = destination; }
    public void setTime(String time) { this.time = time; }
    public void setParkingAllowed(boolean parkingAllowed) { this.parkingAllowed = parkingAllowed; }
}