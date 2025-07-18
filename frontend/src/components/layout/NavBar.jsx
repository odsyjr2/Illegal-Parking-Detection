// src/components/layout/NavBar.jsx
import { Link, useLocation } from 'react-router-dom'
import './Sidebar.css' // 스타일은 따로 관리

function NavBar() {
  const location = useLocation()
  const isActive = (path) => location.pathname === path ? 'active' : ''

  return (
    <div className="sidebar">
      <h2>CCPark</h2>
      <nav>
        <ul>
          <li className={isActive('/')}>
            <Link to="/">홈</Link>
          </li>
          <li className={isActive('/report')}>
            <Link to="/report">신고</Link>
          </li>
          <li className={isActive('/dashboard')}>
            <Link to="/dashboard">지도</Link>
          </li>
          <li className={isActive('/status')}>
            <Link to="/status">현황</Link>
          </li>
          <li className={isActive('/search')}>
            <Link to="/search">검색</Link>
          </li>
          <li className={isActive('/admin')}>
            <Link to="/admin">관리자</Link>
          </li>
          <li>
            <button onClick={() => alert('로그아웃 클릭됨')}>로그아웃</button>
          </li>
        </ul>
      </nav>
    </div>
  )
}

export default NavBar
