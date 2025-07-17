CREATE TABLE [userInfo] (
  [id] long PRIMARY KEY IDENTITY(1, 1),
  [userName] nvarchar(255),
  [userId] nvarchar(255) UNIQUE NOT NULL,
  [password] nvarchar(255) NOT NULL,
  [organization] nvarchar(255),
  [role] nvarchar(255) NOT NULL,
  [createdAt] timestamp
)
GO

CREATE TABLE [humanDetectionReports] (
  [id] long PRIMARY KEY IDENTITY(1, 1),
  [userID] nvarchar(255) NOT NULL,
  [imageURL] nvarchar(255),
  [latitude] decimal,
  [longitude] decimal,
  [vehicleNumber] nvarchar(255),
  [reason] text,
  [status] nvarchar(255) NOT NULL,
  [createdAt] timestamp
)
GO

CREATE TABLE [autoDetectionReports] (
  [id] long PRIMARY KEY IDENTITY(1, 1),
  [cctvId] long NOT NULL,
  [imageURL] nvarchar(255),
  [latitude] decimal,
  [longitude] decimal,
  [vehicleNumber] nvarchar(255),
  [status] nvarchar(255) NOT NULL,
  [detectedBy] long,
  [ocrBy] long,
  [createdAt] timestamp
)
GO

CREATE TABLE [detectionModels] (
  [id] long PRIMARY KEY IDENTITY(1, 1),
  [version] nvarchar(255) NOT NULL,
  [description] text,
  [model_url] nvarchar(255),
  [createdAt] timestamp
)
GO

CREATE TABLE [routeRecommendationModels] (
  [id] long PRIMARY KEY IDENTITY(1, 1),
  [version] nvarchar(255) NOT NULL,
  [description] text,
  [model_url] nvarchar(255),
  [createdAt] timestamp
)
GO

CREATE TABLE [OCRModels] (
  [id] long PRIMARY KEY IDENTITY(1, 1),
  [name] nvarchar(255),
  [version] nvarchar(255) NOT NULL,
  [description] text,
  [model_url] nvarchar(255),
  [createdAt] timestamp
)
GO

CREATE TABLE [cctvInfo] (
  [id] long PRIMARY KEY IDENTITY(1, 1),
  [latitude] decimal,
  [longitude] decimal,
  [purpose] nvarchar(255),
  [resolution] nvarchar(255),
  [isActive] boolean
)
GO

CREATE TABLE [adminCode] (
  [code] nvarchar(255) PRIMARY KEY NOT NULL
)
GO

CREATE TABLE [routes] (
  [id] integer PRIMARY KEY IDENTITY(1, 1),
  [routes] json,
  [generatedBy] long,
  [generatedAt] timestamp
)
GO

CREATE TABLE [parkingZones] (
  [id] long PRIMARY KEY IDENTITY(1, 1),
  [name] nvarchar(255),
  [zonePolygon] json,
  [latitude] decimal,
  [longitude] decimal,
  [isRestricted] boolean,
  [updatedAt] timestamp
)
GO

CREATE TABLE [loginLogs] (
  [id] integer PRIMARY KEY IDENTITY(1, 1),
  [userId] integer NOT NULL,
  [loginTime] timestamp,
  [success] boolean
)
GO

CREATE TABLE [reportLogs] (
  [id] long PRIMARY KEY IDENTITY(1, 1),
  [reportType] nvarchar(255),
  [humanReportId] long,
  [autoReportId] long,
  [imageURL] nvarchar(255),
  [latitude] decimal,
  [longitue] decimal,
  [vehicleNumber] nvarchar(255),
  [previousStatus] nvarchar(255),
  [updatedStatus] nvarchar(255),
  [reportCreationTime] timestamp,
  [updatedAt] timestamp
)
GO

EXEC sp_addextendedproperty
@name = N'Column_Description',
@value = '고유일련번호',
@level0type = N'Schema', @level0name = 'dbo',
@level1type = N'Table',  @level1name = 'userInfo',
@level2type = N'Column', @level2name = 'id';
GO

