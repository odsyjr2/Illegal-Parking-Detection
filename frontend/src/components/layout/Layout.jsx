// Layout.jsx
import { useState, useEffect } from 'react'
import { useLocation } from 'react-router-dom'
import NavBar from './NavBar'
import Header from './Header'
import './Layout.css'

// 사이드바 감출 경로
const HIDDEN_PATHS = ['/login', '/signup']

// 특정 경로 이동 시 자동으로 사이드바 열도록 할 경로
const AUTO_OPEN_PATHS = ['/', '/map','/search'] // <-- 원하는 경로 입력

function Layout({ children }) {
  const location = useLocation()
  const [isSidebarOpen, setIsSidebarOpen] = useState(true)

  const isSidebarHidden = HIDDEN_PATHS.includes(location.pathname)

  // 처음 로드 및 창 크기에 따라 자동 닫힘 로직
  useEffect(() => {
    const handleResize = () => {
      if (window.innerWidth < 768) {
        setIsSidebarOpen(false)
      } else {
        setIsSidebarOpen(true) // 큰 화면에서는 열어둔다
      }
    }
    handleResize()
    window.addEventListener('resize', handleResize)
    return () => window.removeEventListener('resize', handleResize)
  }, [])

  // 경로 변경 시 자동 동작
  useEffect(() => {
    if (AUTO_OPEN_PATHS.includes(location.pathname)) {
      setIsSidebarOpen(true)
    }
    if (HIDDEN_PATHS.includes(location.pathname)) {
      setIsSidebarOpen(false) // 로그인, 회원가입은 확실히 닫기
    }
  }, [location.pathname])

  return (
    <div className={`layout ${isSidebarOpen ? 'sidebar-open' : 'sidebar-closed'} ${isSidebarHidden ? 'no-sidebar' : ''}`}>
      {!isSidebarHidden && <NavBar isOpen={isSidebarOpen} toggle={() => setIsSidebarOpen(!isSidebarOpen)} />}
      <Header />
      <main className="content">
        {children}
      </main>
    </div>
  )
}
export default Layout