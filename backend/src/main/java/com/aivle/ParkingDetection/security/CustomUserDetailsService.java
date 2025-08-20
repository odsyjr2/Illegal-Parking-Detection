package com.aivle.ParkingDetection.security;

import com.aivle.ParkingDetection.domain.User;
import com.aivle.ParkingDetection.repository.UserRepository;
import lombok.RequiredArgsConstructor;
import org.springframework.security.core.GrantedAuthority;
import org.springframework.security.core.authority.SimpleGrantedAuthority;
import org.springframework.security.core.userdetails.UserDetails;
import org.springframework.security.core.userdetails.UserDetailsService;
import org.springframework.security.core.userdetails.UsernameNotFoundException;
import org.springframework.stereotype.Service;

import java.util.List;

@Service
@RequiredArgsConstructor
public class CustomUserDetailsService implements UserDetailsService {

    private final UserRepository userRepository;

    @Override
    public UserDetails loadUserByUsername(String email) throws UsernameNotFoundException {
        User user = userRepository.findByEmail(email)
                .orElseThrow(() -> new UsernameNotFoundException("해당 사용자를 찾을 수 없습니다."));

        List<GrantedAuthority> authorities =
                List.of(new SimpleGrantedAuthority("ROLE_" + user.getRole().name()));  // "ROLE_ADMIN"

        return new CustomUserDetails(user, authorities); // ✅ 수정됨
    }

}
