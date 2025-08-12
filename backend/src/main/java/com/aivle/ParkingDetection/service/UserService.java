package com.aivle.ParkingDetection.service;

import com.aivle.ParkingDetection.domain.User;
import com.aivle.ParkingDetection.dto.*;
import org.springframework.security.core.Authentication;
import java.util.List;

public interface UserService {
    List<UserDTO> getAllUsers(); // 전체 회원 목록
    UserDTO signUpUser(UserSignUpRequestDTO request);
    UserDTO loginUser(LoginRequestDTO request);
    void logoutUser(Long userId, String accessToken);
    UserDTO convertToDtoWithTokens(User user, String accessToken, String refreshToken);
    Authentication authenticate(LoginRequestDTO request);
    void deleteUserById(Long id);   // 탈퇴
    void updatePassword(UpdatePasswordDTO request); // 비밀번호 변경
    void updateName(UpdateNameDTO request); // 이름 변경
    boolean emailExists(String email);  // 이메일 중복 확인
}
