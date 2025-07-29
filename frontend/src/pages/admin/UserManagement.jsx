import React, { useState, useMemo } from 'react'

function UserManagement() {
  const [users, setUsers] = useState([
    { id: 1, name: '김민수', email: 'kim@example.com', role: '사용자', createdAt: '2024-04-01' },
    { id: 2, name: '이영희', email: 'lee@example.com', role: '사용자', createdAt: '2024-05-12' },
    { id: 3, name: '관리자', email: 'admin@example.com', role: '관리자', createdAt: '2024-01-20' },
    { id: 4, name: '박단속', email: 'dan@example.com', role: '단속관리원', createdAt: '2024-06-10' }
  ])

  const [selectedIds, setSelectedIds] = useState([])
  const [searchText, setSearchText] = useState('')
  const [filterRole, setFilterRole] = useState('전체')

  const handleCheckboxChange = (id, checked) => {
    setSelectedIds(prev => {
      if (checked) return [...prev, id]
      else return prev.filter(selectedId => selectedId !== id)
    })
  }

  const handleLeaveSelected = () => {
    if (selectedIds.length === 0) {
      alert('탈퇴할 사용자를 하나 이상 선택하세요.')
      return
    }

    const selectedUsers = users.filter(u => selectedIds.includes(u.id))
    const hasAdmin = selectedUsers.some(u => u.role === '관리자')
    if (hasAdmin) {
      alert('관리자 계정은 탈퇴할 수 없습니다.')
      return
    }

    setUsers(users.filter(u => !selectedIds.includes(u.id)))
    setSelectedIds([])
  }

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

  return (
    <div style={{ background: '#fff', padding: 20, borderRadius: 10 }}>
      <div style={{
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        marginBottom: 16,
        gap: 12
      }}>
      <h2> 📋 사용자 목록</h2>

      {/* 검색 + 필터 영역을 table 위에 같은 줄에 배치 */}
      <div
        style={{
          display: 'flex',
          gap: 12,
          width: '40%',
          minWidth: 300,
        }}
      >
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

      {/* 사용자 목록 테이블 */}
      <table
        style={{
          width: '100%',
          borderCollapse: 'collapse',
          textAlign: 'left',
        }}
      >
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
          {filteredUsers.length === 0 ? (
            <tr>
              <td colSpan={5} style={{ padding: 20, textAlign: 'center', color: '#777' }}>
                검색 결과가 없습니다.
              </td>
            </tr>
          ) : (
            filteredUsers.map(user => {
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