EXEC sp_addextendedproperty
@name = N'Column_Description',
@value = '사용자이름, 20자 이내',
@level0type = N'Schema', @level0name = 'dbo',
@level1type = N'Table',  @level1name = 'userInfo',
@level2type = N'Column', @level2name = 'userName';
GO

EXEC sp_addextendedproperty
@name = N'Column_Description',
@value = '사용자아이디',
@level0type = N'Schema', @level0name = 'dbo',
@level1type = N'Table',  @level1name = 'userInfo',
@level2type = N'Column', @level2name = 'userId';
GO

EXEC sp_addextendedproperty
@name = N'Column_Description',
@value = '8자리 이상 요구 필요, 암호화 저장',
@level0type = N'Schema', @level0name = 'dbo',
@level1type = N'Table',  @level1name = 'userInfo',
@level2type = N'Column', @level2name = 'password';
GO

EXEC sp_addextendedproperty
@name = N'Column_Description',
@value = '소속 조직',
@level0type = N'Schema', @level0name = 'dbo',
@level1type = N'Table',  @level1name = 'userInfo',
@level2type = N'Column', @level2name = 'organization';
GO

EXEC sp_addextendedproperty
@name = N'Column_Description',
@value = 'user, admin',
@level0type = N'Schema', @level0name = 'dbo',
@level1type = N'Table',  @level1name = 'userInfo',
@level2type = N'Column', @level2name = 'role';
GO

EXEC sp_addextendedproperty
@name = N'Column_Description',
@value = '문서고유일련번호',
@level0type = N'Schema', @level0name = 'dbo',
@level1type = N'Table',  @level1name = 'humanDetectionReports',
@level2type = N'Column', @level2name = 'id';
GO

EXEC sp_addextendedproperty
@name = N'Column_Description',
@value = '사용자아이디',
@level0type = N'Schema', @level0name = 'dbo',
@level1type = N'Table',  @level1name = 'humanDetectionReports',
@level2type = N'Column', @level2name = 'userID';
GO

EXEC sp_addextendedproperty
@name = N'Column_Description',
@value = '탐지 이미지 저장 위치; 탐지 이미지 실제 저장은 스토리지에 구성',
@level0type = N'Schema', @level0name = 'dbo',
@level1type = N'Table',  @level1name = 'humanDetectionReports',
@level2type = N'Column', @level2name = 'imageURL';
GO

EXEC sp_addextendedproperty
@name = N'Column_Description',
@value = '위치 좌표 위도; 지도 및 스마트폰 GPS 연동',
@level0type = N'Schema', @level0name = 'dbo',
@level1type = N'Table',  @level1name = 'humanDetectionReports',
@level2type = N'Column', @level2name = 'latitude';
GO

EXEC sp_addextendedproperty
@name = N'Column_Description',
@value = '위치 좌표 경도; 지도 및 스마트폰 GPS 연동',
@level0type = N'Schema', @level0name = 'dbo',
@level1type = N'Table',  @level1name = 'humanDetectionReports',
@level2type = N'Column', @level2name = 'longitude';
GO

EXEC sp_addextendedproperty
@name = N'Column_Description',
@value = '차량 번호, 암호화 저장',
@level0type = N'Schema', @level0name = 'dbo',
@level1type = N'Table',  @level1name = 'humanDetectionReports',
@level2type = N'Column', @level2name = 'vehicleNumber';
GO

EXEC sp_addextendedproperty
@name = N'Column_Description',
@value = '신고 이유',
@level0type = N'Schema', @level0name = 'dbo',
@level1type = N'Table',  @level1name = 'humanDetectionReports',
@level2type = N'Column', @level2name = 'reason';
GO

EXEC sp_addextendedproperty
@name = N'Column_Description',
@value = '등록됨, 처리중, 완료됨',
@level0type = N'Schema', @level0name = 'dbo',
@level1type = N'Table',  @level1name = 'humanDetectionReports',
@level2type = N'Column', @level2name = 'status';
GO

