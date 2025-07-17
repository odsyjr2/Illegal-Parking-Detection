CREATE TABLE `userInfo` (
  `id` long PRIMARY KEY AUTO_INCREMENT COMMENT '고유일련번호',
  `userName` varchar(255) COMMENT '사용자이름, 20자 이내',
  `userId` varchar(255) UNIQUE NOT NULL COMMENT '사용자아이디',
  `password` varchar(255) NOT NULL COMMENT '8자리 이상 요구 필요, 암호화 저장',
  `organization` varchar(255) COMMENT '소속 조직',
  `role` varchar(255) NOT NULL COMMENT 'user, admin',
  `createdAt` timestamp
);

CREATE TABLE `humanDetectionReports` (
  `id` long PRIMARY KEY AUTO_INCREMENT COMMENT '문서고유일련번호',
  `userID` varchar(255) NOT NULL COMMENT '사용자아이디',
  `imageURL` varchar(255) COMMENT '탐지 이미지 저장 위치; 탐지 이미지 실제 저장은 스토리지에 구성',
  `latitude` decimal COMMENT '위치 좌표 위도; 지도 및 스마트폰 GPS 연동',
  `longitude` decimal COMMENT '위치 좌표 경도; 지도 및 스마트폰 GPS 연동',
  `vehicleNumber` varchar(255) COMMENT '차량 번호, 암호화 저장',
  `reason` text COMMENT '신고 이유',
  `status` varchar(255) NOT NULL COMMENT '등록됨, 처리중, 완료됨',
  `createdAt` timestamp
);

CREATE TABLE `autoDetectionReports` (
  `id` long PRIMARY KEY AUTO_INCREMENT COMMENT '문서고유일련번호',
  `cctvId` long NOT NULL COMMENT '탐지 CCTV 고유번호',
  `imageURL` varchar(255) COMMENT '탐지 이미지 저장 위치; 탐지 이미지 실제 저장은 스토리지에 구성',
  `latitude` decimal COMMENT '탐지 (cctv) 위도',
  `longitude` decimal COMMENT '탐지 (cctv) 경도',
  `vehicleNumber` varchar(255) COMMENT 'OCR 결과 차량 번호, 암호화 저장',
  `status` varchar(255) NOT NULL COMMENT '등록됨, 처리중, 완료됨',
  `detectedBy` long COMMENT '탐지 모델 고유일련번호',
  `ocrBy` long COMMENT 'OCR 모델 or 엔진 고유일련번호',
  `createdAt` timestamp
);

CREATE TABLE `detectionModels` (
  `id` long PRIMARY KEY AUTO_INCREMENT COMMENT '탐지 모델 고유일련번호',
  `version` varchar(255) NOT NULL COMMENT 'v1.0, v1.1 등',
  `description` text COMMENT '필요한 경우 설명 입력',
  `model_url` varchar(255) COMMENT '모델 저장된 위치, 실제 저장은 스토리지에 구성',
  `createdAt` timestamp
);

CREATE TABLE `routeRecommendationModels` (
  `id` long PRIMARY KEY AUTO_INCREMENT COMMENT '경로 추천 모델 (그래프 임베딩 모델 포함) 고유일련번호',
  `version` varchar(255) NOT NULL COMMENT 'v1.0, v1.1 등',
  `description` text COMMENT '필요한 경우 설명 입력',
  `model_url` varchar(255) COMMENT '모델 저장된 위치, 실제 저장은 스토리지에 구성',
  `createdAt` timestamp
);

CREATE TABLE `OCRModels` (
  `id` long PRIMARY KEY AUTO_INCREMENT COMMENT '경로 추천 모델 (그래프 임베딩 모델 포함) 고유일련번호',
  `name` varchar(255) COMMENT 'OCR 엔진 이름',
  `version` varchar(255) NOT NULL COMMENT 'v1.0, v1.1 등',
  `description` text COMMENT '필요한 경우 설명 입력',
  `model_url` varchar(255) COMMENT 'OCR 모델 경로 또는 API 엔드포인트',
  `createdAt` timestamp
);

