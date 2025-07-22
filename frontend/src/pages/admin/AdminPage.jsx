import React, { useState } from 'react'
import { useNavigate } from 'react-router-dom'

function AdminPage() {
  const navigate = useNavigate()

  // 사용자 목록 mock
  const [users, setUsers] = useState([
    { id: 1, name: '김민수', email: 'kim@example.com', role: '사용자', createdAt: '2024-04-01' },
    { id: 2, name: '이영희', email: 'lee@example.com', role: '사용자', createdAt: '2024-05-12' },
    { id: 3, name: '관리자', email: 'admin@example.com', role: '관리자', createdAt: '2024-01-20' },
    { id: 4, name: '박철수', email: 'park@example.com', role: '사용자', createdAt: '2024-07-15' },
    { id: 5, name: '최유진', email: 'choi@example.com', role: '사용자', createdAt: '2024-07-16' },
    { id: 6, name: '홍성민', email: 'hong@example.com', role: '사용자', createdAt: '2024-07-18' }
  ])

  // CCTV 상태 관리
  const [cctvs, setCctvs] = useState([
    { id: 1, location: '서울 관악구 봉천동 123-45' },
    { id: 2, location: '서울 강남구 테헤란로 321' }
  ])
  const [newCctv, setNewCctv] = useState('')

  // 탈퇴 (삭제) 로직: 관리자 자기 자신은 탈퇴 방지 예시
  const handleLeave = (id, email, role) => {
    if (role === '관리자') {
      alert('관리자 계정은 탈퇴할 수 없습니다.')
      return
    }
    setUsers(users.filter(u => u.id !== id))
  }

  const handleAddCctv = () => {
    if (newCctv.trim() === '') return
    setCctvs([...cctvs, { id: Date.now(), location: newCctv }])
    setNewCctv('')
  }

  const handleDeleteCctv = (id) => {
    setCctvs(cctvs.filter(c => c.id !== id))
  }

  const handleGotoReports = () => {
    navigate('/search')
  }

  return (
    <div style={{ maxWidth: 1000, margin: '40px auto', padding: 20 }}>
      <h1 style={{ fontSize: 24, marginBottom: 28 }}>👥 사용자 </h1>

      {/* 사용자 목록 */}
      <div style={{
        background: '#fff',
        padding: 20,
        borderRadius: 10,
        boxShadow: '0 2px 10px rgba(0,0,0,0.05)',
        marginBottom: 40
      }}>
        <h2 style={{ fontSize: 18, marginBottom: 14 }}>📋 사용자 목록</h2>
        {/* 스크롤 가능 영역 */}
        <div style={{ maxHeight: 260, overflowY: 'auto', borderRadius: 8, border: '1px solid #f0f0f0' }}>
          <table style={{ width: '100%', borderCollapse: 'collapse' }}>
            <thead>
              <tr style={{ background: '#f0f4f8' }}>
                <th style={thStyle}>이름</th>
                <th style={thStyle}>이메일</th>
                <th style={thStyle}>역할</th>
                <th style={thStyle}>가입일</th>
                <th style={thStyle}></th>
              </tr>
            </thead>
            <tbody>
              {users.map(user => (
                <tr key={user.id}>
                  <td style={tdStyle}>{user.name}</td>
                  <td style={tdStyle}>{user.email}</td>
                  <td style={tdStyle}>{user.role}</td>
                  <td style={tdStyle}>{user.createdAt}</td>
                  <td style={tdStyle}>
                    <button
                      onClick={() => handleLeave(user.id, user.email, user.role)}
                      disabled={user.role === '관리자'}
                      style={{
                        fontSize: 13,
                        padding: '5px 11px',
                        background: user.role === '관리자' ? '#eee' : '#ef4444',
                        color: user.role === '관리자' ? '#ccc' : '#fff',
                        border: 'none',
                        borderRadius: 6,
                        cursor: user.role === '관리자' ? 'not-allowed' : 'pointer',
                        opacity: user.role === '관리자' ? 0.7 : 1
                      }}
                    >
                      탈퇴
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* CCTV 관리 */}
      <div style={{
        background: '#fff',
        padding: 20,
        borderRadius: 10,
        boxShadow: '0 2px 10px rgba(0,0,0,0.05)',
        marginBottom: 40
      }}>
        <h2 style={{ fontSize: 18, marginBottom: 16 }}>📹 CCTV 관리</h2>
        <div style={{ display: 'flex', gap: 8 }}>
          <input
            placeholder="CCTV 위치 입력"
            value={newCctv}
            onChange={e => setNewCctv(e.target.value)}
            style={{
              flex: 1,
              padding: '8px 12px',
              borderRadius: 6,
              border: '1px solid #ccc'
            }}
          />
          <button
            onClick={handleAddCctv}
            style={{
              padding: '8px 14px',
              backgroundColor: '#337aff',
              color: '#fff',
              border: 'none',
              borderRadius: 6,
              fontWeight: 600,
              cursor: 'pointer'
            }}
          >
            + 추가
          </button>
        </div>
        <ul style={{ marginTop: 16, paddingLeft: 0, listStyle: 'none' }}>
          {cctvs.map(c => (
            <li
              key={c.id}
              style={{
                marginBottom: 8,
                background: '#f1f5f9',
                padding: '8px 12px',
                borderRadius: 6,
                display: 'flex',
                justifyContent: 'space-between'
              }}
            >
              <span>{c.location}</span>
              <button
                onClick={() => handleDeleteCctv(c.id)}
                style={{
                  backgroundColor: '#ef4444',
                  color: '#fff',
                  border: 'none',
                  borderRadius: 6,
                  padding: '4px 10px',
                  cursor: 'pointer'
                }}
              >
                삭제
              </button>
            </li>
          ))}
        </ul>
      </div>

      {/* 신고현황 이동 버튼 */}
      <div>
        <button
          onClick={handleGotoReports}
          style={{
            padding: '12px 28px',
            backgroundColor: '#10b981',
            color: '#fff',
            border: 'none',
            borderRadius: 8,
            fontSize: 16,
            cursor: 'pointer',
            fontWeight: 600
          }}
        >
          🧾 신고 현황 보기
        </button>
      </div>
    </div>
  )
}

const thStyle = {
  padding: '10px 8px',
  fontWeight: 'bold',
  textAlign: 'left',
  borderBottom: '1px solid #ddd'
}

const tdStyle = {
  padding: '10px 8px',
  borderBottom: '1px solid #f0f0f0',
  color: '#333'
}

export default AdminPage
