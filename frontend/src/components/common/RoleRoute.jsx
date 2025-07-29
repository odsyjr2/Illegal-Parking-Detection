import React from 'react';
import { Navigate } from 'react-router-dom';

// allowedRoles: 접속 허용 역할 배열
// fallbackPath: 접근 불가 시 이동 경로
function RoleRoute({ userRole, allowedRoles, fallbackPath = "/login", children }) {
  if (!userRole) {
    // 로그인 안 한 상태면 로그인 페이지로
    return <Navigate to="/login" replace />;
  }
  if (!allowedRoles.includes(userRole)) {
    // 권한 없는 경우 fallback 페이지로 리다이렉트
    return <Navigate to={fallbackPath} replace />;
  }
  return children;
}
export default RoleRoute;
