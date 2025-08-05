import { useState, useEffect } from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';

import Layout from './components/layout/Layout';
import LoginPage from './pages/auth/LoginPage';
import SignupPage from './pages/auth/SignupPage';
import Main from './pages/dashboard/MainPage';
import MapPage from './pages/dashboard/MapPage';
import SearchPage from './pages/search/SearchPage';
import ReportPage from './pages/report/ReportPage';
import AdminPage from './pages/admin/AdminPage';
import AdminRoutes from './pages/admin/AdminRoutes';

function App() {
  // 역할 상태
  const [role, setRole] = useState(null);
  // 인증 여부 상태 추가 (토큰 존재 등 기반 판단 가능)
  const [isAuthenticated, setIsAuthenticated] = useState(false);

  useEffect(() => {
    const handleAuthChange = () => {
      const userStr = localStorage.getItem('user');
      const user = userStr ? JSON.parse(userStr) : null;
      setRole(user?.role || null);
      // 예: 토큰 존재 유무로 인증 판단 (필요 시 토큰 유효성도 검사)
      setIsAuthenticated(!!localStorage.getItem('accessToken'));
    };

    handleAuthChange();

    window.addEventListener('roleChanged', handleAuthChange);
    window.addEventListener('storage', handleAuthChange);
    return () => {
      window.removeEventListener('roleChanged', handleAuthChange);
      window.removeEventListener('storage', handleAuthChange);
    };
  }, []);

  // 보호 라우트 컴포넌트
  const ProtectedRoute = ({ children }) => {
    if (!isAuthenticated) {
      // 인증 안 된 경우 로그인 페이지로 강제 이동
      return <Navigate to="/login" replace />;
    }
    return children;
  };

  // USER 권한 여부
  const isUser = role === 'USER';

  return (
    <Router>
      <Layout>
        <Routes>
          {/* 인증이 필요한 페이지는 ProtectedRoute로 감싸기 */}
          <Route
            path="/report"
            element={
              <ProtectedRoute>
                {/* USER만 접근 가능하도록 추가 제어 */}
                {isUser ? <ReportPage /> : <Navigate to="/" replace />}
              </ProtectedRoute>
            }
          />
          <Route
            path="/"
            element={
              <ProtectedRoute>
                {/* USER 아님만 접근 가능 */}
                {isUser ? <Navigate to="/report" replace /> : <Main />}
              </ProtectedRoute>
            }
          />
          <Route
            path="/search"
            element={
              <ProtectedRoute>{isUser ? <Navigate to="/report" replace /> : <SearchPage />}</ProtectedRoute>
            }
          />
          <Route
            path="/admin"
            element={
              <ProtectedRoute>{isUser ? <Navigate to="/report" replace /> : <AdminPage />}</ProtectedRoute>
            }
          />
          <Route
            path="/map"
            element={
              <ProtectedRoute>{isUser ? <Navigate to="/report" replace /> : <MapPage />}</ProtectedRoute>
            }
          />
          <Route path="/admin/*" element={<ProtectedRoute><AdminRoutes /></ProtectedRoute>} />

          {/* 인증 관련 페이지는 로그인하지 않은 사용자만 접근 가능 */}
          <Route
            path="/login"
            element={isAuthenticated ? <Navigate to={isUser ? "/report" : "/"} replace /> : <LoginPage />}
          />
          <Route
            path="/signup"
            element={isAuthenticated ? <Navigate to={isUser ? "/report" : "/"} replace /> : <SignupPage />}
          />

          {/* 정의되지 않은 경로 */}
          <Route
            path="*"
            element={
              isAuthenticated
                ? (isUser ? <Navigate to="/report" replace /> : <Navigate to="/" replace />)
                : <Navigate to="/login" replace />
            }
          />
        </Routes>
      </Layout>
    </Router>
  );
}

export default App;