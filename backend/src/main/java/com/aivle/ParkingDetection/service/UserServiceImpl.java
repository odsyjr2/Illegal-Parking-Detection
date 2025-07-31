package com.aivle.ParkingDetection.service;

import com.aivle.ParkingDetection.domain.Role;
import com.aivle.ParkingDetection.domain.User;
import com.aivle.ParkingDetection.dto.LoginRequestDTO;
import com.aivle.ParkingDetection.dto.UserDTO;
import com.aivle.ParkingDetection.dto.UserSignUpRequestDTO;
import com.aivle.ParkingDetection.exception.UserExistsException;
import com.aivle.ParkingDetection.jwt.JwtTokenProvider;
import com.aivle.ParkingDetection.repository.UserRepository;
import com.aivle.ParkingDetection.security.CustomUserDetails;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.security.authentication.BadCredentialsException;
import org.springframework.security.authentication.UsernamePasswordAuthenticationToken;
import org.springframework.security.config.annotation.authentication.builders.AuthenticationManagerBuilder;
import org.springframework.security.core.Authentication;
import org.springframework.security.core.AuthenticationException;
import org.springframework.security.core.context.SecurityContextHolder;
import org.springframework.security.crypto.password.PasswordEncoder;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.util.StringUtils;


import java.time.LocalDateTime;
import java.util.List;
import java.util.concurrent.TimeUnit;
import java.util.stream.Collectors;

@Slf4j
@Service
public class UserServiceImpl implements UserService {

    private final UserRepository userRepository;
    private final PasswordEncoder passwordEncoder;
    private final JwtTokenProvider jwtTokenProvider;
    private final AuthenticationManagerBuilder authenticationManagerBuilder;

    @Autowired
    public UserServiceImpl(UserRepository userRepository,
                           PasswordEncoder passwordEncoder,
                           JwtTokenProvider jwtTokenProvider,
                           AuthenticationManagerBuilder authenticationManagerBuilder) {
        this.userRepository = userRepository;
        this.passwordEncoder = passwordEncoder;
        this.jwtTokenProvider = jwtTokenProvider;
        this.authenticationManagerBuilder = authenticationManagerBuilder;
    }

    @Override
    @Transactional(readOnly = true)
    public List<UserDTO> getAllUsers() {
        List<User> users = userRepository.findAll();
        return users.stream()
                .map(user -> UserDTO.builder()
                        .id(user.getId())
                        .name(user.getName())
                        .email(user.getEmail())
                        .role(user.getRole())
                        .joinedAt(user.getJoinedAt())
                        .build())
                .collect(Collectors.toList());
    }


    @Override
    @Transactional
    public UserDTO signUpUser(UserSignUpRequestDTO request) {
        // 이메일 중복 체크
        if (userRepository.existsByEmail(request.getEmail())) {
            throw new UserExistsException("이미 존재하는 이메일입니다.");
        }

        // 비밀번호 암호화
        String encodedPassword = passwordEncoder.encode(request.getPassword());

        Role role;
        String adminCode = request.getAdminCode();
        if ("AAAA".equals(adminCode)) {
            role = Role.ADMIN;
        } else if ("BBBB".equals(adminCode)) {
            role = Role.INSPECTOR;
        } else {
            role = Role.USER;
        }

        // User 엔티티 생성
        User newUser = User.builder()
                .name(request.getName())
                .password(encodedPassword)
                .email(request.getEmail())
                .adminCode(request.getAdminCode()) // 선택사항 필드
                .role(role)
                .joinedAt(LocalDateTime.now())
                .build();

        // 저장
        User savedUser = userRepository.save(newUser);

        // DTO로 변환하여 반환
        return UserDTO.builder()
                .id(savedUser.getId())
                .name(savedUser.getName())
                .email(savedUser.getEmail())
                .role(savedUser.getRole())
                .joinedAt(savedUser.getJoinedAt())
                .build();
    }

    @Override
    @Transactional
    public UserDTO loginUser(LoginRequestDTO request) {
        try {
            UsernamePasswordAuthenticationToken authToken =
                    new UsernamePasswordAuthenticationToken(request.getEmail(), request.getPassword());

            Authentication authentication = authenticationManagerBuilder
                    .getObject()
                    .authenticate(authToken); // 이 시점에서 비밀번호 일치 여부 내부적으로 판단됨

            CustomUserDetails userDetails = (CustomUserDetails) authentication.getPrincipal();
            Long userId = userDetails.getUserId();

            String accessToken = jwtTokenProvider.generateAccessToken(authentication);
            String refreshToken = jwtTokenProvider.generateRefreshToken(authentication);

            return UserDTO.builder()
                    .id(userId)
                    .name(userDetails.getUsername())
                    .email(userDetails.getEmail())
                    .role(userDetails.getRole())
                    .accessToken(accessToken)
                    .refreshToken(refreshToken)
                    .build();

        } catch (AuthenticationException e) {
            log.warn("❌ 로그인 실패 - 인증 실패: {}", e.getMessage());
            throw new BadCredentialsException("로그인 실패: 이메일 또는 비밀번호가 일치하지 않습니다.");
        }
    }




    @Override
    @Transactional
    public void logoutUser(Long userId, String accessToken) {
        String refreshTokenKey = "RT:" + userId;

        if (StringUtils.hasText(accessToken) && jwtTokenProvider.validateToken(accessToken)) {
            long expiration = jwtTokenProvider.getRemainingExpiration(accessToken);
        }

        SecurityContextHolder.clearContext();
    }

    @Override
    public UserDTO convertToDtoWithTokens(User user, String accessToken, String refreshToken) {
        return UserDTO.builder()
                .id(user.getId())
                .name(user.getName())
                .email(user.getEmail())
                .role(user.getRole())
                .accessToken(accessToken)
                .refreshToken(refreshToken)
                .build();
    }

    @Override
    public Authentication authenticate(LoginRequestDTO request) {
        UsernamePasswordAuthenticationToken authToken =
                new UsernamePasswordAuthenticationToken(request.getEmail(), request.getPassword());

        return authenticationManagerBuilder.getObject().authenticate(authToken);
    }

    @Override
    public void deleteUserById(Long id) {
        User user = userRepository.findById(id)
                .orElseThrow(() -> new RuntimeException("해당 사용자를 찾을 수 없습니다."));

        if (user.getRole() == Role.ADMIN) {
            throw new IllegalArgumentException("관리자 계정은 탈퇴할 수 없습니다.");
        }

        userRepository.deleteById(id);
    }



}
