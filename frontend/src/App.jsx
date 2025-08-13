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
import RoutePage from './pages/dashboard/RoutePage'; 

function App() {
  const [role, setRole] = useState(null);
  const [isAuthenticated, setIsAuthenticated] = useState(false);

  useEffect(() => {
    const handleAuthChange = () => {
      const userStr = localStorage.getItem('user');
      const user = userStr ? JSON.parse(userStr) : null;
      setRole(user?.role || null);
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

  const isUser = role === 'USER';

  // 인증 및 역할에 따른 페이지 접근 제어 컴포넌트
  const AuthRoute = ({ children, requireUserOnly = false }) => {
    if (!isAuthenticated) {
      // 비로그인자는 로그인, 회원가입만 접근 가능
      return <Navigate to="/login" replace />;
    }
    if (!requireUserOnly && isUser) {
      // USER가 들어갈 수 없는 경로는 /report로 이동
      return <Navigate to="/report" replace />;
    }
    return children;
  };

  return (
    <Router>
      <Layout>
        <Routes>
          {/* 로그인, 회원가입은 비로그인자만 접근 가능 */}
          <Route
            path="/login"
            element={
              isAuthenticated ? (
                isUser ? (
                  <Navigate to="/report" replace />
                ) : (
                  <Navigate to="/" replace />
                )
              ) : (
                <LoginPage />
              )
            }
          />
          <Route
            path="/signup"
            element={
              isAuthenticated ? (
                isUser ? (
                  <Navigate to="/report" replace />
                ) : (
                  <Navigate to="/" replace />
                )
              ) : (
                <SignupPage />
              )
            }
          />

          {/* USER만 접근 가능한 신고 페이지 */}
          <Route
            path="/report"
            element={
              <AuthRoute requireUserOnly={true}>
                <ReportPage />
              </AuthRoute>
            }
          />

          {/* USER가 아닌 일반 회원용 페이지 (모든 페이지) */}
          <Route
            path="/"
            element={
              <AuthRoute>
                <Main />
              </AuthRoute>
            }
          />
          <Route
            path="/report"
            element={
              <AuthRoute>
                <ReportPage />
              </AuthRoute>
            }
          />
          <Route
            path="/search"
            element={
              <AuthRoute>
                <SearchPage />
              </AuthRoute>
            }
          />
          <Route
            path="/map"
            element={
              <AuthRoute>
                <MapPage />
              </AuthRoute>
            }
          />
          <Route
            path="/admin"
            element={
              <AuthRoute>
                <AdminPage />
              </AuthRoute>
            }
          />
          <Route
            path="/admin/*"
            element={
              <AuthRoute>
                <AdminRoutes />
              </AuthRoute>
            }
          />

          <Route
            path="/route"
            element={
              <AuthRoute>
                <RoutePage />
              </AuthRoute>
            }
          />

          {/* 정의되지 않은 경로 */}
          <Route
            path="*"
            element={
              isAuthenticated ? (
                isUser ? (
                  <Navigate to="/report" replace />
                ) : (
                  <Navigate to="/" replace />
                )
              ) : (
                <Navigate to="/login" replace />
              )
            }
          />
        </Routes>
      </Layout>
    </Router>
  );
}

export default App;