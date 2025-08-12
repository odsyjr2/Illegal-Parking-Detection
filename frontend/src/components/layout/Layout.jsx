import { useState, useEffect } from 'react'
import { useLocation, useNavigate } from 'react-router-dom'
import NavBar from './NavBar'
import Header from './Header'
import EditProfileModal from '../../pages/auth/EditProfileModal';
import './Layout.css'

const HIDDEN_PATHS = ['/login', '/signup']
const AUTO_OPEN_PATHS = ['/', '/map', '/search']

function Layout({ children }) {
  const location = useLocation()
  const navigate = useNavigate()
  const [isSidebarOpen, setIsSidebarOpen] = useState(true)

  const [role, setRole] = useState(null)

  const [isModalOpen, setModalOpen] = useState(false)

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

    handleRoleChange()

    window.addEventListener('roleChanged', handleRoleChange)
    window.addEventListener('storage', handleRoleChange)

    return () => {
      window.removeEventListener('roleChanged', handleRoleChange)
      window.removeEventListener('storage', handleRoleChange)
    }
  }, [])

  const isSidebarHidden = HIDDEN_PATHS.includes(location.pathname) || role === 'USER'

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

  useEffect(() => {
    if (AUTO_OPEN_PATHS.includes(location.pathname)) {
      setIsSidebarOpen(true)
    }
    if (HIDDEN_PATHS.includes(location.pathname)) {
      setIsSidebarOpen(false)
    }
  }, [location.pathname])

  const logout = () => {
    localStorage.removeItem('user')
    localStorage.removeItem('role')
    localStorage.removeItem('accessToken')
    localStorage.removeItem('refreshToken')
    alert('로그아웃 되었습니다!')
    navigate('/login')
    window.dispatchEvent(new Event('roleChanged'))
  }

  return (
    <div
      className={`layout ${isSidebarOpen ? 'sidebar-open' : 'sidebar-closed'} ${
        isSidebarHidden ? 'no-sidebar' : ''
      }`}
    >
      {role === 'USER' ? (
        <div
          style={{
            position: 'fixed',
            top: 13,
            left: 10,
            right: 10,
            zIndex: 1500,
            display: 'flex',
            justifyContent: 'flex-start',
            gap: 12,
            padding: '8px 16px',
            borderRadius: 8,
            color: 'white',
            fontWeight: 'bold',
          }}
        >
          <button
            onClick={() => setModalOpen(true)}
            style={{
              backgroundColor: 'transparent',
              border: '1px solid white',
              borderRadius: 4,
              color: 'white',
              cursor: 'pointer',
              padding: '8px 20px',
            }}
            aria-label="정보 변경"
            title="정보 변경"
          >
            정보 변경
          </button>

          <button
            onClick={logout}
            style={{
              backgroundColor: 'transparent',
              border: '1px solid white',
              borderRadius: 4,
              color: 'white',
              cursor: 'pointer',
              padding: '8px 20px',
            }}
            aria-label="로그아웃"
            title="로그아웃"
          >
            로그아웃
          </button>
        </div>
      ) : (
        !isSidebarHidden && (
          <NavBar isOpen={isSidebarOpen} toggle={() => setIsSidebarOpen(!isSidebarOpen)} />
        )
      )}

      <Header />
      <main className="content">{children}</main>

      <EditProfileModal isOpen={isModalOpen} onClose={() => setModalOpen(false)} />
    </div>
  )
}

export default Layout