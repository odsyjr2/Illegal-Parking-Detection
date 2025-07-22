import { Link, useLocation } from 'react-router-dom'
import { useState, useEffect } from 'react'
import './Sidebar.css'

const HIDDEN_PATHS = ['/login', '/signup']

function NavBar({ isOpen, toggle }) {
  const location = useLocation()

  if (HIDDEN_PATHS.includes(location.pathname)) return null

  const isActive = (path) => (location.pathname === path ? 'active' : '')

  // 🧑 임시 관리자 정보
  const adminInfo = {
    name: '홍길동',
    email: 'admin@example.com'
  }

  return (
    <>
      <button className="hamburger" onClick={toggle}>
        ☰
      </button>

      <div className={`sidebar ${isOpen ? 'open' : 'hidden'}`}>
        <div>
          <h2>로고</h2>

          {/* 관리자 정보 */}
          <div className="admin-info" style={{
            padding: '10px 14px',
            borderRadius: 8,
            marginBottom: 16,
            fontSize: '14px'
          }}>
            <div><strong>{adminInfo.name}</strong></div>
            <div style={{ color: '#fff' }}>{adminInfo.email}</div>
          </div>

          {/* 메뉴 목록 */}
          <nav>
            <ul>
              <li className={isActive('/')}>
                <Link to="/" onClick={toggle}>홈</Link>
              </li>
              <li className={isActive('/report')}>
                <Link to="/report" onClick={toggle}>신고</Link>
              </li>
              <li className={isActive('/map')}>
                <Link to="/map" onClick={toggle}>지도</Link>
              </li>
              <li className={isActive('/search')}>
                <Link to="/search" onClick={toggle}>검색</Link>
              </li>
              <li className={isActive('/admin')}>
                <Link to="/admin" onClick={toggle}>관리자</Link>
              </li>
            </ul>
          </nav>
        </div>

        {/* 👇 맨 아래 로그아웃 버튼 영역 */}
        <div style={{ marginTop: 'auto', paddingTop: 16 }}>
          <Link to="/login" onClick={toggle}
            style={{
              fontSize: 13,
              color: '#ccc',
              display: 'block',
              textAlign: 'center',
              padding: '8px 0',
              borderTop: '1px solid rgba(255,255,255,0.1)'
            }}
          >
            로그아웃
          </Link>
        </div>
      </div>
    </>
  )
}

export default NavBar
