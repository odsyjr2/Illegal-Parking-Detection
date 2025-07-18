import { useState } from 'react';

function SignupPage() {
  const [name, setName] = useState('');
  const [id, setId] = useState('');
  const [password, setPassword] = useState('');
  const [passwordCheck, setPasswordCheck] = useState('');
  const [adminCode, setAdminCode] = useState('');

  const handleSignup = (e) => {
    e.preventDefault();
    if (password !== passwordCheck) {
      alert('비밀번호와 확인이 일치하지 않습니다.');
      return;
    }
    // TODO: 회원가입 로직 넣기 (API 호출 등)
    alert(`회원가입 시도: 이름=${name}, 아이디=${id}, 관리자코드=${adminCode}`);
  };

  return (
    <div>
      <h2>회원가입</h2>
      <form onSubmit={handleSignup}>
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
          <label>아이디:</label>
          <input
            type="text"
            value={id}
            onChange={(e) => setId(e.target.value)}
            required
          />
          {/* TODO: 중복 확인 버튼 추가 가능 */}
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
        <button type="submit">회원가입</button>
      </form>
    </div>
  );
}

export default SignupPage;
