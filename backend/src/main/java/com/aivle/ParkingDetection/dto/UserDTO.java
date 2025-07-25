package com.aivle.ParkingDetection.dto;

import com.aivle.ParkingDetection.domain.User;
import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

@Data
@NoArgsConstructor
@AllArgsConstructor
@Builder
public class UserDTO {
    private Long id;
    private String name;
    private String email;
    private String password;
    private String adminCode;

    // 사용자가 로그인에 성공하면 서버가 발급하는 JWT
    // accessToken을 통해 로그인 상태 유지, API 요청 보내기 가능
    // 짧은 유효 시간
    private String accessToken;
    // accessToken이 만료되었을 때 새로운 accessToken을 발급받기 위한 갱신용 토큰
    // 긴 유효 시간
    private String refreshToken;

    public static UserDTO from(User user) {
        return UserDTO.builder()
                .id(user.getId())
                .email(user.getEmail())
                .name(user.getName())
                .adminCode(user.getAdminCode()) // optional
                .build();
    }
}