CREATE TABLE `cctvInfo` (
  `id` long PRIMARY KEY AUTO_INCREMENT COMMENT 'CCTV 고유번호',
  `latitude` decimal COMMENT '위치 좌표 위도',
  `longitude` decimal COMMENT '위치 좌표 경도',
  `purpose` varchar(255) COMMENT '설치 목적',
  `resolution` varchar(255) COMMENT 'cctv 화소 수',
  `isActive` boolean COMMENT '운영 상태'
);

CREATE TABLE `adminCode` (
  `code` varchar(255) PRIMARY KEY NOT NULL COMMENT '미리 저장 필요, 암호화 저장'
);

CREATE TABLE `routes` (
  `id` integer PRIMARY KEY AUTO_INCREMENT,
  `routes` json COMMENT '지도 api용 경로 정보',
  `generatedBy` long COMMENT '생성모델 ID / 탐색알고리즘 구현시 임베딩 모델 ID',
  `generatedAt` timestamp
);

CREATE TABLE `parkingZones` (
  `id` long PRIMARY KEY AUTO_INCREMENT,
  `name` varchar(255) COMMENT '도로명 or 구역명',
  `zonePolygon` json COMMENT '다각형 형태로 정의된 구역 좌표 배열 (위도/경도 쌍)',
  `latitude` decimal COMMENT '위치 좌표 위도',
  `longitude` decimal COMMENT '위치 좌표 경도',
  `isRestricted` boolean COMMENT '불법주정차 금지 구역 여부',
  `updatedAt` timestamp
);

CREATE TABLE `loginLogs` (
  `id` integer PRIMARY KEY AUTO_INCREMENT COMMENT '로그관리번호',
  `userId` integer NOT NULL COMMENT '사용자아이디',
  `loginTime` timestamp,
  `success` boolean COMMENT '로그인 성공 여부'
);

CREATE TABLE `reportLogs` (
  `id` long PRIMARY KEY AUTO_INCREMENT,
  `reportType` varchar(255) COMMENT 'human or auto 구분',
  `humanReportId` long COMMENT '수동 탐지 문서 고유 일련번호',
  `autoReportId` long COMMENT '자동 탐지 문서 고유 일련번호',
  `imageURL` varchar(255) COMMENT '로깅 시점 정보 기록용',
  `latitude` decimal COMMENT '로깅 시점 정보 기록용',
  `longitue` decimal COMMENT '로깅 시점 정보 기록용',
  `vehicleNumber` varchar(255) COMMENT '로깅 시점 정보 기록용',
  `previousStatus` varchar(255) COMMENT '변경 전 상태',
  `updatedStatus` varchar(255) COMMENT '변경 후 상태',
  `reportCreationTime` timestamp COMMENT '첫 report 생성 시점; 로깅 시점 정보 기록용',
  `updatedAt` timestamp
);

ALTER TABLE `humanDetectionReports` ADD FOREIGN KEY (`userID`) REFERENCES `userInfo` (`userId`);

ALTER TABLE `autoDetectionReports` ADD FOREIGN KEY (`cctvId`) REFERENCES `cctvInfo` (`id`);

ALTER TABLE `loginLogs` ADD FOREIGN KEY (`userId`) REFERENCES `userInfo` (`id`);

ALTER TABLE `routes` ADD FOREIGN KEY (`generatedBy`) REFERENCES `routeRecommendationModels` (`id`);

ALTER TABLE `autoDetectionReports` ADD FOREIGN KEY (`detectedBy`) REFERENCES `detectionModels` (`id`);

ALTER TABLE `autoDetectionReports` ADD FOREIGN KEY (`ocrBy`) REFERENCES `OCRModels` (`id`);

ALTER TABLE `reportLogs` ADD FOREIGN KEY (`humanReportId`) REFERENCES `humanDetectionReports` (`id`);

ALTER TABLE `reportLogs` ADD FOREIGN KEY (`autoReportId`) REFERENCES `autoDetectionReports` (`id`);
