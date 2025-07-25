package com.aivle.ParkingDetection.dto;

import lombok.Data;

@Data
public class UserSignUpRequestDTO {
    private String name;
    private String email;
    private String password;
    private String adminCode;
}