EXEC sp_addextendedproperty
@name = N'Column_Description',
@value = '문서고유일련번호',
@level0type = N'Schema', @level0name = 'dbo',
@level1type = N'Table',  @level1name = 'autoDetectionReports',
@level2type = N'Column', @level2name = 'id';
GO

EXEC sp_addextendedproperty
@name = N'Column_Description',
@value = '탐지 CCTV 고유번호',
@level0type = N'Schema', @level0name = 'dbo',
@level1type = N'Table',  @level1name = 'autoDetectionReports',
@level2type = N'Column', @level2name = 'cctvId';
GO

EXEC sp_addextendedproperty
@name = N'Column_Description',
@value = '탐지 이미지 저장 위치; 탐지 이미지 실제 저장은 스토리지에 구성',
@level0type = N'Schema', @level0name = 'dbo',
@level1type = N'Table',  @level1name = 'autoDetectionReports',
@level2type = N'Column', @level2name = 'imageURL';
GO

EXEC sp_addextendedproperty
@name = N'Column_Description',
@value = '탐지 (cctv) 위도',
@level0type = N'Schema', @level0name = 'dbo',
@level1type = N'Table',  @level1name = 'autoDetectionReports',
@level2type = N'Column', @level2name = 'latitude';
GO

EXEC sp_addextendedproperty
@name = N'Column_Description',
@value = '탐지 (cctv) 경도',
@level0type = N'Schema', @level0name = 'dbo',
@level1type = N'Table',  @level1name = 'autoDetectionReports',
@level2type = N'Column', @level2name = 'longitude';
GO

EXEC sp_addextendedproperty
@name = N'Column_Description',
@value = 'OCR 결과 차량 번호, 암호화 저장',
@level0type = N'Schema', @level0name = 'dbo',
@level1type = N'Table',  @level1name = 'autoDetectionReports',
@level2type = N'Column', @level2name = 'vehicleNumber';
GO

EXEC sp_addextendedproperty
@name = N'Column_Description',
@value = '등록됨, 처리중, 완료됨',
@level0type = N'Schema', @level0name = 'dbo',
@level1type = N'Table',  @level1name = 'autoDetectionReports',
@level2type = N'Column', @level2name = 'status';
GO

EXEC sp_addextendedproperty
@name = N'Column_Description',
@value = '탐지 모델 고유일련번호',
@level0type = N'Schema', @level0name = 'dbo',
@level1type = N'Table',  @level1name = 'autoDetectionReports',
@level2type = N'Column', @level2name = 'detectedBy';
GO

EXEC sp_addextendedproperty
@name = N'Column_Description',
@value = 'OCR 모델 or 엔진 고유일련번호',
@level0type = N'Schema', @level0name = 'dbo',
@level1type = N'Table',  @level1name = 'autoDetectionReports',
@level2type = N'Column', @level2name = 'ocrBy';
GO

EXEC sp_addextendedproperty
@name = N'Column_Description',
@value = '탐지 모델 고유일련번호',
@level0type = N'Schema', @level0name = 'dbo',
@level1type = N'Table',  @level1name = 'detectionModels',
@level2type = N'Column', @level2name = 'id';
GO

EXEC sp_addextendedproperty
@name = N'Column_Description',
@value = 'v1.0, v1.1 등',
@level0type = N'Schema', @level0name = 'dbo',
@level1type = N'Table',  @level1name = 'detectionModels',
@level2type = N'Column', @level2name = 'version';
GO

EXEC sp_addextendedproperty
@name = N'Column_Description',
@value = '필요한 경우 설명 입력',
@level0type = N'Schema', @level0name = 'dbo',
@level1type = N'Table',  @level1name = 'detectionModels',
@level2type = N'Column', @level2name = 'description';
GO

EXEC sp_addextendedproperty
@name = N'Column_Description',
@value = '모델 저장된 위치, 실제 저장은 스토리지에 구성',
@level0type = N'Schema', @level0name = 'dbo',
@level1type = N'Table',  @level1name = 'detectionModels',
@level2type = N'Column', @level2name = 'model_url';
GO

