// src/components/layout/NavBar.jsx

import { Link, useLocation } from 'react-router-dom'
import { useState, useEffect } from 'react'
import './Sidebar.css'

const HIDDEN_PATHS = ['/login', '/signup'] // 이 경로들에서는 네비바와 햄버거 모두 숨김

function NavBar({ isOpen, toggle }) {
  const location = useLocation()

  const HIDDEN_PATHS = ['/login', '/signup']
  if (HIDDEN_PATHS.includes(location.pathname)) return null

  const isActive = (path) => location.pathname === path ? 'active' : ''

  return (
    <>
      <button className="hamburger" onClick={toggle}>
        ☰
      </button>

      <div className={`sidebar ${isOpen ? 'open' : 'hidden'}`}>
        <h2>CCPark</h2>
        <nav>
          <ul>
            <li className={isActive('/')}>
              <Link to="/" onClick={toggle}>홈</Link>
            </li>
            <li className={isActive('/report')}>
              <Link to="/report" onClick={toggle}>신고</Link>
            </li>
            <li className={isActive('/dashboard')}>
              <Link to="/dashboard" onClick={toggle}>지도</Link>
            </li>
            <li className={isActive('/status')}>
              <Link to="/status" onClick={toggle}>현황</Link>
            </li>
            <li className={isActive('/search')}>
              <Link to="/search" onClick={toggle}>검색</Link>
            </li>
            <li className={isActive('/admin')}>
              <Link to="/admin" onClick={toggle}>관리자</Link>
            </li>
            <li>
              <Link to="/login" onClick={toggle}>로그아웃</Link> 
              {/* 임시로 로그인페이지로 이동할수있게함 */}
            </li>
          </ul>
        </nav>
      </div>
    </>
  )
}
export default NavBar