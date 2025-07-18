import { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom'

function LoginPage() {
  const [id, setId] = useState('');
  const [password, setPassword] = useState('');
  const navigate = useNavigate()

  const handleLogin = (e) => {
    e.preventDefault();
    // TODO: 로그인 로직 넣기 (API 호출 등)
    alert(`로그인 시도: 아이디=${id}, 비밀번호=${password}`);
  };

  return (
    <div>
      <h2>로그인</h2>
      <form onSubmit={handleLogin}>
        <div>
          <label>아이디:</label>
          <input
            type="text"
            value={id}
            onChange={(e) => setId(e.target.value)}
            required
          />
        </div>
        <div>
          <label>비밀번호:</label>
          <input
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            required
          />
        </div>
        <button type="submit">로그인</button>
        <p style={{ marginTop: 10 }}>
          계정이 없나요? <Link to="/signup">회원가입</Link>
        </p>
      </form>
    </div>
  );
}

export default LoginPage;