EXEC sp_addextendedproperty
@name = N'Column_Description',
@value = '경로 추천 모델 (그래프 임베딩 모델 포함) 고유일련번호',
@level0type = N'Schema', @level0name = 'dbo',
@level1type = N'Table',  @level1name = 'routeRecommendationModels',
@level2type = N'Column', @level2name = 'id';
GO

EXEC sp_addextendedproperty
@name = N'Column_Description',
@value = 'v1.0, v1.1 등',
@level0type = N'Schema', @level0name = 'dbo',
@level1type = N'Table',  @level1name = 'routeRecommendationModels',
@level2type = N'Column', @level2name = 'version';
GO

EXEC sp_addextendedproperty
@name = N'Column_Description',
@value = '필요한 경우 설명 입력',
@level0type = N'Schema', @level0name = 'dbo',
@level1type = N'Table',  @level1name = 'routeRecommendationModels',
@level2type = N'Column', @level2name = 'description';
GO

EXEC sp_addextendedproperty
@name = N'Column_Description',
@value = '모델 저장된 위치, 실제 저장은 스토리지에 구성',
@level0type = N'Schema', @level0name = 'dbo',
@level1type = N'Table',  @level1name = 'routeRecommendationModels',
@level2type = N'Column', @level2name = 'model_url';
GO

EXEC sp_addextendedproperty
@name = N'Column_Description',
@value = '경로 추천 모델 (그래프 임베딩 모델 포함) 고유일련번호',
@level0type = N'Schema', @level0name = 'dbo',
@level1type = N'Table',  @level1name = 'OCRModels',
@level2type = N'Column', @level2name = 'id';
GO

EXEC sp_addextendedproperty
@name = N'Column_Description',
@value = 'OCR 엔진 이름',
@level0type = N'Schema', @level0name = 'dbo',
@level1type = N'Table',  @level1name = 'OCRModels',
@level2type = N'Column', @level2name = 'name';
GO

EXEC sp_addextendedproperty
@name = N'Column_Description',
@value = 'v1.0, v1.1 등',
@level0type = N'Schema', @level0name = 'dbo',
@level1type = N'Table',  @level1name = 'OCRModels',
@level2type = N'Column', @level2name = 'version';
GO

EXEC sp_addextendedproperty
@name = N'Column_Description',
@value = '필요한 경우 설명 입력',
@level0type = N'Schema', @level0name = 'dbo',
@level1type = N'Table',  @level1name = 'OCRModels',
@level2type = N'Column', @level2name = 'description';
GO

EXEC sp_addextendedproperty
@name = N'Column_Description',
@value = 'OCR 모델 경로 또는 API 엔드포인트',
@level0type = N'Schema', @level0name = 'dbo',
@level1type = N'Table',  @level1name = 'OCRModels',
@level2type = N'Column', @level2name = 'model_url';
GO

EXEC sp_addextendedproperty
@name = N'Column_Description',
@value = 'CCTV 고유번호',
@level0type = N'Schema', @level0name = 'dbo',
@level1type = N'Table',  @level1name = 'cctvInfo',
@level2type = N'Column', @level2name = 'id';
GO

EXEC sp_addextendedproperty
@name = N'Column_Description',
@value = '위치 좌표 위도',
@level0type = N'Schema', @level0name = 'dbo',
@level1type = N'Table',  @level1name = 'cctvInfo',
@level2type = N'Column', @level2name = 'latitude';
GO

EXEC sp_addextendedproperty
@name = N'Column_Description',
@value = '위치 좌표 경도',
@level0type = N'Schema', @level0name = 'dbo',
@level1type = N'Table',  @level1name = 'cctvInfo',
@level2type = N'Column', @level2name = 'longitude';
GO

EXEC sp_addextendedproperty
@name = N'Column_Description',
@value = '설치 목적',
@level0type = N'Schema', @level0name = 'dbo',
@level1type = N'Table',  @level1name = 'cctvInfo',
@level2type = N'Column', @level2name = 'purpose';
GO

