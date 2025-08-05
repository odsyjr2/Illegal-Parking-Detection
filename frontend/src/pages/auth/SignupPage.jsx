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

  // 중복확인 상태 관리
  const [checking, setChecking] = useState(false)
  const [emailExists, setEmailExists] = useState(null) // null: 확인 안함, true: 중복, false: 사용 가능
  const [checkError, setCheckError] = useState('')

  const navigate = useNavigate()

  const isValidEmail = (email) => {
    const regex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/
    return regex.test(email)
  }

  // 이메일 중복 검사 함수
  const checkEmailDuplicate = async () => {
    if (!id) {
      alert('이메일을 입력하세요.')
      return
    }
    if (!isValidEmail(id)) {
      alert('올바른 이메일 형식을 입력해주세요.')
      return
    }

    setChecking(true)
    setCheckError('')
    setEmailExists(null)

    try {
      console.log('중복확인 API 호출: ', id)
      const res = await fetch(`http://localhost:8080/api/users/check-email?email=${encodeURIComponent(id)}`)
      if (!res.ok) {
        throw new Error('중복 확인 서버 에러')
      }
      const data = await res.json()
      console.log('중복확인 API 응답 데이터:', data)

      setEmailExists(data.data.emailExists)
    } catch (e) {
      console.error('중복 확인 중 오류:', e)
      setCheckError('중복 확인 중 오류가 발생했습니다.')
    } finally {
      setChecking(false)
      console.log('중복확인 완료')
    }
  }

  const handleSignup = async (e) => {
    e.preventDefault()

    if (!id) {
      alert('이메일을 입력하세요.')
      return
    }
    if (!isValidEmail(id)) {
      alert('올바른 이메일 형식을 입력해주세요.')
      return
    }

    if (password !== passwordCheck) {
      alert('비밀번호와 확인이 일치하지 않습니다.')
      return
    }

    if (emailExists === null) {
      alert('이메일 중복확인을 해주세요.')
      return
    }

    if (emailExists) {
      alert('중복된 이메일입니다. 다른 이메일을 사용하세요.')
      return
    }

    setLoading(true)

    try {
      const res = await fetch('http://localhost:8080/api/users/signup', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          name,
          email: id,
          password,
          adminCode: adminCode.trim() || undefined,
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

  return (
    <div className="auth-container">
      <form className="auth-box" onSubmit={handleSignup}>
        <h2>회원가입</h2>

        <div>
          <label>이름:</label>
          <input type="text" value={name} onChange={(e) => setName(e.target.value)} required />
        </div>

        <div>
          <label>아이디(이메일):</label>
          <div className="input-row">
            <input
              type="email"
              value={id}
              onChange={(e) => {
                setId(e.target.value)
                setEmailExists(null) // 이메일 변경시 중복확인 초기화
                setCheckError('')
              }}
              required
            />
            <button
              type="button"
              onClick={checkEmailDuplicate}
              disabled={checking || !id}
              style={{
                opacity: checking || !id ? 0.5 : 1,
                cursor: checking || !id ? 'not-allowed' : 'pointer',
              }}
            >
              {checking ? '확인중...' : '중복확인'}
            </button>
          </div>
          {/* 중복 확인 결과 메시지 */}
          {emailExists === true && (
            <div className="check-message duplicate">
              이미 사용중인 이메일입니다.
            </div>
          )}
          {emailExists === false && (
            <div className="check-message available">
              사용 가능한 이메일입니다.
            </div>
          )}
          {checkError && (
            <div className="check-message error">{checkError}</div>
          )}
        </div>

        <div>
          <label>비밀번호:</label>
          <input type="password" value={password} onChange={(e) => setPassword(e.target.value)} required />
        </div>

        <div>
          <label>비밀번호 확인:</label>
          <input type="password" value={passwordCheck} onChange={(e) => setPasswordCheck(e.target.value)} required />
        </div>

        <div>
          <label>관리자 코드 (선택):</label>
          <input type="text" value={adminCode} onChange={(e) => setAdminCode(e.target.value)} />
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