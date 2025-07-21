// src/components/layout/NavBar.jsx

import { Link, useLocation } from 'react-router-dom'
import { useState, useEffect } from 'react'
import './Sidebar.css'

const HIDDEN_PATHS = ['/login', '/signup'] // 이 경로들에서는 네비바와 햄버거 모두 숨김

function NavBar() {
  const location = useLocation()
  const [isSidebarOpen, setIsSidebarOpen] = useState(true)

  // 1. 경로별 초기 닫힘 상태
  useEffect(() => {
    if (['/dashboard', '/report'].includes(location.pathname)) {
      setIsSidebarOpen(false)
    }
  }, [location.pathname])

  // 2. 화면 작아질 때 자동 닫힘
  useEffect(() => {
    const handleResize = () => {
      if (window.innerWidth < 900) {
        setIsSidebarOpen(false)
      }
    }
    handleResize() // mount 시 한번 실행
    window.addEventListener('resize', handleResize)
    return () => window.removeEventListener('resize', handleResize)
  }, [])

  // 3. 로그인/회원가입 페이지에서는 사이드바와 버튼 아예 안 보이게
  if (HIDDEN_PATHS.includes(location.pathname)) {
    return null
  }

  const isActive = (path) =>
    location.pathname === path ? 'active' : ''

  return (
    <>
      {/* ☰ 햄버거 버튼 */}
      <button className="hamburger" onClick={() => setIsSidebarOpen(!isSidebarOpen)}>
        ☰
      </button>

      {/* 사이드바 */}
      <div className={`sidebar ${isSidebarOpen ? 'open' : 'hidden'}`}>
        <h2>CCPark</h2>
        <nav>
          <ul>
            <li className={isActive('/')}>
              <Link to="/" onClick={() => setIsSidebarOpen(false)}>홈</Link>
            </li>
            <li className={isActive('/report')}>
              <Link to="/report" onClick={() => setIsSidebarOpen(false)}>신고</Link>
            </li>
            <li className={isActive('/dashboard')}>
              <Link to="/dashboard" onClick={() => setIsSidebarOpen(false)}>지도</Link>
            </li>
            <li className={isActive('/status')}>
              <Link to="/status" onClick={() => setIsSidebarOpen(false)}>신고</Link>
            </li>
            <li className={isActive('/search')}>
              <Link to="/search" onClick={() => setIsSidebarOpen(false)}>검색</Link>
            </li>
            <li className={isActive('/admin')}>
              <Link to="/admin" onClick={() => setIsSidebarOpen(false)}>관리자</Link>
            </li>
            <li>
              <button onClick={() => alert('로그아웃 클릭됨')}>로그아웃</button>
            </li>
          </ul>
        </nav>
      </div>
    </>
  )
}

export default NavBar