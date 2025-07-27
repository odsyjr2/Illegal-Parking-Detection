package com.aivle.parkingdetection.controller;

import com.aivle.parkingdetection.dto.UserRequestDto;
import com.aivle.parkingdetection.dto.UserResponseDto;
import com.aivle.parkingdetection.service.UserService;
import lombok.RequiredArgsConstructor;
import org.springframework.web.bind.annotation.*;

@RestController
@RequestMapping("/api/users")
@RequiredArgsConstructor
public class UserController {

    private final UserService userService;

    @PostMapping("/register")
    public UserResponseDto register(@RequestBody UserRequestDto dto) {
        return userService.registerUser(dto);
    }

    @PostMapping("/login")
    public UserResponseDto login(@RequestBody UserRequestDto dto) {
        return userService.loginUser(dto);
    }
}