EXEC sp_addextendedproperty
@name = N'Column_Description',
@value = 'cctv 화소 수',
@level0type = N'Schema', @level0name = 'dbo',
@level1type = N'Table',  @level1name = 'cctvInfo',
@level2type = N'Column', @level2name = 'resolution';
GO

EXEC sp_addextendedproperty
@name = N'Column_Description',
@value = '운영 상태',
@level0type = N'Schema', @level0name = 'dbo',
@level1type = N'Table',  @level1name = 'cctvInfo',
@level2type = N'Column', @level2name = 'isActive';
GO

EXEC sp_addextendedproperty
@name = N'Column_Description',
@value = '미리 저장 필요, 암호화 저장',
@level0type = N'Schema', @level0name = 'dbo',
@level1type = N'Table',  @level1name = 'adminCode',
@level2type = N'Column', @level2name = 'code';
GO

EXEC sp_addextendedproperty
@name = N'Column_Description',
@value = '지도 api용 경로 정보',
@level0type = N'Schema', @level0name = 'dbo',
@level1type = N'Table',  @level1name = 'routes',
@level2type = N'Column', @level2name = 'routes';
GO

EXEC sp_addextendedproperty
@name = N'Column_Description',
@value = '생성모델 ID / 탐색알고리즘 구현시 임베딩 모델 ID',
@level0type = N'Schema', @level0name = 'dbo',
@level1type = N'Table',  @level1name = 'routes',
@level2type = N'Column', @level2name = 'generatedBy';
GO

EXEC sp_addextendedproperty
@name = N'Column_Description',
@value = '도로명 or 구역명',
@level0type = N'Schema', @level0name = 'dbo',
@level1type = N'Table',  @level1name = 'parkingZones',
@level2type = N'Column', @level2name = 'name';
GO

EXEC sp_addextendedproperty
@name = N'Column_Description',
@value = '다각형 형태로 정의된 구역 좌표 배열 (위도/경도 쌍)',
@level0type = N'Schema', @level0name = 'dbo',
@level1type = N'Table',  @level1name = 'parkingZones',
@level2type = N'Column', @level2name = 'zonePolygon';
GO

EXEC sp_addextendedproperty
@name = N'Column_Description',
@value = '위치 좌표 위도',
@level0type = N'Schema', @level0name = 'dbo',
@level1type = N'Table',  @level1name = 'parkingZones',
@level2type = N'Column', @level2name = 'latitude';
GO

EXEC sp_addextendedproperty
@name = N'Column_Description',
@value = '위치 좌표 경도',
@level0type = N'Schema', @level0name = 'dbo',
@level1type = N'Table',  @level1name = 'parkingZones',
@level2type = N'Column', @level2name = 'longitude';
GO

EXEC sp_addextendedproperty
@name = N'Column_Description',
@value = '불법주정차 금지 구역 여부',
@level0type = N'Schema', @level0name = 'dbo',
@level1type = N'Table',  @level1name = 'parkingZones',
@level2type = N'Column', @level2name = 'isRestricted';
GO

EXEC sp_addextendedproperty
@name = N'Column_Description',
@value = '로그관리번호',
@level0type = N'Schema', @level0name = 'dbo',
@level1type = N'Table',  @level1name = 'loginLogs',
@level2type = N'Column', @level2name = 'id';
GO

EXEC sp_addextendedproperty
@name = N'Column_Description',
@value = '사용자아이디',
@level0type = N'Schema', @level0name = 'dbo',
@level1type = N'Table',  @level1name = 'loginLogs',
@level2type = N'Column', @level2name = 'userId';
GO

EXEC sp_addextendedproperty
@name = N'Column_Description',
@value = '로그인 성공 여부',
@level0type = N'Schema', @level0name = 'dbo',
@level1type = N'Table',  @level1name = 'loginLogs',
@level2type = N'Column', @level2name = 'success';
GO

EXEC sp_addextendedproperty
@name = N'Column_Description',
@value = 'human or auto 구분',
@level0type = N'Schema', @level0name = 'dbo',
@level1type = N'Table',  @level1name = 'reportLogs',
@level2type = N'Column', @level2name = 'reportType';
GO

