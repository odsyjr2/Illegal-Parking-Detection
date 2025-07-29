import { useState, useEffect } from 'react'
import { useLocation, useNavigate } from 'react-router-dom'
import NavBar from './NavBar'
import Header from './Header'
import './Layout.css'

// 사이드바 감출 경로
const HIDDEN_PATHS = ['/login', '/signup']

// 특정 경로 이동 시 자동으로 사이드바 열도록 할 경로
const AUTO_OPEN_PATHS = ['/', '/map', '/search']

function Layout({ children }) {
  const location = useLocation()
  const navigate = useNavigate()
  const [isSidebarOpen, setIsSidebarOpen] = useState(true)

  // role 상태 관리 (localStorage에서 읽기 + role 변경 감지 이벤트 추가 권장)
  const [role, setRole] = useState(null)

  useEffect(() => {
    const handleRoleChange = () => {
      const storedUserStr = localStorage.getItem('user')
      try {
        const storedUser = storedUserStr ? JSON.parse(storedUserStr) : null
        setRole(storedUser?.role || null)
      } catch {
        setRole(null)
      }
    }

    // 최초 호출
    handleRoleChange()

    // 이벤트 리스너 등록 (로그인/로그아웃 시 window.dispatchEvent('roleChanged')를 꼭 발생시키셔야 합니다)
    window.addEventListener('roleChanged', handleRoleChange)
    window.addEventListener('storage', handleRoleChange) // 다른 탭에서 변경 대비

    return () => {
      window.removeEventListener('roleChanged', handleRoleChange)
      window.removeEventListener('storage', handleRoleChange)
    }
  }, [])

  // 사이드바 숨김 조건
  const isSidebarHidden = HIDDEN_PATHS.includes(location.pathname) || role === 'USER'

  // 창 크기에 따른 사이드바 초기 열림 상태 조절
  useEffect(() => {
    const handleResize = () => {
      if (window.innerWidth < 768) {
        setIsSidebarOpen(false)
      } else {
        setIsSidebarOpen(true)
      }
    }

    handleResize()
    window.addEventListener('resize', handleResize)
    return () => window.removeEventListener('resize', handleResize)
  }, [])

  // 경로 변경에 따른 자동 사이드바 열림/닫힘
  useEffect(() => {
    if (AUTO_OPEN_PATHS.includes(location.pathname)) {
      setIsSidebarOpen(true)
    }
    if (HIDDEN_PATHS.includes(location.pathname)) {
      setIsSidebarOpen(false)
    }
  }, [location.pathname])

  // 로그아웃 함수
  const logout = () => {
    localStorage.removeItem('user')
    localStorage.removeItem('role')
    alert('로그아웃 되었습니다!')
    navigate('/login')
    // role 변경된 사실을 앱에 알리기 위해 이벤트 발생 (옵션)
    window.dispatchEvent(new Event('roleChanged'))
  }

  return (
    <div
      className={`layout ${isSidebarOpen ? 'sidebar-open' : 'sidebar-closed'} ${
        isSidebarHidden ? 'no-sidebar' : ''
      }`}
    >
      {/* USER일 경우 NavBar 숨기고 상단에 로그아웃 버튼만 노출 */}
      {role === 'USER' ? (
        <div
          style={{
            position: 'fixed',
            top: 10,
            left: 10,
            zIndex: 1500,
          }}
        >
          <button
            onClick={logout}
            style={{
              backgroundColor: 'transparent',
              border: 'none',
              fontSize: 15,
              color: '#ccc',
              cursor: 'pointer',
              padding: '8px 12px',
              fontWeight: 'bold',
            }}
            aria-label="로그아웃"
            title="로그아웃"
          >
            로그아웃
          </button>
        </div>
      ) : (
        // ADMIN 등은 기존대로 NavBar 노출
        !isSidebarHidden && <NavBar isOpen={isSidebarOpen} toggle={() => setIsSidebarOpen(!isSidebarOpen)} />
      )}

      <Header />
      <main className="content">{children}</main>
    </div>
  )
}

export default Layout
