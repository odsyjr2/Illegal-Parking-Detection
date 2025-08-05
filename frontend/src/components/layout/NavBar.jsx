import { Link, useLocation, useNavigate } from 'react-router-dom';
import { useState, useEffect } from 'react';
import PasswordChangeModal from '../../pages/auth/EditProfileModal';
import './Sidebar.css';

const HIDDEN_PATHS = ['/login', '/signup'];

function NavBar({ isOpen, toggle }) {
  const location = useLocation();
  const navigate = useNavigate();

  const [user, setUser] = useState(null);
  const [isModalOpen, setModalOpen] = useState(false);

  useEffect(() => {
    const handleUserChange = () => {
      try {
        const storedUser = JSON.parse(localStorage.getItem('user'));
        setUser(storedUser || null);
      } catch {
        setUser(null);
      }
    };

    handleUserChange();

    window.addEventListener('roleChanged', handleUserChange);  // 이벤트 리스너 등록

    return () => {
      window.removeEventListener('roleChanged', handleUserChange);  // 이벤트 리스너 해제
    };
  }, []); // 의존성 빈 배열로 컴포넌트 마운트 시 1회 등록

  if (HIDDEN_PATHS.includes(location.pathname)) return null;

  const adminInfo = user
    ? { name: user.name || '이름없음', email: user.email || '이메일없음' }
    : { name: '홍길동', email: 'admin@example.com' };

  const logout = () => {
    localStorage.removeItem('user');
    localStorage.removeItem('role');
    localStorage.removeItem('accessToken');
    localStorage.removeItem('refreshToken');
    window.dispatchEvent(new Event('roleChanged'));
    alert('로그아웃 되었습니다!');
    navigate('/login');
  };

  const isActive = (path) => (location.pathname === path ? 'active' : '');

  return (
    <>
      <button className="hamburger" onClick={toggle} aria-label="메뉴 열기" title="메뉴">
        ☰
      </button>
      <div className={`sidebar ${isOpen ? 'open' : 'hidden'}`}>
        <div>
          <h2>로고</h2>
          <div
            className="admin-info"
            style={{
              padding: '10px 14px',
              borderRadius: 8,
              marginBottom: 16,
              fontSize: '14px',
            }}
          >
            <div>
              <strong>{adminInfo.name}</strong>
            </div>
            <div style={{ color: '#fff' }}>{adminInfo.email}</div>
          </div>

          <nav>
            <ul>
              <li className={isActive('/')}>
                <Link to="/" onClick={toggle}>
                  홈
                </Link>
              </li>
              <li className={isActive('/report')}>
                <Link to="/report" onClick={toggle}>
                  신고
                </Link>
              </li>
              <li className={isActive('/map')}>
                <Link to="/map" onClick={toggle}>
                  지도
                </Link>
              </li>
              <li className={isActive('/search')}>
                <Link to="/search" onClick={toggle}>
                  검색
                </Link>
              </li>
              <li className={isActive('/admin')}>
                <Link to="/admin" onClick={toggle}>
                  관리자
                </Link>
              </li>
            </ul>
          </nav>
        </div>

        <div style={{ marginTop: 'auto', paddingTop: 16 }}>
          <button
            onClick={() => setModalOpen(true)}
            style={{
              background: 'none',
              border: 'none',
              fontSize: 13,
              color: '#ccc',
              display: 'block',
              textAlign: 'center',
              padding: '8px 0',
              borderTop: '1px solid rgba(255,255,255,0.1)',
              width: '100%',
              cursor: 'pointer',
              marginBottom: 8,
            }}
            aria-label="정보 변경"
            title="정보 변경"
          >
            정보 변경
          </button>

          <button
            onClick={() => {
              toggle();
              logout();
            }}
            style={{
              background: 'none',
              border: 'none',
              fontSize: 13,
              color: '#ccc',
              display: 'block',
              textAlign: 'center',
              padding: '8px 0',
              borderTop: '1px solid rgba(255,255,255,0.1)',
              width: '100%',
              cursor: 'pointer',
            }}
            aria-label="로그아웃"
            title="로그아웃"
          >
            로그아웃
          </button>
        </div>
      </div>

      {/* 비밀번호 변경 모달 */}
      <PasswordChangeModal isOpen={isModalOpen} onClose={() => setModalOpen(false)} />
    </>
  );
}

export default NavBar;