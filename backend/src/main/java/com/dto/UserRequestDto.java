package com.aivle.parkingdetection.dto;

import lombok.Builder;
import lombok.Data;

@Data
@Builder
public class UserRequestDto {
    private String username;
    private String password;
    private String email;  // 로그인 시에는 email 제외해도 됨
}
