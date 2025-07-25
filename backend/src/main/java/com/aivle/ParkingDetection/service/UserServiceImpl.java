package com.aivle.ParkingDetection.service;

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
import org.springframework.data.redis.core.RedisTemplate;
import org.springframework.security.authentication.UsernamePasswordAuthenticationToken;
import org.springframework.security.config.annotation.authentication.builders.AuthenticationManagerBuilder;
import org.springframework.security.core.Authentication;
import org.springframework.security.core.context.SecurityContextHolder;
import org.springframework.security.crypto.password.PasswordEncoder;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.util.StringUtils;
import org.springframework.data.redis.core.RedisTemplate;


import java.util.concurrent.TimeUnit;

@Slf4j
@Service
public class UserServiceImpl implements UserService {

    private final UserRepository userRepository;
    private final PasswordEncoder passwordEncoder;
    private final JwtTokenProvider jwtTokenProvider;
    private final AuthenticationManagerBuilder authenticationManagerBuilder;
    private final RedisTemplate<String, Object> redisTemplate;

    @Autowired
    public UserServiceImpl(UserRepository userRepository,
                           PasswordEncoder passwordEncoder,
                           JwtTokenProvider jwtTokenProvider,
                           AuthenticationManagerBuilder authenticationManagerBuilder,
                           RedisTemplate<String, Object> redisTemplate) {
        this.userRepository = userRepository;
        this.passwordEncoder = passwordEncoder;
        this.jwtTokenProvider = jwtTokenProvider;
        this.authenticationManagerBuilder = authenticationManagerBuilder;
        this.redisTemplate = redisTemplate;
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

        // User 엔티티 생성
        User newUser = User.builder()
                .name(request.getName())
                .password(encodedPassword)
                .email(request.getEmail())
                .adminCode(request.getAdminCode()) // 선택사항 필드
                .build();

        // 저장
        User savedUser = userRepository.save(newUser);

        // DTO로 변환하여 반환
        return UserDTO.builder()
                .id(savedUser.getId())
                .name(savedUser.getName())
                .email(savedUser.getEmail())
                .build();
    }

    @Override
    @Transactional
    public UserDTO loginUser(LoginRequestDTO request) {
        UsernamePasswordAuthenticationToken authToken =
                new UsernamePasswordAuthenticationToken(request.getEmail(), request.getPassword());

        Authentication authentication = authenticationManagerBuilder.getObject().authenticate(authToken);

        String accessToken = jwtTokenProvider.generateAccessToken(authentication);
        String refreshToken = jwtTokenProvider.generateRefreshToken(authentication);

        CustomUserDetails userDetails = (CustomUserDetails) authentication.getPrincipal();
        Long userId = userDetails.getUserId();

        redisTemplate.opsForValue().set("RT:" + userId, refreshToken, 7, TimeUnit.DAYS);

        return UserDTO.builder()
                .id(userId)
                .name(userDetails.getUsername())
                .email(userDetails.getEmail())
                .accessToken(accessToken)
                .refreshToken(refreshToken)
                .build();
    }

    @Override
    @Transactional
    public void logoutUser(Long userId, String accessToken) {
        String refreshTokenKey = "RT:" + userId;
        if (redisTemplate.hasKey(refreshTokenKey)) {
            redisTemplate.delete(refreshTokenKey);
        }

        if (StringUtils.hasText(accessToken) && jwtTokenProvider.validateToken(accessToken)) {
            long expiration = jwtTokenProvider.getRemainingExpiration(accessToken);
            redisTemplate.opsForValue().set(accessToken, "logout", expiration, TimeUnit.MILLISECONDS);
        }

        SecurityContextHolder.clearContext();
    }

    @Override
    public UserDTO convertToDtoWithTokens(User user, String accessToken, String refreshToken) {
        return UserDTO.builder()
                .id(user.getId())
                .name(user.getName())
                .email(user.getEmail())
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

}
