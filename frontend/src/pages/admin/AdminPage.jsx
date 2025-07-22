import React, { useState } from 'react'
import { useNavigate } from 'react-router-dom'

function AdminPage() {
  const navigate = useNavigate()

  // 사용자 정보 예시 (실제론 백엔드에서 받아올 것)
  const userInfo = {
    name: '홍길동',
    role: '관리자',
    email: 'admin@example.com',
    createdAt: '2024-05-03'
  }

  // CCTV 목록 및 입력 상태
  const [cctvs, setCctvs] = useState([
    { id: 1, location: '서울 관악구 봉천동 123-45' },
    { id: 2, location: '서울 강남구 테헤란로 321' }
  ])
  const [newCctv, setNewCctv] = useState('')

  // CCTV 추가
  const handleAddCctv = () => {
    if (newCctv.trim() === '') return
    setCctvs([...cctvs, { id: Date.now(), location: newCctv }])
    setNewCctv('')
  }

  // CCTV 삭제
  const handleDeleteCctv = (id) => {
    setCctvs(cctvs.filter(c => c.id !== id))
  }

  // 신고 현황 페이지 이동
  const handleGotoReports = () => {
    navigate('/search') // 👉 /search 경로로 이동
  }

  return (
    <div style={{ maxWidth: 700, margin: '40px auto', padding: 20 }}>
      <h1 style={{ fontSize: 24, marginBottom: 24 }}>🔐 관리자 페이지</h1>

      {/* 사용자 정보 */}
      <div style={{
        marginBottom: 30,
        padding: 18,
        background: '#fff',
        borderRadius: 10,
        boxShadow: '0 2px 8px rgba(0,0,0,0.05)'
      }}>
        <h2 style={{ fontSize: 18, marginBottom: 10 }}>👤 사용자 정보</h2>
        <p><strong>이름:</strong> {userInfo.name}</p>
        <p><strong>역할:</strong> {userInfo.role}</p>
        <p><strong>이메일:</strong> {userInfo.email}</p>
        <p><strong>가입일:</strong> {userInfo.createdAt}</p>
      </div>

      {/* CCTV 관리 */}
      <div style={{
        marginBottom: 30,
        padding: 18,
        background: '#fff',
        borderRadius: 10,
        boxShadow: '0 2px 8px rgba(0,0,0,0.05)'
      }}>
        <h2 style={{ fontSize: 18, marginBottom: 10 }}>📹 CCTV 관리</h2>

        <div style={{ display: 'flex', gap: 8 }}>
          <input
            placeholder="CCTV 위치를 입력하세요"
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

        {/* CCTV 목록 */}
        <ul style={{ marginTop: 16, listStyle: 'none', padding: 0 }}>
          {cctvs.map(c => (
            <li
              key={c.id}
              style={{
                marginBottom: 8,
                background: '#f1f5f9',
                padding: '8px 12px',
                borderRadius: 6,
                display: 'flex',
                justifyContent: 'space-between',
                alignItems: 'center'
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

      {/* 신고 현황 버튼 */}
      <div>
        <button
          onClick={handleGotoReports}
          style={{
            padding: '12px 24px',
            backgroundColor: '#10b981',
            color: '#fff',
            border: 'none',
            borderRadius: 8,
            fontSize: 16,
            cursor: 'pointer',
            fontWeight: 600
          }}
        >
          📊 신고 현황 보기
        </button>
      </div>
    </div>
  )
}

export default AdminPage
