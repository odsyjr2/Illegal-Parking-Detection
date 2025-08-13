import { useState } from 'react';

function ProfileEditModal({ isOpen, onClose }) {
  const userObj = JSON.parse(localStorage.getItem('user')) || {};
  const originalName = userObj.name || '';
  const originalPassword = userObj.password || '';
  const [name, setName] = useState('');
  const [password, setPassword] = useState('');
  const [loading, setLoading] = useState(false);

  if (!isOpen) return null;

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!name && !password) {
      alert('이름 또는 비밀번호를 입력하세요.');
      return;
    }

    const token = localStorage.getItem('accessToken');
    if (!token) {
      alert('로그인 정보가 없습니다. 다시 로그인해주세요.');
      onClose();
      return;
    }

    setLoading(true);
    let changed = false;
    try {
      // 이름 변경
      if (name && name !== originalName) {
        const nameRes = await fetch('http://localhost:8080/api/users/profile/name', {
          method: 'PUT',
          headers: {
            'Content-Type': 'application/json',
            Authorization: `Bearer ${token}`,
          },
          body: JSON.stringify({ name }),
        });
        if (!nameRes.ok) {
          const errorText = await nameRes.text();
          let errorMsg = '이름 변경에 실패했습니다.';
          try {
            const errJson = errorText ? JSON.parse(errorText) : {};
            errorMsg = errJson.message || errorMsg;
          } catch {}
          throw new Error(errorMsg);
        }
        // 로컬 유저 정보 업데이트
        const user = JSON.parse(localStorage.getItem('user')) || {};
        user.name = name;
        localStorage.setItem('user', JSON.stringify(user));
        changed = true;
      }

      // 비밀번호 변경
      if (password && password !== originalPassword) {
        const pwRes = await fetch('http://localhost:8080/api/users/profile/password', {
          method: 'PUT',
          headers: {
            'Content-Type': 'application/json',
            Authorization: `Bearer ${token}`,
          },
          body: JSON.stringify({ password }),
        });
        if (!pwRes.ok) {
          const errorText = await pwRes.text();
          let errorMsg = '비밀번호 변경에 실패했습니다.';
          try {
            const errJson = errorText ? JSON.parse(errorText) : {};
            errorMsg = errJson.message || errorMsg;
          } catch {}
          throw new Error(errorMsg);
        }
        changed = true;
      }

      if (changed) {
        alert('정보가 성공적으로 변경되었습니다.');
        window.dispatchEvent(new Event('roleChanged')); // 이름 변경시 즉각 반영
        onClose();
      } else {
        alert('변경된 내용이 없습니다.');
      }
    } catch (error) {
      console.error('Profile update error:', error);
      alert(error.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={styles.overlay}>
      <div style={styles.modal}>
        <h2>정보 변경</h2>
        <form onSubmit={handleSubmit}>
          <input
            type="text"
            placeholder="새 이름을 입력하세요"
            value={name}
            onChange={(e) => setName(e.target.value)}
            style={{ width: '95%', padding: 8, marginBottom: 12 }}
          />
          <input
            type="password"
            placeholder="새 비밀번호를 입력하세요"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            minLength={3}
            style={{ width: '95%', padding: 8, marginBottom: 12 }}
          />
          <button type="submit" disabled={loading} style={{ width: '100%', padding: 8 }}>
            {loading ? '변경 중...' : '정보 변경'}
          </button>
          <button type="button" onClick={onClose} style={{ marginTop: 8, width: '100%', padding: 8 }}>
            닫기
          </button>
        </form>
      </div>
    </div>
  );
}

const styles = {
  overlay: {
    position: 'fixed',
    top: 0,
    left: 0,
    right: 0,
    bottom: 0,
    backgroundColor: 'rgba(0,0,0,0.5)',
    display: 'flex',
    justifyContent: 'center',
    alignItems: 'center',
    zIndex: 1000,
  },
  modal: {
    backgroundColor: '#fff',
    padding: 24,
    borderRadius: 8,
    maxWidth: 400,
    width: '90%',
    boxSizing: 'border-box',
  },
};

export default ProfileEditModal;