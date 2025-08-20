# 불법 주정차 단속 백엔드 시스템

## 🎯 개요

이 Spring Boot 백엔드 시스템은 AI 통합, 실시간 스트림 관리 및 위반 처리와 함께 포괄적인 불법 주정차 단속 기능을 제공합니다. 이 시스템은 한국 ITS CCTV 스트림을 관리하고, AI가 감지한 위반 사항을 처리하며, 프론트엔드 애플리케이션을 위한 API를 제공하는 중앙 허브 역할을 합니다.

## 🏗️ 시스템 아키텍처

```
한국 ITS API → AI 탐색 → 백엔드 저장소 → 프론트엔드 표시
                      ↓              ↓              ↓
                 AI 모니터링 → 위반 감지 → 실시간 보고
```

### 핵심 구성 요소

1.  **스트림 관리**: 라이브 CCTV 스트림을 위한 한국 ITS API 통합
2.  **AI 통합**: 실시간 위반 감지 및 보고
3.  **비즈니스 로직**: 주차 구역 유효성 검사 및 위반 확인
4.  **데이터 영속성**: 개발용 H2 데이터베이스, 프로덕션용 PostgreSQL 준비
5.  **API 서비스**: 프론트엔드 및 AI 시스템 통신을 위한 RESTful API

## 📋 구현된 기능

### 🎥 **CCTV 스트림 관리**
- 라이브 스트림 탐색을 위한 한국 ITS API 통합
- 스트림 메타데이터 저장 및 동기화
- 수동 CCTV 등록 및 자동 스트림 탐색 지원
- 실시간 스트림 상태 모니터링

### 🤖 **AI 통합**
- 실시간 위반 감지 처리
- 번호판 인식(OCR) 통합
- 위반 심각도 점수 및 신뢰도 검증
- 다중 스트림 동시 처리 지원

### 🚗 **위반 처리**
- 비즈니스 규칙 검증 (주차 구역, 시간 제한)
- 자동 위반 확인/거부
- 증거 수집 (이미지, 좌표, 타임스탬프)
- 포괄적인 위반 보고

### 👥 **사용자 관리**
- 역할 기반 접근 제어 (USER, INSPECTOR, ADMIN)
- JWT 기반 인증 및 인가
- 사용자 프로필 관리 및 관리자 기능

### 📊 **데이터 관리**
- 포괄적인 위반 이력
- 주차 구역 및 섹션 관리
- 사람 감지 보고서 처리
- 증거 이미지를 위한 파일 저장소

## 🛠️ 기술 스택

- **프레임워크**: Spring Boot 3.5.3
- **데이터베이스**: H2 (개발), PostgreSQL-ready (프로덕션)
- **보안**: JWT 인증을 사용하는 Spring Security
- **ORM**: Hibernate를 사용하는 Spring Data JPA
- **빌드 도구**: Gradle
- **자바 버전**: 17

## 📚 API 엔드포인트

### 🎥 **CCTV 스트림 관리**

#### 모든 스트림 가져오기
```http
GET /api/cctvs
```
한국 ITS 스트림을 포함한 모든 CCTV 스트림을 반환합니다.

#### 활성 스트림만 가져오기
```http
GET /api/cctvs/active
```
프론트엔드 선택을 위해 활성 스트림만 반환합니다.

#### ID로 스트림 가져오기
```http
GET /api/cctvs/{id}
```
특정 CCTV 스트림 세부 정보를 반환합니다.

#### 스트림 ID로 스트림 가져오기
```http
GET /api/cctvs/stream/{streamId}
```
한국 ITS 스트림 식별자(예: `its_cctv_001`)로 스트림을 반환합니다.

#### 소스로 스트림 가져오기
```http
GET /api/cctvs/source/{source}
```
소스 유형(예: `korean_its_api`, `manual`)으로 필터링된 스트림을 반환합니다.

#### 스트림 동기화 (AI 시스템)
```http
POST /api/cctvs/sync
Content-Type: application/json

[
  {
    "streamId": "its_cctv_001",
    "streamName": "메인 스트리트 교차로",
    "streamUrl": "http://example.com/stream.m3u8",
    "location": "대한민국 서울",
    "latitude": 37.5665,
    "longitude": 126.9780,
    "streamSource": "korean_its_api",
    "active": true,
    "discoveredAt": "2024-01-15T10:30:00Z"
  }
]
```

### 🤖 **AI 위반 보고**

