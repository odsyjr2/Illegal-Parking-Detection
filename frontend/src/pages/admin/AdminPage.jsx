import { Outlet, NavLink } from 'react-router-dom'

function AdminPage() {
  return (
    <div style={{ maxWidth: 1200, margin: '40px auto', padding: 20 }}>
      {/* 상단 네비게이션: 모든 메뉴 한 줄에 배치 */}
      <nav
        style={{
          display: 'flex',
          gap: 12,
          marginBottom: 40,
          justifyContent: 'flex-start',
          flexWrap: 'wrap', // 화면 좁아지면 다음 줄로 이동
        }}
      >
        <NavLink
          to="/admin/users"
          style={({ isActive }) => (isActive ? { ...buttonStyle, ...activeButtonStyle } : buttonStyle)}
        >
          회원관리
        </NavLink>
        <NavLink
          to="/admin/cctv"
          style={({ isActive }) => (isActive ? { ...buttonStyle, ...activeButtonStyle } : buttonStyle)}
        >
          CCTV 관리
        </NavLink>
        <NavLink
          to="/admin/reports"
          style={({ isActive }) => (isActive ? { ...buttonStyle, ...activeButtonStyle } : buttonStyle)}
        >
          🧾 신고현황 보기
        </NavLink>
        <NavLink
          to="/admin/zones"
          style={({ isActive }) => (isActive ? { ...buttonStyle, ...activeButtonStyle } : buttonStyle)}
        >
          🕒 구역별 주정차 허용시간/구간정보 수정
        </NavLink>
      </nav>

      {/* 하위 페이지 렌더링 */}
      <main style={{ marginBottom: 40 }}>
        <Outlet />
      </main>
    </div>
  )
}

// 공통 버튼 스타일
const buttonStyle = {
  padding: '10px 24px',
  backgroundColor: '#f4f6ff',
  color: '#555',
  fontWeight: 600,
  fontSize: 16,
  borderRadius: 6,
  textDecoration: 'none',
  cursor: 'pointer',
  userSelect: 'none',
  transition: 'background-color 0.2s, color 0.2s'
}

// 활성화된 버튼 스타일
const activeButtonStyle = {
  backgroundColor: '#2e5eb8ff',
  color: '#fff',
  boxShadow: '0 2px 8px rgb(51 122 255 / 0.4)'
}

export default AdminPage
