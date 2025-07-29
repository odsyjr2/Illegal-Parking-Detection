import { useState, useEffect } from 'react'
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom'

import Layout from './components/layout/Layout'
import LoginPage from './pages/auth/LoginPage'
import SignupPage from './pages/auth/SignupPage'
import Main from './pages/dashboard/MainPage'
import MapPage from './pages/dashboard/MapPage'
import SearchPage from './pages/search/SearchPage'
import ReportPage from './pages/report/ReportPage'
import AdminPage from './pages/admin/AdminPage'
import AdminRoutes from './pages/admin/AdminRoutes'

function App() {
  const [role, setRole] = useState(null)

  useEffect(() => {
    const handleRoleChange = () => {
      try {
        const storedUserStr = localStorage.getItem('user')
        const storedUser = storedUserStr ? JSON.parse(storedUserStr) : null
        setRole(storedUser?.role || null)
      } catch {
        setRole(null)
      }
    }

    handleRoleChange()

    window.addEventListener('roleChanged', handleRoleChange)
    window.addEventListener('storage', handleRoleChange)

    return () => {
      window.removeEventListener('roleChanged', handleRoleChange)
      window.removeEventListener('storage', handleRoleChange)
    }
  }, [])

  const isUser = role === 'USER'

  return (
    <Router>
      <Layout>
        <Routes>
          {/* USER는 /report만 접근 가능 */}
          <Route path="/report" element={<ReportPage />} />

          <Route path="/" element={isUser ? <Navigate to="/report" replace /> : <Main />} />
          <Route path="/search" element={isUser ? <Navigate to="/report" replace /> : <SearchPage />} />
          <Route path="/admin" element={isUser ? <Navigate to="/report" replace /> : <AdminPage />} />
          <Route path="/map" element={isUser ? <Navigate to="/report" replace /> : <MapPage />} />
          <Route path="/admin/*" element={<AdminRoutes />} />

          {/* 인증 관련 */}
          <Route path="/login" element={<LoginPage />} />
          <Route path="/signup" element={<SignupPage />} />

          {/* 정의되지 않은 경로 */}
          <Route path="*" element={<Navigate to={isUser ? "/report" : "/"} replace />} />
        </Routes>
      </Layout>
    </Router>
  )
}

export default App
