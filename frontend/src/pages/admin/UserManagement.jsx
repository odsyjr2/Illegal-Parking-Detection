import React, { useState, useEffect, useMemo } from 'react'

const PAGE_SIZE = 15

function UserManagement() {
  // 상태 정의
  const [users, setUsers] = useState([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const [currentPage, setCurrentPage] = useState(1)
  const [selectedIds, setSelectedIds] = useState([])
  const [searchText, setSearchText] = useState('')
  const [filterRole, setFilterRole] = useState('전체')

  // 로그인한 사용자 정보 (id, role)
  const loggedInUser = useMemo(() => {
    try {
      return JSON.parse(localStorage.getItem('user')) || {}
    } catch {
      return {}
    }
  }, [])
  const loggedInUserId = loggedInUser.id
  const isAdmin = loggedInUser.role === '관리자'

  // 인증 토큰
  const token = localStorage.getItem('accessToken')
  const authHeaders = {
    'Content-Type': 'application/json',
    Authorization: `Bearer ${token}`,
  }

  // 사용자 목록 불러오기
  useEffect(() => {
    async function fetchUsers() {
      setLoading(true)
      setError(null)
      try {
        const res = await fetch('http://localhost:8080/api/admin/users', { headers: authHeaders })
        if (res.status === 401) throw new Error('인증이 필요합니다. 다시 로그인하세요.')
        if (!res.ok) throw new Error('사용자 목록을 불러오는데 실패했습니다.')
        const data = await res.json()
        setUsers(data)
      } catch (e) {
        setError(e.message || '데이터 로드 실패')
      } finally {
        setLoading(false)
        setSelectedIds([])
      }
    }
    if (token) fetchUsers()
  }, [token])

  // 체크박스 선택 변경 (여러 개 선택 가능)
  const handleCheckboxChange = (id, checked) => {
    setSelectedIds(prev => (checked ? [...prev, id] : prev.filter(sid => sid !== id)))
  }

  // 체크박스 비활성화 여부 판단 함수
  // - 로그인 관리자의 경우, 본인과 일반/단속관리원 계정만 선택 가능
  // - 다른 관리자 계정은 선택 불가능
  // - 비관리자는 모든 계정 선택 가능
  const isCheckboxDisabled = (user) => {
    if (isAdmin) {
      if (user.role === '관리자' && user.id !== loggedInUserId) {
        return true // 다른 관리자 체크 불가
      }
      return false // 본인 관리자 및 일반/단속관리원 체크 가능
    } 
    // 비관리자: 모두 체크 가능 (필요시 조절 가능)
    return false
  }

  // 필터링 및 검색
  const filteredUsers = useMemo(() => {
    const lowerSearch = searchText.toLowerCase()
    return users.filter(user =>
      (filterRole === '전체' || user.role === filterRole) &&
      (user.name.toLowerCase().includes(lowerSearch) || user.email.toLowerCase().includes(lowerSearch))
    )
  }, [users, searchText, filterRole])

  // 페이징 계산
  const totalPages = Math.ceil(filteredUsers.length / PAGE_SIZE) || 1
  const currentPageUsers = useMemo(() => {
    const start = (currentPage - 1) * PAGE_SIZE
    return filteredUsers.slice(start, start + PAGE_SIZE)
  }, [filteredUsers, currentPage])

  // 페이지 이동
  const goToPage = (page) => {
    if (page < 1 || page > totalPages) return
    setCurrentPage(page)
    setSelectedIds([])
  }

  // 탈퇴 버튼 활성화 조건  
  // - 선택된 유저가 한 명 이상이고,  
  // - 로그인 사용자가 관리자인 경우  
  // - 선택된 목록에 다른 관리자(본인 제외)는 없어야 함
  const canDelete =
    selectedIds.length > 0 &&
    isAdmin &&
    !selectedIds.some(
      selId => {
        const user = users.find(u => u.id === selId)
        return user?.role === '관리자' && selId !== loggedInUserId
      }
    )

  // 탈퇴 처리 함수
  const handleLeaveSelected = async () => {
    if (!canDelete) return

    if (!window.confirm(`선택한 사용자 ${selectedIds.length}명을 탈퇴 처리하시겠습니까?`)) return

    try {
      await Promise.all(
        selectedIds.map(id =>
          fetch(`http://localhost:8080/api/admin/users/${id}`, {
            method: 'DELETE',
            headers: authHeaders,
          })
        )
      )
      setUsers(prev => prev.filter(u => !selectedIds.includes(u.id)))
      setSelectedIds([])
      setCurrentPage(1)
      alert('선택한 사용자들이 정상적으로 탈퇴 처리되었습니다.')
    } catch {
      alert('사용자 탈퇴 처리 중 오류가 발생했습니다.')
    }
  }

  // 이메일 마스킹 (앞 두 글자 노출)
  const maskEmail = (email) => {
    if (!email) return ''
    const [local, domain] = email.split('@')
    if (!domain) return email
    if (local.length <= 2) {
      return local[0] + '*'.repeat(local.length - 1) + '@' + domain
    }
    return local.slice(0, 2) + '*'.repeat(local.length - 2) + '@' + domain
  }

  // 이름 마스킹 (앞 두 글자만 노출)
  const maskName = (name) => {
    if (!name) return ''
    if (name.length === 1) return name
    if (name.length === 2) return name[0] + '*'
    // 3글자 이상이면 가운데 한 글자만 마스킹
    const mid = Math.floor(name.length / 2)
    return name.slice(0, mid) + '*' + name.slice(mid + 1)
  }

  // 날짜 포맷 변환 함수 (YYYY-MM-DD)
  const formatDate = (isoString) => {
    if (!isoString) return '-'
    const date = new Date(isoString)
    if (isNaN(date.getTime())) return '-'
    const year = date.getFullYear()
    const month = String(date.getMonth() + 1).padStart(2, '0')  // 월은 0부터 시작하므로 +1
    const day = String(date.getDate()).padStart(2, '0')
    return `${year}-${month}-${day}`
  }
  // 페이지네이션 버튼 스타일
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

  // 페이지네이션 컴포넌트
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

  return (
    <div style={{ background: '#fff', padding: 20, borderRadius: 10 }}>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 16, gap: 12 }}>
        <h2>📋 사용자 목록</h2>
        <div style={{ display: 'flex', gap: 12, width: '40%', minWidth: 300 }}>
          <input
            type="text"
            placeholder="이름 또는 이메일 검색"
            value={searchText}
            onChange={e => setSearchText(e.target.value)}
            style={{
              flex: 1, padding: '8px 12px',
              borderRadius: 6, border: '1px solid #ccc',
              fontSize: 14, width: '100%', boxSizing: 'border-box'
            }}
          />
          <select
            value={filterRole}
            onChange={e => setFilterRole(e.target.value)}
            style={{
              padding: '8px 12px', borderRadius: 6,
              border: '1px solid #ccc',
              fontSize: 14, width: 140, boxSizing: 'border-box'
            }}
          >
            <option value="전체">전체</option>
            <option value="USER">사용자</option>
            <option value="ADMIN">관리자</option>
            <option value="INSPECTOR">단속관리원</option>
          </select>
        </div>
      </div>

      {loading && <div style={{ padding: 20, textAlign: 'center' }}>로딩 중...</div>}
      {error && <div style={{ color: 'red', padding: 12, textAlign: 'center' }}>{error}</div>}

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
          {currentPageUsers.length === 0 ?
            (<tr>
              <td colSpan={5} style={{ padding: 20, textAlign: 'center', color: '#777' }}>
                검색 결과가 없습니다.
              </td>
            </tr>) :
            currentPageUsers.map(user => {
              const isChecked = selectedIds.includes(user.id)
              const disableCheckbox = isCheckboxDisabled(user)
              return (
                <tr key={user.id} style={{ borderBottom: '1px solid #eee' }}>
                  <td style={{ padding: '8px' }}>
                    <input
                      type="checkbox"
                      disabled={disableCheckbox}
                      checked={isChecked}
                      onChange={e => handleCheckboxChange(user.id, e.target.checked)}
                      aria-label={`${user.name} 선택`}
                    />
                  </td>
                  <td style={{ padding: '8px 12px', userSelect: 'none' }}>{maskName(user.name)}</td>
                  <td style={{ padding: '8px 12px', color: '#555' }}>{maskEmail(user.email)}</td>
                  <td style={{ padding: '8px 12px' }}>{user.role}</td>
                  <td style={{ padding: '8px 12px' }}>{formatDate(user.joinedAt)}</td>
                </tr>
              )
            })}
        </tbody>
      </table>

      <Pagination />

      <div style={{ textAlign: 'right', marginTop: 16 }}>
        <button
          onClick={handleLeaveSelected}
          disabled={!canDelete}
          style={{
            padding: '10px 18px',
            backgroundColor: canDelete ? '#354185ff' : '#ccc',
            color: '#fff',
            border: 'none',
            borderRadius: 6,
            fontWeight: 'bold',
            cursor: canDelete ? 'pointer' : 'not-allowed',
            userSelect: 'none',
          }}
          aria-label="선택 사용자 탈퇴"
        >
          선택 사용자 탈퇴
        </button>
      </div>
    </div>
  )
}

export default UserManagement