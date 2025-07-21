// Layout.jsx
import { useState, useEffect } from 'react'
import { useLocation } from 'react-router-dom'
import NavBar from './NavBar'
import Header from './Header'
import './Layout.css'

const HIDDEN_PATHS = ['/login', '/signup']

function Layout({ children }) {
  const location = useLocation()
  const [isSidebarOpen, setIsSidebarOpen] = useState(true)

  // 로그인/회원가입 페이지 등에서 sidebar 자동 숨기기
  const isSidebarHidden = HIDDEN_PATHS.includes(location.pathname)

  useEffect(() => {
    // 창 크기가 작아질 때 자동 닫기
    const handleResize = () => {
      if (window.innerWidth < 768) {
        setIsSidebarOpen(false)
      }
    }
    handleResize()
    window.addEventListener('resize', handleResize)
    return () => window.removeEventListener('resize', handleResize)
  }, [])

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