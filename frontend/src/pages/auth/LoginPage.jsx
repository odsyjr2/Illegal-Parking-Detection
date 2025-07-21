import { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import './AuthForm.css'; // 스타일 파일 import

function LoginPage() {
  const [id, setId] = useState('');
  const [password, setPassword] = useState('');
  const navigate = useNavigate();

  const handleLogin = (e) => {
    e.preventDefault();
    // TODO: 로그인 로직 넣기 (API 호출 등)
    alert(`로그인 시도: 아이디=${id}, 비밀번호=${password}`);
  };

  return (
    <div className="auth-container">
      <form className="auth-box" onSubmit={handleLogin}>
        <h2>로그인</h2>
        <div>
          <label htmlFor="id">아이디</label>
          <input
            id="id"
            type="text"
            value={id}
            onChange={(e) => setId(e.target.value)}
            required
          />
        </div>
        <div>
          <label htmlFor="password">비밀번호</label>
          <input
            id="password"
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            required
          />
        </div>
        <button type="submit" className="auth-button">로그인</button>
        <div className="auth-link">
          계정이 없나요? <Link to="/signup">회원가입</Link>
        </div>
      </form>
    </div>
  );
}

export default LoginPage;
