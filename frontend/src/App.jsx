// src/App.jsx
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom'
import Layout from './components/layout/Layout'
import LoginPage from './pages/auth/LoginPage'
import SignupPage from './pages/auth/SignupPage'
import Main from './pages/dashboard/MainPage'
import MapPage from './pages/dashboard/MapPage'
import SearchPage from './pages/search/SearchPage'
import ReportPage from './pages/report/ReportPage'
import AdminPage from './pages/admin/AdminPage'
// 필요한 페이지들 import

function App() {
  return (
    <Router>
      <Layout>
          <Routes>
            <Route path="/" element={<Main />} />
            <Route path="/search" element={<SearchPage />} />
            <Route path="/report" element={<ReportPage />} />
            <Route path="/admin" element={<AdminPage />} />
            <Route path="/map" element={<MapPage />} />
            <Route path="/login" element={<LoginPage />} />
            <Route path="/signup" element={<SignupPage />} />
            {/* 나중에 다른 페이지 추가 */}
          </Routes>
      </Layout>
    </Router>
  )
}

export default App
