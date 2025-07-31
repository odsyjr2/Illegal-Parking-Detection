import React, { useState, useMemo, useEffect } from 'react'

// 임시 더미 사용자 데이터 (API 구현 전용)
const dummyUsers = [
  { id: 1, name: '김민수', email: 'kim@example.com', role: '사용자', createdAt: '2024-04-01' },
  { id: 2, name: '이영희', email: 'lee@example.com', role: '사용자', createdAt: '2024-05-12' },
  { id: 3, name: '관리자', email: 'admin@example.com', role: '관리자', createdAt: '2024-01-20' },
  { id: 4, name: '박단속', email: 'dan@example.com', role: '단속관리원', createdAt: '2024-06-10' },  
  // 필요시 더 추가 가능
]

const PAGE_SIZE = 15

function UserManagement() {
  // [1] 유저 데이터 상태
  const [users, setUsers] = useState(dummyUsers) // 초기엔 더미 데이터 표시
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)

  // [2] 페이지네이션 상태
  const [currentPage, setCurrentPage] = useState(1)

  // [3] 선택된 사용자 ID 리스트 상태
  const [selectedIds, setSelectedIds] = useState([])

  // [4] 검색어 및 필터 상태
  const [searchText, setSearchText] = useState('')
  const [filterRole, setFilterRole] = useState('전체')

  // [5] 백엔드 API 호출 예시 (컴포넌트 마운트 시 한번 실행)
  useEffect(() => {
    const fetchUsers = async () => {
      setLoading(true)
      setError(null)
      try {
        // TODO: 실제 API URL로 변경
        const res = await fetch('/api/users')
        if (!res.ok) throw new Error('네트워크 오류')
        const data = await res.json()
        setUsers(data)
      } catch (e) {
        setError(e.message || '데이터 로드 실패')
        // 실패 시 dummyUsers 유지하며 화면 표시
      } finally {
        setLoading(false)
      }
    }
    fetchUsers()
  }, [])

  // [6] 체크박스 선택 변경 함수
  const handleCheckboxChange = (id, checked) => {
    setSelectedIds(prev => {
      if (checked) return [...prev, id]
      else return prev.filter(selectedId => selectedId !== id)
    })
  }

  // [7] 선택된 사용자 탈퇴 처리 함수 (관리자 제외)
  const handleLeaveSelected = () => {
    if (selectedIds.length === 0) {
      alert('탈퇴할 사용자를 하나 이상 선택하세요.')
      return
    }
    const selectedUsers = users.filter(u => selectedIds.includes(u.id))
    if (selectedUsers.some(u => u.role === '관리자')) {
      alert('관리자 계정은 탈퇴할 수 없습니다.')
      return
    }
    // TODO: 실제 백엔드 탈퇴 API 호출 구현 필요
    // 현재는 클라이언트 상태만 업데이트
    setUsers(users.filter(u => !selectedIds.includes(u.id)))
    setSelectedIds([])
    setCurrentPage(1) // 탈퇴 후 첫 페이지로 이동
  }

  // [8] 검색+필터 적용된 사용자 리스트 계산
  const filteredUsers = useMemo(() => {
    const lowerSearch = searchText.toLowerCase()
    return users.filter(user => {
      if (filterRole !== '전체' && user.role !== filterRole) return false
      return (
        user.name.toLowerCase().includes(lowerSearch) ||
        user.email.toLowerCase().includes(lowerSearch)
      )
    })
  }, [users, searchText, filterRole])

  // [9] 전체 페이지 수 계산
  const totalPages = Math.ceil(filteredUsers.length / PAGE_SIZE)

  // [10] 현재 페이지 사용자 슬라이스
  const currentPageUsers = useMemo(() => {
    const start = (currentPage - 1) * PAGE_SIZE
    return filteredUsers.slice(start, start + PAGE_SIZE)
  }, [filteredUsers, currentPage])

  // [11] 페이지 이동 함수
  const goToPage = (page) => {
    if (page < 1 || page > totalPages) return
    setCurrentPage(page)
    setSelectedIds([]) // 페이지 변경 시 선택 초기화
  }

  // [12] 페이지네이션 UI 컴포넌트
  const Pagination = () => {
    if (totalPages <= 0) return null
    const pages = [...Array(totalPages).keys()].map(i => i + 1)
    return (
      <div style={{ display: 'flex', justifyContent: 'center', marginTop: 20, gap: 8 }}>
        <button
          onClick={() => goToPage(currentPage - 1)}
          disabled={currentPage === 1}
          style={pagBtnStyle(currentPage === 1)}
          aria-label="이전 페이지"
        >
          &lt;
        </button>
        {pages.map(page => (
          <button
            key={page}
            onClick={() => goToPage(page)}
            style={pagBtnStyle(page === currentPage)}
            aria-current={page === currentPage ? 'page' : undefined}
          >
            {page}
          </button>
        ))}
        <button
          onClick={() => goToPage(currentPage + 1)}
          disabled={currentPage === totalPages}
          style={pagBtnStyle(currentPage === totalPages)}
          aria-label="다음 페이지"
        >
          &gt;
        </button>
      </div>
    )
  }

  // [13] 페이지네이션 버튼 스타일 함수
  const pagBtnStyle = (active) => ({
    padding: '6px 12px',
    fontWeight: active ? 'bold' : 'normal',
    borderRadius: 4,
    border: active ? '2px solid #354185ff' : '1px solid #ccc',
    backgroundColor: active ? '#354185ff' : 'transparent',
    color: active ? '#fff' : '#333',
    cursor: active ? 'default' : 'pointer',
    userSelect: 'none',
  })

  // [14] 렌더링
  return (
    <div style={{ background: '#fff', padding: 20, borderRadius: 10 }}>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 16, gap: 12 }}>
        <h2> 📋 사용자 목록</h2>

        <div style={{ display: 'flex', gap: 12, width: '40%', minWidth: 300 }}>
          <input
            type="text"
            placeholder="이름 또는 이메일 검색"
            value={searchText}
            onChange={e => setSearchText(e.target.value)}
            style={{
              flex: 1,
              padding: '8px 12px',
              borderRadius: 6,
              border: '1px solid #ccc',
              fontSize: 14,
              width: '100%',
              boxSizing: 'border-box',
            }}
          />
          <select
            value={filterRole}
            onChange={e => setFilterRole(e.target.value)}
            style={{
              padding: '8px 12px',
              borderRadius: 6,
              border: '1px solid #ccc',
              fontSize: 14,
              width: 140,
              boxSizing: 'border-box',
            }}
          >
            <option value="전체">전체</option>
            <option value="사용자">사용자</option>
            <option value="관리자">관리자</option>
            <option value="단속관리원">단속관리원</option>
          </select>
        </div>
      </div>

      {loading && <div style={{ padding: 20, textAlign: 'center' }}>로딩 중...</div>}
      {error && <div style={{ color: 'red', textAlign: 'center', marginBottom: 8 }}>⚠️ {error} (임시 데이터 표시 중)</div>}

      <table style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left' }}>
        <thead>
          <tr style={{ borderBottom: '2px solid #ddd' }}>
            <th style={{ width: 40, padding: '10px 8px' }}></th>
            <th style={{ padding: '10px 12px' }}>이름</th>
            <th style={{ padding: '10px 12px' }}>이메일</th>
            <th style={{ padding: '10px 12px' }}>역할</th>
            <th style={{ padding: '10px 12px' }}>가입일</th>
          </tr>
        </thead>
        <tbody>
          {currentPageUsers.length === 0 ? (
            <tr>
              <td colSpan={5} style={{ padding: 20, textAlign: 'center', color: '#777' }}>
                검색 결과가 없습니다.
              </td>
            </tr>
          ) : (
            currentPageUsers.map(user => {
              const isAdmin = user.role === '관리자'
              const isChecked = selectedIds.includes(user.id)
              return (
                <tr key={user.id} style={{ borderBottom: '1px solid #eee' }}>
                  <td style={{ padding: '8px' }}>
                    <input
                      type="checkbox"
                      disabled={isAdmin}
                      checked={isChecked}
                      onChange={e => handleCheckboxChange(user.id, e.target.checked)}
                      aria-label={`${user.name} 선택`}
                    />
                  </td>
                  <td style={{ padding: '8px 12px', userSelect: 'none' }}>{user.name}</td>
                  <td style={{ padding: '8px 12px', color: '#555' }}>{user.email}</td>
                  <td style={{ padding: '8px 12px' }}>{user.role}</td>
                  <td style={{ padding: '8px 12px' }}>{user.createdAt}</td>
                </tr>
              )
            })
          )}
        </tbody>
      </table>

      <Pagination />

      <div style={{ textAlign: 'right', marginTop: 16 }}>
        <button
          onClick={handleLeaveSelected}
          disabled={selectedIds.length === 0}
          style={{
            padding: '10px 18px',
            backgroundColor: selectedIds.length === 0 ? '#ccc' : '#354185ff',
            color: '#fff',
            border: 'none',
            borderRadius: 6,
            fontWeight: 'bold',
            cursor: selectedIds.length === 0 ? 'not-allowed' : 'pointer',
            userSelect: 'none',
          }}
        >
          선택 사용자 탈퇴
        </button>
      </div>
    </div>
  )
}

export default UserManagement