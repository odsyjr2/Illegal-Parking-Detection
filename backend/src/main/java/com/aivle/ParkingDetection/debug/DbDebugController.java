package com.aivle.ParkingDetection.debug;

import com.aivle.ParkingDetection.domain.ParkingZone;
import com.aivle.ParkingDetection.repository.ParkingZoneRepository;
import lombok.RequiredArgsConstructor;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.transaction.PlatformTransactionManager;
import org.springframework.transaction.TransactionDefinition;
import org.springframework.transaction.TransactionStatus;
import org.springframework.transaction.support.DefaultTransactionDefinition;
import org.springframework.web.bind.annotation.*;

import javax.sql.DataSource;
import java.sql.Connection;
import java.time.LocalTime;
import java.util.HashMap;
import java.util.Map;
import java.util.UUID;

@RestController
@RequestMapping("/__diag")
@RequiredArgsConstructor
public class DbDebugController {

    private final DataSource dataSource;
    private final JdbcTemplate jdbcTemplate;
    private final ParkingZoneRepository zoneRepo;
    private final PlatformTransactionManager txManager;

    @Value("${spring.profiles.active:}")
    private String activeProfiles;

    @GetMapping("/whoami")
    public Map<String, Object> whoami() throws Exception {
        Map<String, Object> r = new HashMap<>();
        try (Connection c = dataSource.getConnection()) {
            r.put("activeProfiles", activeProfiles);
            r.put("jdbcUrl", c.getMetaData().getURL());
            r.put("dbProduct", c.getMetaData().getDatabaseProductName());
            r.put("dbUser", c.getMetaData().getUserName());
        }
        r.put("txManager", txManager.getClass().getName());
        return r;
    }

    @PostMapping("/test-insert")
    public Map<String, Object> testInsert() throws Exception {
        // 트랜잭션을 코드로 명시 시작 → 커밋까지 보장
        DefaultTransactionDefinition def = new DefaultTransactionDefinition();
        def.setName("diag-insert");
        def.setPropagationBehavior(TransactionDefinition.PROPAGATION_REQUIRED);
        TransactionStatus status = txManager.getTransaction(def);

        String uuid = "diag-" + UUID.randomUUID();
        ParkingZone z = new ParkingZone();
        z.setZoneName(uuid);
        z.setAllowedStart(LocalTime.of(1, 0));
        z.setAllowedEnd(LocalTime.of(2, 0));

        zoneRepo.saveAndFlush(z); // 강제 flush

        // 동일 커넥션/세션에서 곧장 확인
        Long count = jdbcTemplate.queryForObject(
                "SELECT COUNT(*) FROM parking_zone WHERE zone_name = ?",
                Long.class, uuid
        );

        Map<String, Object> r = new HashMap<>();
        r.put("insertedZoneId", z.getId());
        r.put("rowCountVisibleInTxn", count);

        txManager.commit(status); // 커밋!

        // 커밋 후 새 커넥션으로 재확인
        Long countAfter = jdbcTemplate.queryForObject(
                "SELECT COUNT(*) FROM parking_zone WHERE zone_name = ?",
                Long.class, uuid
        );
        r.put("rowCountAfterCommit", countAfter);

        try (Connection c = dataSource.getConnection()) {
            r.put("jdbcUrl", c.getMetaData().getURL());
            r.put("dbProduct", c.getMetaData().getDatabaseProductName());
        }
        return r;
    }
}
