package com.aivle.ParkingDetection.service;

import com.aivle.ParkingDetection.domain.User;
import com.aivle.ParkingDetection.dto.LoginRequestDTO;
import com.aivle.ParkingDetection.dto.UserDTO;
import com.aivle.ParkingDetection.dto.UserSignUpRequestDTO;
import org.springframework.security.core.Authentication;

public interface UserService {
    UserDTO signUpUser(UserSignUpRequestDTO request);
    UserDTO loginUser(LoginRequestDTO request);
    void logoutUser(Long userId, String accessToken);
    UserDTO convertToDtoWithTokens(User user, String accessToken, String refreshToken);
    Authentication authenticate(LoginRequestDTO request);
    void deleteUserById(Long id);   // 탈퇴

}
