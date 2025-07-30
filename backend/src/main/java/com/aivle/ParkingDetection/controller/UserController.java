package com.aivle.ParkingDetection.controller;

import com.aivle.ParkingDetection.domain.User;
import com.aivle.ParkingDetection.dto.ApiResponse;
import com.aivle.ParkingDetection.dto.LoginRequestDTO;
import com.aivle.ParkingDetection.dto.UserDTO;
import com.aivle.ParkingDetection.dto.UserSignUpRequestDTO;
import com.aivle.ParkingDetection.jwt.JwtTokenProvider;
import com.aivle.ParkingDetection.security.CustomUserDetails;
import com.aivle.ParkingDetection.service.UserService;
import jakarta.servlet.http.HttpServletRequest;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.security.core.Authentication;
import org.springframework.security.core.annotation.AuthenticationPrincipal;
import org.springframework.web.bind.annotation.*;

@Slf4j
@RestController
@RequestMapping("/api/users")
public class UserController {

    private final UserService userService;
    private final JwtTokenProvider jwtTokenProvider;

    public UserController(UserService userService, JwtTokenProvider jwtTokenProvider) {
        this.userService = userService;
        this.jwtTokenProvider = jwtTokenProvider;
    }

    // ✅ 1. 회원가입
    @PostMapping("/signup")
    public ResponseEntity<ApiResponse<UserDTO>> register(
            @RequestBody UserSignUpRequestDTO request) {

        UserDTO registeredUser = userService.signUpUser(request);
        return new ResponseEntity<>(
                ApiResponse.success("회원가입 성공", registeredUser),
                HttpStatus.CREATED
        );
    }

    // ✅ 2. 로그인
    @PostMapping("/login")
    public ResponseEntity<ApiResponse<UserDTO>> login(@RequestBody LoginRequestDTO request) {
        // 사용자 인증
        Authentication authentication = userService.authenticate(request);

        // JWT 토큰 생성
        String accessToken = jwtTokenProvider.generateAccessToken(authentication);
        String refreshToken = jwtTokenProvider.generateRefreshToken(authentication);

        // CustomUserDetails에서 User 객체 추출
        CustomUserDetails userDetails = (CustomUserDetails) authentication.getPrincipal();
        User user = userDetails.getUser();  // <- 핵심 부분

        // UserDTO 생성
        UserDTO userDto = userService.convertToDtoWithTokens(user, accessToken, refreshToken);

        return ResponseEntity.ok(ApiResponse.success("로그인 성공", userDto));
    }

    // ✅ 3. 로그아웃
    @PostMapping("/logout")
    public ResponseEntity<ApiResponse<Void>> logout(
            @AuthenticationPrincipal CustomUserDetails customUserDetails,
            HttpServletRequest request) {

        log.debug("🧪 로그아웃 요청 사용자: {}", customUserDetails != null ? customUserDetails.getEmail() : "null");

        if (customUserDetails == null) {
            return new ResponseEntity<>(
                    ApiResponse.error("로그인된 사용자가 없습니다."),
                    HttpStatus.UNAUTHORIZED
            );
        }

        String accessToken = resolveToken(request);

        userService.logoutUser(customUserDetails.getUserId(), accessToken);

        return ResponseEntity.ok(ApiResponse.success("로그아웃 완료", null));
    }

    // ✅ AccessToken 추출 (Authorization 헤더에서)
    private String resolveToken(HttpServletRequest request) {
        String bearerToken = request.getHeader("Authorization");
        if (bearerToken != null && bearerToken.startsWith("Bearer ")) {
            return bearerToken.substring(7);
        }
        return null;
    }

}