# 불법주정차 단속 자동화 및 단속 경로 추천 시스템

Aivle School 05반 13조 빅 프로젝트 : 불법 주정차 적발 및 단속 경로 추천 시스템

## 📖 개요
실시간 CCTV 이미지 데이터 기반 AI 모델로 불법주정차 위치를 탐지하고, 최적의 단속 경로를 제안해 단속 업무 효율을 극대화하는 웹 서비스입니다.  
3‑Tier 아키텍처 기반으로 프론트엔드, 백엔드, 데이터베이스를 분리하여 확장성과 안정성을 강화합니다.

## 🚀 주요 기능
- **자동 탐지**: CCTV·차량 위치 데이터 연동을 통해 불법주정차를 자동 식별  
- **경로 추천**: 단속 대상 위치를 분석해 최적 경로를 계산·제시  
- **실시간 대시보드**:  
  - 지도 기반 단속 현황 시각화  
  - 단속 상태·리포트 페이지 제공  
- **사용자 기능**:  
  - 로그인/회원가입 (비밀번호 암호화)  
  - 신고 작성 & 통합검색  
- **관리자 기능**:  
  - 관리자 전용 페이지에서 단속·사용자 관리  
  - 시스템 설정 및 권한 분리  

## 🎯 요구사항 요약
- **서버구축 & 아키텍처**: 3‑Tier 소프트웨어 아키텍처 설계  
- **코드 관리**: GitHub/GitLab 기반 소스코드 저장소 운영  
- **프로젝트 관리**: 이슈 트래킹 및 진척도 모니터링  
- **보안**: 개인정보 암호화, 권한 분리  
- **성능**: AUC 0.98 이상의 탐지 정확도 목표  

## 🛠️ 기술 스택
- **프론트엔드**: React.js, Tailwind CSS  
- **백엔드**: Node.js (Express) / Python (Flask)  
- **데이터베이스**: PostgreSQL / MongoDB  
- **지도 API**: Kakao Map / Leaflet  
- **CI/CD & 배포**: Docker, GitHub Actions  

## 🔧 설치 및 실행
1. 저장소 클론  
   ```bash
   git clone https://github.com/your-org/illegal-parking-system.git
   cd illegal-parking-system
