// src/components/layout/Header.jsx
import { Link } from "react-router-dom";
const headerStyle = {
  position: 'fixed',         // 항상 상단 고정
  top: 0,
  left: 0,
  right: 0,
  height: '80px',
  backgroundColor: '#1C3D90', // 어두운 배경 (원하는 색상으로 변경 가능)
  display: 'flex',
  alignItems: 'center',
  justifyContent: 'flex-end',
  padding: '0 1.5rem',
  boxShadow: '0 1px 5px rgba(0, 0, 0, 0.2)',
  zIndex: 1200
};

const logoStyle = {
  color: 'white',
  fontSize: '1.25rem',
  fontWeight: 'bold',
  textDecoration: 'none',
};

function Header() {
  return (
    <header style={headerStyle}>
      <Link to="/" style={logoStyle}>
        <img src="/logo.png" alt="로고" style={{ width: 100, height: 'auto' }} />
      </Link>
    </header>
  );
}

export default Header;