#### 위반 보고 (AI 시스템)
```http
POST /api/ai/v1/report-detection
Content-Type: application/json

{
  "event_id": "violation_its_cctv_001_1703845234",
  "event_type": "violation_detected",
  "priority": "high",
  "timestamp": 1703845234.567,
  "timestamp_iso": "2023-12-29T10:33:54.567Z",
  "stream_id": "its_cctv_001",
  "data": {
    "violation": {
      "stream_id": "its_cctv_001",
      "duration": 125.3,
      "violation_severity": 0.85,
      "is_confirmed": true,
      "vehicle_type": "car"
    },
    "license_plate": {
      "plate_text": "ABC1234",
      "confidence": 0.88,
      "is_valid_format": true
    },
    "vehicle": {
      "vehicle_type": "car",
      "confidence": 0.92,
      "last_position": [127.0, 37.5]
    }
  }
}
```

### 🚗 **탐지 관리**

#### 모든 탐지 가져오기
```http
GET /api/detections
```

#### 최근 위반 가져오기
```http
GET /api/detections/recent?hours=24
```

#### 스트림별 탐지 가져오기
```http
GET /api/detections/stream/{streamId}
```

### 👥 **사용자 관리**

#### 사용자 등록
```http
POST /api/users/signup
```

#### 사용자 로그인
```http
POST /api/users/login
```

#### 사용자 프로필 가져오기
```http
GET /api/users/profile
Authorization: Bearer {jwt_token}
```

### 🅿️ **주차 구역 관리**

#### 모든 주차 구역 가져오기
```http
GET /api/parking-zones
```

#### 주차 구역 생성
```http
POST /api/parking-zones
Authorization: Bearer {admin_jwt_token}
```

## 🗄️ 데이터베이스 스키마

### 향상된 CCTV 테이블
```sql
CREATE TABLE cctv (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    location VARCHAR(255),
    stream_url VARCHAR(255),      -- 한국 ITS 스트림 URL
    stream_id VARCHAR(255),       -- 스트림 식별자 (its_cctv_001)
    stream_name VARCHAR(255),     -- 사람이 읽을 수 있는 이름
    stream_source VARCHAR(255),   -- 소스 유형 (korean_its_api, manual)
    active BOOLEAN NOT NULL,
    latitude DOUBLE,
    longitude DOUBLE,
    installation_date DATE,       -- 수동 CCTV용
    last_updated TIMESTAMP        -- 한국 ITS 스트림용
);
```

### 탐지 테이블
```sql
CREATE TABLE detection (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    cctv_id VARCHAR(255),
    correlation_id VARCHAR(255),
    vehicle_type VARCHAR(255),
    plate_number VARCHAR(255),
    is_illegal BOOLEAN NOT NULL,
    violation_severity DOUBLE,
    detected_at TIMESTAMP,
    latitude DOUBLE,
    longitude DOUBLE,
    location VARCHAR(255),
    image_url VARCHAR(255),
    report_type VARCHAR(255)
);
```

## 🚀 시작하기

### 전제 조건
- Java 17 이상
- Gradle 7.0+
- 한국 ITS API 키 (라이브 스트림 통합용)

### 설치

1.  **리포지토리 클론**
    ```bash
    git clone <repository-url>
    cd backend
    ```

2.  **구성 설정**
    - `src/main/resources/application.yml`을 설정에 맞게 업데이트
    - AI 시스템에서 한국 ITS API 자격 증명 구성

3.  **빌드 및 실행**
    ```bash
    # 클린 빌드 및 실행
    ./gradlew clean bootRun
    
    # 또는 정리 스크립트 사용 (Windows)
    cleanup-and-run.bat
    ```

4.  **애플리케이션 접근**
    - 백엔드 API: `http://localhost:8080`
    - H2 데이터베이스 콘솔: `http://localhost:8080/h2-console`
      - JDBC URL: `jdbc:h2:mem:testdb`
      - 사용자 이름: `sa`
      - 비밀번호: (없음)

## 🧪 테스트

### 1. **백엔드 유닛 테스트**
```bash
./gradlew test
```

### 2. **AI-백엔드 통합 테스트**
```bash
cd ../AI
python test_ai_backend_integration.py --duration 60
```

이 테스트는 다음을 수행합니다:
- 한국 ITS API에서 스트림 탐색
- 백엔드 데이터베이스에 스트림 동기화
- 위반 사항에 대한 스트림 모니터링
- 백엔드에 위반 사항 보고
- 전체 통합 흐름 검증

### 3. **수동 API 테스트**

#### 스트림 동기화 테스트
```bash
curl -X GET http://localhost:8080/api/cctvs/active
```

#### 위반 보고 테스트
```bash
curl -X POST http://localhost:8080/api/ai/v1/report-detection \
  -H "Content-Type: application/json" \
  -d @test_ai_payload.json
```

### 4. **데이터베이스 검증**

