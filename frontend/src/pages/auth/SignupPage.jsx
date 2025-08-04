import { useState } from 'react'
import { useNavigate, Link } from 'react-router-dom'
import './AuthForm.css'

function SignupPage() {
  const [name, setName] = useState('')
  const [id, setId] = useState('')
  const [password, setPassword] = useState('')
  const [passwordCheck, setPasswordCheck] = useState('')
  const [adminCode, setAdminCode] = useState('')
  const [loading, setLoading] = useState(false)

  const navigate = useNavigate()

  const handleSignup = async (e) => {
    e.preventDefault()

    if (password !== passwordCheck) {
      alert('비밀번호와 확인이 일치하지 않습니다.')
      return
    }

    setLoading(true)

    try {
      const res = await fetch('http://localhost:8080/api/users/signup', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          name,
          email: id,           // 백엔드가 아이디 대신 이메일로 받으니 email로 보냄
          password,
          adminCode: adminCode.trim() || undefined, // 빈 문자열이면 undefined로 넘겨서 생략 가능하도록
        }),
      })

      if (!res.ok) {
        const errorData = await res.json().catch(() => ({}))
        const msg = errorData.message || '회원가입에 실패했습니다.'
        throw new Error(msg)
      }

      alert('회원가입이 완료되었습니다. 로그인 페이지로 이동합니다.')
      navigate('/login')
    } catch (error) {
      alert(error.message)
    } finally {
      setLoading(false)
    }
  }

  // 선택 항목 중복확인 버튼은 별도 API 연동 필요. 없으면 제거하거나 비활성화하세요.

  return (
    <div className="auth-container">
      <form className="auth-box" onSubmit={handleSignup}>
        <h2>회원가입</h2>
        <div>
          <label>이름:</label>
          <input
            type="text"
            value={name}
            onChange={(e) => setName(e.target.value)}
            required
          />
        </div>
        <div>
          <label>아이디(이메일):</label>
          <div className="input-row">
            <input
              type="email"
              value={id}
              onChange={(e) => setId(e.target.value)}
              required
            />
            {/* 중복확인 버튼은 아래처럼 비활성화 혹은 제거하세요 */}
            <button id="CheckUsername" type="button" disabled style={{ opacity: 0.5, cursor: 'not-allowed' }}>
              중복확인
            </button>
          </div>
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
        <div>
          <label>비밀번호 확인:</label>
          <input
            type="password"
            value={passwordCheck}
            onChange={(e) => setPasswordCheck(e.target.value)}
            required
          />
        </div>
        <div>
          <label>관리자 코드 (선택):</label>
          <input
            type="text"
            value={adminCode}
            onChange={(e) => setAdminCode(e.target.value)}
          />
        </div>
        <button type="submit" className="auth-button" disabled={loading}>
          {loading ? '가입 중...' : '회원가입'}
        </button>
        <div className="auth-link">
          계정이 있나요? <Link to="/login">로그인</Link>
        </div>
      </form>
    </div>
  )
}

export default SignupPage
