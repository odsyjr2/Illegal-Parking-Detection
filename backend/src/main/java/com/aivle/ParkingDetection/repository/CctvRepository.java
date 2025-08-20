package com.aivle.ParkingDetection.repository;

import com.aivle.ParkingDetection.domain.Cctv;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;
import org.springframework.stereotype.Repository;

import java.util.List;
import java.util.Optional;

@Repository
public interface CctvRepository extends JpaRepository<Cctv, Long> {
    
    // Stream-related query methods for AI integration
    Optional<Cctv> findByStreamId(String streamId);
    
    List<Cctv> findByActiveTrue();
    
    List<Cctv> findByStreamSource(String streamSource);
    
    @Query("SELECT c FROM Cctv c WHERE c.streamId IS NOT NULL AND c.active = true")
    List<Cctv> findActiveStreams();
    
    // Check if stream already exists to avoid duplicates during sync
    boolean existsByStreamId(String streamId);
}
