**CCTV 영상 분석을 통한 불법주정차 AI 단속 플랫폼**

---

## 🧱 기술 스택

- Vite + React (JavaScript)
- React Router DOM (페이지 라우팅)
- Axios (API 통신)
- 외부 지도 API (Kakao / Naver 등)

---

## 🗂️ 폴더 구조

frontend/
├── public/                            # 정적 파일 (favicon, index.html 등)
├── src/                               # 소스 코드 루트 디렉토리
│   ├── assets/                        # 이미지, 폰트, 아이콘 등 정적 리소스 저장용
│   ├── components/                    # 공통 UI 컴포넌트 모음
│   │   ├── common/                    
│   │   └── layout/                    
│   ├── pages/                         # 각 기능(도메인)별 화면 구성
│   │   ├── auth/                      # 로그인 및 회원가입 관련 화면
│   │   │   ├── CheckModal.jsx
│   │   │   ├── EditProfileModal.jsx
│   │   │   ├── LoginPage.jsx      
│   │   │   └── SignupPage.jsx        
│   │   ├── dashboard/                 # 메인/지도 대시보드 관련 페이지
│   │   │   ├── MainPage.jsx 
│   │   │   ├── InfoPanel.jsx 
│   │   │   ├── MapPage.jsx          
│   │   │   └── DashboardPage.jsx     
│   │   ├── report/                    # 신고 및 리포트 관련 페이지 
│   │   │   └── ReportPage.jsx       
│   │   ├── admin/                     # 관리자 페이지 관련    
│   │   │   ├── AdminPage.jsx
│   │   │   ├── AdminRoutes.jsx
│   │   │   ├── CctvManagement.jsx
│   │   │   ├── ReportsPage.jsx
│   │   │   ├── ZonesManagement.jsx
│   │   │   └── UserManagement.jsx
│   │   └── search/                    # 통합 검색 기능 관련
│   │       └── SearchPage.jsx        
│   ├── App.jsx                        # 루트 컴포넌트 (라우터 포함)
│   └── main.jsx                       # 애플리케이션 진입점 (ReactDOM 렌더링)


---

## 🚀 실행 방법

# 1. 패키지 설치
npm install      # 또는 yarn install

# 2. 개발 서버 실행
npm run dev      # http://localhost:5173

