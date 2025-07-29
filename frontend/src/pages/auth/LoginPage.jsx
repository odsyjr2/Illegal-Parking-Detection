import { useState } from 'react'
import { useNavigate, Link } from 'react-router-dom'
import './AuthForm.css'

function LoginPage() {
  const [id, setId] = useState('')
  const [password, setPassword] = useState('')
  const navigate = useNavigate()

  const mockUsers = [
    {
      id: 'user',
      name: '일반사용자',
      email: 'USER@example.com',
      password: '1234',
      adminCode: null,
      role: 'USER',
      accessToken: 'access-token-user1',
      refreshToken: 'refresh-token-user1',
    },
    {
      id: 'admin',
      name: '관리자',
      email: 'admin@example.com',
      password: '1234',
      adminCode: 'ADMIN001',
      role: 'ADMIN',
      accessToken: 'access-token-admin',
      refreshToken: 'refresh-token-admin',
    },
  ]

  const handleLogin = (e) => {
    e.preventDefault()
    const matchedUser = mockUsers.find((user) => user.id === id && user.password === password)

    if (matchedUser) {
      console.log('로그인 성공:', matchedUser)
      localStorage.setItem('user', JSON.stringify(matchedUser))
      localStorage.setItem('role', matchedUser.role)
      window.dispatchEvent(new Event('roleChanged'))
      alert(`환영합니다, ${matchedUser.name}님!`)
      navigate('/')
    } else {
      alert('아이디 또는 비밀번호가 잘못되었습니다.')
    }
  }

  return (
    <div className="auth-container">
      <form className="auth-box" onSubmit={handleLogin}>
        <h2>로그인</h2>
        <div>
          <label htmlFor="id">아이디</label>
          <input id="id" type="text" value={id} onChange={(e) => setId(e.target.value)} required />
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
        <button type="submit" className="auth-button">
          로그인
        </button>
        <div className="auth-link">
          계정이 없나요? <Link to="/signup">회원가입</Link>
        </div>
      </form>
    </div>
  )
}

export default LoginPage