H2 콘솔에 접속하여 다음을 실행합니다:
```sql
-- 동기화된 스트림 확인
SELECT * FROM CCTV WHERE STREAM_SOURCE = 'korean_its_api';

-- 위반 보고서 확인
SELECT * FROM DETECTION ORDER BY DETECTED_AT DESC;

-- 소스별 스트림 수 계산
SELECT STREAM_SOURCE, COUNT(*) FROM CCTV GROUP BY STREAM_SOURCE;
```

## 🔧 구성

### 애플리케이션 속성 (application.yml)
```yaml
spring:
  datasource:
    url: jdbc:h2:mem:testdb
    username: sa
    password:
    driver-class-name: org.h2.Driver
  
  h2:
    console:
      enabled: true
      path: /h2-console
  
  jpa:
    hibernate:
      ddl-auto: create-drop
    show-sql: true
```

### AI 통합 구성
AI 시스템 구성은 `../AI/config/`에 있습니다:
- `streams.yaml` - 한국 ITS API 설정
- `models.yaml` - AI 모델 구성
- `processing.yaml` - 성능 매개변수

## 📊 모니터링 및 유지보수

### 성능 모니터링
- H2 데이터베이스는 내장 모니터링 제공
- 애플리케이션 로그는 상세한 처리 정보 표시
- AI 통합에는 성능 메트릭 포함

### 데이터 백업
프로덕션 배포의 경우:
1. H2에서 PostgreSQL로 마이그레이션
2. 정기적인 데이터베이스 백업 구현
3. 모니터링 및 경고 설정

### 확장 고려 사항
- 로드 밸런서를 사용한 수평 확장
- 대용량을 위한 데이터베이스 최적화
- AI 처리 큐 관리

## 🔒 보안 기능

### 인증 및 인가
- JWT 기반 상태 비저장 인증
- 역할 기반 접근 제어 (RBAC)
- BCrypt를 사용한 안전한 비밀번호 해싱

### API 보안
- 프론트엔드 통합을 위한 CORS 구성
- 요청 유효성 검사 및 정제
- 정보 유출 없는 오류 처리

### 데이터 보호
- 민감한 데이터 암호화
- 규정 준수를 위한 감사 로깅
- 증거를 위한 안전한 파일 저장소

## 🐛 문제 해결

### 일반적인 문제

1.  **포트 8080 사용 중**
    ```bash
    # 정리 스크립트 사용
    cleanup-and-run.bat
    
    # 또는 포트 사용량 확인
    netstat -ano | findstr :8080
    ```

2.  **데이터베이스 연결 문제**
    - H2 콘솔 설정 확인
    - application.yml 데이터베이스 구성 확인

3.  **AI 통합 실패**
    - AI 구성에서 한국 ITS API 키 확인
    - 네트워크 연결 확인
    - AI 시스템 로그 검토

### 로그 및 디버깅
- 애플리케이션 로그: 표준 Spring Boot 로깅
- 데이터베이스 쿼리: `show-sql: true`를 통해 활성화
- AI 통합: AI 시스템의 상세 로깅

## 🤝 프론트엔드 통합 가이드

### 스트림 표시
```javascript
// 선택 가능한 스트림 가져오기
const streams = await fetch('/api/cctvs/active').then(r => r.json());

// 비디오 플레이어를 위한 특정 스트림 가져오기
const stream = await fetch(`/api/cctvs/stream/${streamId}`).then(r => r.json());

// 비디오 플레이어에서 stream.streamUrl 사용
<video src={stream.streamUrl} controls autoPlay />
```

### 위반 모니터링
```javascript
// 최근 위반 사항 폴링
const violations = await fetch('/api/detections/recent?hours=1').then(r => r.json());

// 특정 스트림에 대한 위반 팝업 표시
violations.forEach(violation => {
    if (violation.cctvId === currentStreamId) {
        showViolationAlert(violation);
    }
});
```

## 📈 향후 개선 사항

### 계획된 기능
- 실시간 알림을 위한 WebSocket 지원
- 고급 분석 및 보고
- 모바일 애플리케이션 지원
- 외부 집행 시스템과의 통합

### 성능 개선
- 자주 접근하는 데이터에 대한 Redis 캐싱
- 데이터베이스 쿼리 최적화
- 무거운 작업을 위한 비동기 처리

---

## 📞 지원

기술 지원이나 구현에 대한 질문은 다음을 확인하세요:
1. 일반적인 해결 방법은 이 README를 확인하세요
2. 오류 세부 정보는 애플리케이션 로그를 검토하세요
3. 제공된 예제를 사용하여 API 엔드포인트를 테스트하세요
4. H2 콘솔을 사용하여 데이터베이스 상태를 확인하세요

**시스템 상태**: ✅ AI 통합 및 포괄적인 위반 처리 기능을 갖춘 프로덕션 준비 완료.

```