EXEC sp_addextendedproperty
@name = N'Column_Description',
@value = '수동 탐지 문서 고유 일련번호',
@level0type = N'Schema', @level0name = 'dbo',
@level1type = N'Table',  @level1name = 'reportLogs',
@level2type = N'Column', @level2name = 'humanReportId';
GO

EXEC sp_addextendedproperty
@name = N'Column_Description',
@value = '자동 탐지 문서 고유 일련번호',
@level0type = N'Schema', @level0name = 'dbo',
@level1type = N'Table',  @level1name = 'reportLogs',
@level2type = N'Column', @level2name = 'autoReportId';
GO

EXEC sp_addextendedproperty
@name = N'Column_Description',
@value = '로깅 시점 정보 기록용',
@level0type = N'Schema', @level0name = 'dbo',
@level1type = N'Table',  @level1name = 'reportLogs',
@level2type = N'Column', @level2name = 'imageURL';
GO

EXEC sp_addextendedproperty
@name = N'Column_Description',
@value = '로깅 시점 정보 기록용',
@level0type = N'Schema', @level0name = 'dbo',
@level1type = N'Table',  @level1name = 'reportLogs',
@level2type = N'Column', @level2name = 'latitude';
GO

EXEC sp_addextendedproperty
@name = N'Column_Description',
@value = '로깅 시점 정보 기록용',
@level0type = N'Schema', @level0name = 'dbo',
@level1type = N'Table',  @level1name = 'reportLogs',
@level2type = N'Column', @level2name = 'longitue';
GO

EXEC sp_addextendedproperty
@name = N'Column_Description',
@value = '로깅 시점 정보 기록용',
@level0type = N'Schema', @level0name = 'dbo',
@level1type = N'Table',  @level1name = 'reportLogs',
@level2type = N'Column', @level2name = 'vehicleNumber';
GO

EXEC sp_addextendedproperty
@name = N'Column_Description',
@value = '변경 전 상태',
@level0type = N'Schema', @level0name = 'dbo',
@level1type = N'Table',  @level1name = 'reportLogs',
@level2type = N'Column', @level2name = 'previousStatus';
GO

EXEC sp_addextendedproperty
@name = N'Column_Description',
@value = '변경 후 상태',
@level0type = N'Schema', @level0name = 'dbo',
@level1type = N'Table',  @level1name = 'reportLogs',
@level2type = N'Column', @level2name = 'updatedStatus';
GO

EXEC sp_addextendedproperty
@name = N'Column_Description',
@value = '첫 report 생성 시점; 로깅 시점 정보 기록용',
@level0type = N'Schema', @level0name = 'dbo',
@level1type = N'Table',  @level1name = 'reportLogs',
@level2type = N'Column', @level2name = 'reportCreationTime';
GO

ALTER TABLE [humanDetectionReports] ADD FOREIGN KEY ([userID]) REFERENCES [userInfo] ([userId])
GO

ALTER TABLE [autoDetectionReports] ADD FOREIGN KEY ([cctvId]) REFERENCES [cctvInfo] ([id])
GO

ALTER TABLE [loginLogs] ADD FOREIGN KEY ([userId]) REFERENCES [userInfo] ([id])
GO

ALTER TABLE [routes] ADD FOREIGN KEY ([generatedBy]) REFERENCES [routeRecommendationModels] ([id])
GO

ALTER TABLE [autoDetectionReports] ADD FOREIGN KEY ([detectedBy]) REFERENCES [detectionModels] ([id])
GO

ALTER TABLE [autoDetectionReports] ADD FOREIGN KEY ([ocrBy]) REFERENCES [OCRModels] ([id])
GO

ALTER TABLE [reportLogs] ADD FOREIGN KEY ([humanReportId]) REFERENCES [humanDetectionReports] ([id])
GO

ALTER TABLE [reportLogs] ADD FOREIGN KEY ([autoReportId]) REFERENCES [autoDetectionReports] ([id])
GO
