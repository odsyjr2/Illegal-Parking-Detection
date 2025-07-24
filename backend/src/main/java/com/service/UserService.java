package com.aivle.parkingdetection.service;

import com.aivle.parkingdetection.dto.UserRequestDto;
import com.aivle.parkingdetection.dto.UserResponseDto;

public interface UserService {
    UserResponseDto registerUser(UserRequestDto dto);
    UserResponseDto loginUser(UserRequestDto dto);   // 추가
}
