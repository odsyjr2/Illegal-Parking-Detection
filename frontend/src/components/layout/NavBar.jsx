// NavBar.js
import { Link, useLocation, useNavigate } from 'react-router-dom';
import { useState, useEffect } from 'react';
import './Sidebar.css';

const HIDDEN_PATHS = ['/login', '/signup'];

function NavBar({ isOpen, toggle }) {
  const location = useLocation();
  const navigate = useNavigate();

  // 상태로 사용자 정보 유지 (null이면 미로그인 상황)
  const [user, setUser] = useState(null);

  useEffect(() => {
    // localStorage에서 user 정보 불러오기 (예: 로그인 시 저장한 객체)
    try {
      const storedUser = JSON.parse(localStorage.getItem('user'));
      if (storedUser) setUser(storedUser);
      else setUser(null);
    } catch {
      setUser(null);  // 파싱 실패 시 null 처리
    }
  }, [location.pathname]); // 경로가 바뀔 때마다 최신 정보 반영

  // 페이지가 로그인 또는 회원가입일 경우 NavBar 숨김
  if (HIDDEN_PATHS.includes(location.pathname)) return null;

  // 로그인 정보가 없으면 기본값
  // adminInfo가 user 정보와 동일하거나 없는 경우 기본 admin 정보 출력
  const adminInfo = user
    ? { name: user.name || '이름없음', email: user.email || '이메일없음' }
    : { name: '홍길동', email: 'admin@example.com' };

  // 로그아웃 함수
  const logout = () => {
    localStorage.removeItem('user');
    localStorage.removeItem('role');
    alert('로그아웃 되었습니다!');
    navigate('/login');
  };

  // 현재 경로가 활성 메뉴인지 확인 함수
  const isActive = (path) => (location.pathname === path ? 'active' : '');

  return (
    <>
      <button className="hamburger" onClick={toggle} aria-label="메뉴 열기" title="메뉴">
        ☰
      </button>
      <div className={`sidebar ${isOpen ? 'open' : 'hidden'}`}>
        <div>
          <h2>로고</h2>

          {/* 로그인 사용자 정보 */}
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

          {/* 메뉴 목록 */}
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

        {/* 맨 아래 로그아웃 버튼 영역 */}
        <div style={{ marginTop: 'auto', paddingTop: 16 }}>
          <button
            onClick={() => {
              toggle();  // 메뉴 닫기
              logout();  // 로그아웃 처리
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
    </>
  );
}

export default NavBar;
