package com.aivle.ParkingDetection.dto;

public class ParkingSectionRequestDTO {
    private Long id; // 업데이트 시 존재, 생성 시 null
    
    // 도로명 주소 필드 (필수 - 프론트엔드에서 입력)
    private String origin;
    private String destination;
    
    // GPS 좌표 필드 (선택적 - 백엔드에서 지오코딩으로 자동 생성)
    private Double originLatitude;
    private Double originLongitude;
    private Double destinationLatitude;
    private Double destinationLongitude;
    
    private String time; // "HH:mm~HH:mm"
    private Boolean parkingAllowed;

    // Getters
    public Long getId() { return id; }
    public String getOrigin() { return origin; }
    public String getDestination() { return destination; }
    public Double getOriginLatitude() { return originLatitude; }
    public Double getOriginLongitude() { return originLongitude; }
    public Double getDestinationLatitude() { return destinationLatitude; }
    public Double getDestinationLongitude() { return destinationLongitude; }
    public String getTime() { return time; }
    public Boolean getParkingAllowed() { return parkingAllowed; }

    // Setters
    public void setId(Long id) { this.id = id; }
    public void setOrigin(String origin) { this.origin = origin; }
    public void setDestination(String destination) { this.destination = destination; }
    public void setOriginLatitude(Double originLatitude) { this.originLatitude = originLatitude; }
    public void setOriginLongitude(Double originLongitude) { this.originLongitude = originLongitude; }
    public void setDestinationLatitude(Double destinationLatitude) { this.destinationLatitude = destinationLatitude; }
    public void setDestinationLongitude(Double destinationLongitude) { this.destinationLongitude = destinationLongitude; }
    public void setTime(String time) { this.time = time; }
    public void setParkingAllowed(Boolean parkingAllowed) { this.parkingAllowed = parkingAllowed; }
    
    /**
     * 필수 주소 필드가 설정되어 있는지 확인
     */
    public boolean hasRequiredAddresses() {
        return origin != null && !origin.trim().isEmpty() &&
               destination != null && !destination.trim().isEmpty();
    }
    
    /**
     * GPS 좌표가 프론트엔드에서 제공되었는지 확인
     */
    public boolean hasProvidedCoordinates() {
        return originLatitude != null && originLongitude != null &&
               destinationLatitude != null && destinationLongitude != null;
    }
}
