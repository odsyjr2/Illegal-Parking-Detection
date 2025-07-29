package com.aivle.ParkingDetection.security;
import com.aivle.ParkingDetection.domain.Role;
import com.aivle.ParkingDetection.domain.User;
import lombok.Getter;
import org.springframework.security.core.GrantedAuthority;
import org.springframework.security.core.authority.SimpleGrantedAuthority;
import org.springframework.security.core.userdetails.UserDetails;

import java.util.Collection;
import java.util.Collections;
import java.util.List;
@Getter
public class CustomUserDetails implements UserDetails {

    private final User user;
    private final Collection<? extends GrantedAuthority> authorities; // ✅ 필드 추가

    public CustomUserDetails(User user, Collection<? extends GrantedAuthority> authorities) {
        this.user = user;
        this.authorities = authorities;
    }

    public Long getUserId() {
        return user.getId();
    }

    @Override
    public Collection<? extends GrantedAuthority> getAuthorities() {
        return authorities; // ✅ 필드에서 반환
    }

    public String getEmail() {
        return user.getEmail();
    }

    @Override
    public String getPassword() {
        return user.getPassword();
    }

    @Override
    public String getUsername() {
        return user.getEmail(); // ✅ 보통 이메일을 username으로 씀
    }

    public Role getRole() {
        return user.getRole();
    }

    @Override
    public boolean isAccountNonExpired() {
        return true;
    }

    @Override
    public boolean isAccountNonLocked() {
        return true;
    }

    @Override
    public boolean isCredentialsNonExpired() {
        return true;
    }

    @Override
    public boolean isEnabled() {
        return true;
    }
}