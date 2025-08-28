import { useState } from 'react'
import { useNavigate, Link } from 'react-router-dom'
import './AuthForm.css'

function LoginPage() {
  const [id, setId] = useState('')
  const [password, setPassword] = useState('')
  const [loading, setLoading] = useState(false)
  const navigate = useNavigate()

  const handleLogin = async (e) => {
    e.preventDefault()
    setLoading(true)

    try {
      const res = await fetch('/api/users/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          email: id, // 이메일 기준
          password,
        }),
      })

      if (!res.ok) {
        throw new Error('아이디 또는 비밀번호가 잘못되었습니다.')
      }

      const { data } = await res.json()

      const { accessToken, refreshToken, id: userId, name, email, adminCode, role } = data

      if (!accessToken) {
        throw new Error('로그인 응답에 액세스 토큰이 없습니다.')
      }

      const user = { id: userId, name, email, adminCode, role }

      localStorage.setItem('accessToken', accessToken)
      localStorage.setItem('refreshToken', refreshToken)
      localStorage.setItem('user', JSON.stringify(user))
      localStorage.setItem('role', role)

      window.dispatchEvent(new Event('roleChanged'))

      alert(`환영합니다, ${name}님!`)
      navigate('/')
    } catch (error) {
      alert(error.message || '로그인 실패')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="auth-container">
      <form className="auth-box" onSubmit={handleLogin}>
        <h2>로그인</h2>
        <div>
          <label htmlFor="id">아이디(이메일)</label>
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
        <button type="submit" className="auth-button" disabled={loading}>
          {loading ? '로그인 중...' : '로그인'}
        </button>
        <div className="auth-link">
          계정이 없나요? <Link to="/signup">회원가입</Link>
          <div>
            계정이 없나요? <Link to="/report">로그인 없이 신고</Link>
          </div>
        </div>
      </form>
    </div>
  )
}

export default LoginPage