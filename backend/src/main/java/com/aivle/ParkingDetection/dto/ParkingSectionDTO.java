package com.aivle.ParkingDetection.dto;

public class ParkingSectionDTO {
    private Long id;
    
    // 도로명 주소 필드
    private String origin;
    private String destination;
    
    // GPS 좌표 필드 - 하이브리드 매칭을 위한 추가
    private Double originLatitude;
    private Double originLongitude;
    private Double destinationLatitude;
    private Double destinationLongitude;
    
    private String time; // "HH:mm~HH:mm"
    private boolean parkingAllowed;

    public ParkingSectionDTO() {}
    
    public ParkingSectionDTO(Long id, String origin, String destination, String time, boolean parkingAllowed) {
        this.id = id; 
        this.origin = origin; 
        this.destination = destination; 
        this.time = time; 
        this.parkingAllowed = parkingAllowed;
    }
    
    // 완전한 생성자 (GPS 좌표 포함)
    public ParkingSectionDTO(Long id, String origin, String destination, 
                           Double originLatitude, Double originLongitude,
                           Double destinationLatitude, Double destinationLongitude,
                           String time, boolean parkingAllowed) {
        this.id = id;
        this.origin = origin;
        this.destination = destination;
        this.originLatitude = originLatitude;
        this.originLongitude = originLongitude;
        this.destinationLatitude = destinationLatitude;
        this.destinationLongitude = destinationLongitude;
        this.time = time;
        this.parkingAllowed = parkingAllowed;
    }

    // Getters
    public Long getId() { return id; }
    public String getOrigin() { return origin; }
    public String getDestination() { return destination; }
    public Double getOriginLatitude() { return originLatitude; }
    public Double getOriginLongitude() { return originLongitude; }
    public Double getDestinationLatitude() { return destinationLatitude; }
    public Double getDestinationLongitude() { return destinationLongitude; }
    public String getTime() { return time; }
    public boolean isParkingAllowed() { return parkingAllowed; }

    // Setters
    public void setId(Long id) { this.id = id; }
    public void setOrigin(String origin) { this.origin = origin; }
    public void setDestination(String destination) { this.destination = destination; }
    public void setOriginLatitude(Double originLatitude) { this.originLatitude = originLatitude; }
    public void setOriginLongitude(Double originLongitude) { this.originLongitude = originLongitude; }
    public void setDestinationLatitude(Double destinationLatitude) { this.destinationLatitude = destinationLatitude; }
    public void setDestinationLongitude(Double destinationLongitude) { this.destinationLongitude = destinationLongitude; }
    public void setTime(String time) { this.time = time; }
    public void setParkingAllowed(boolean parkingAllowed) { this.parkingAllowed = parkingAllowed; }
    
    /**
     * GPS 좌표가 모두 설정되어 있는지 확인
     */
    public boolean hasCompleteCoordinates() {
        return originLatitude != null && originLongitude != null &&
               destinationLatitude != null && destinationLongitude != null;
    }
}