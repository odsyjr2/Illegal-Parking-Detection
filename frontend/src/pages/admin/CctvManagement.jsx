import React, { useState, useMemo } from 'react'

const ZONES = ['전체', '관악구', '강남구', '서초구']
const PAGE_SIZE = 15

function CctvManagement() {
  const [cctvs, setCctvs] = useState([
    { id: 1, location: '서울 관악구 봉천동 123-45', installedAt: '2024-01-10' },
    { id: 2, location: '서울 강남구 테헤란로 321', installedAt: '2024-02-15' },
    { id: 3, location: '서울 서초구 반포동 50', installedAt: '2024-03-20' },
    { id: 4, location: '서울 관악구 신림동 87', installedAt: '2024-04-25' },
    // ... 더 많은 데이터 예시, 필요시 추가
  ])
  const [newCctv, setNewCctv] = useState('')
  const [searchText, setSearchText] = useState('')
  const [filterZone, setFilterZone] = useState('전체')
  const [selectedIds, setSelectedIds] = useState([])
  const [currentPage, setCurrentPage] = useState(1)

  // 필터링: 위치명+구역 필터 적용
  const filteredCctvs = useMemo(() => {
    const lowerSearch = searchText.toLowerCase()
    return cctvs.filter(cctv => {
      if (filterZone !== '전체' && !cctv.location.includes(filterZone)) {
        return false
      }
      if (!cctv.location.toLowerCase().includes(lowerSearch)) {
        return false
      }
      return true
    })
  }, [cctvs, searchText, filterZone])

  // 페이지별 CCTV 목록
  const totalPages = Math.ceil(filteredCctvs.length / PAGE_SIZE)
  const pagedCctvs = useMemo(() => {
    const startIdx = (currentPage - 1) * PAGE_SIZE
    return filteredCctvs.slice(startIdx, startIdx + PAGE_SIZE)
  }, [filteredCctvs, currentPage])

  // 전체 목록이 변경되면 페이지 초기화
  React.useEffect(() => {
    if (currentPage > totalPages) {
      setCurrentPage(totalPages || 1)
    }
  }, [totalPages, currentPage])

  // 한 줄 체크박스 모두 선택/해제 (위치 + 설치일 영역 클릭 시)
  const toggleRowSelection = (id) => {
    if (selectedIds.includes(id)) {
      setSelectedIds(selectedIds.filter(sel => sel !== id))
    } else {
      setSelectedIds([...selectedIds, id])
    }
  }

  // 개별 체크박스 변경
  const handleCheckboxChange = (id, checked) => {
    if (checked) {
      setSelectedIds(prev => [...prev, id])
    } else {
      setSelectedIds(prev => prev.filter(sid => sid !== id))
    }
  }

  const handleAddCctv = () => {
    if (!newCctv.trim()) return
    setCctvs([...cctvs, { id: Date.now(), location: newCctv, installedAt: new Date().toISOString().slice(0, 10) }])
    setNewCctv('')
  }

  const handleDeleteSelected = () => {
    if (selectedIds.length === 0) {
      alert('삭제할 CCTV를 하나 이상 선택하세요.')
      return
    }
    if (window.confirm(`선택한 CCTV ${selectedIds.length}개를 삭제하시겠습니까?`)) {
      setCctvs(cctvs.filter(c => !selectedIds.includes(c.id)))
      setSelectedIds([])
      // 페이지 리셋은 useEffect에서 처리됨
    }
  }

  // 페이지 이동 함수
  const goToPage = (page) => {
    if (page < 1 || page > totalPages) return
    setCurrentPage(page)
    setSelectedIds([])
  }

  // 페이지네이션 UI (번호 및 이전/다음 버튼)
  const Pagination = () => {
    // 항상 렌더링 (페이지가 1개여도 표시)
    const pages = [...Array(totalPages || 1).keys()].map(i => i + 1)

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

  return (
    <div style={{ background: '#fff', padding: 20, borderRadius: 10 }}>
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          marginBottom: 16,
          gap: 12
        }}
      >
        <h2>📹 CCTV 관리</h2>

        {/* 검색 및 구역 선택 */}
        <div>
          <div style={{ display: 'flex', gap: 12, marginBottom: 12 }}>
            <input
              type="text"
              placeholder="위치명으로 검색"
              value={searchText}
              onChange={e => setSearchText(e.target.value)}
              style={{
                flex: 1,
                minWidth: 200,
                padding: '8px 12px',
                borderRadius: 6,
                border: '1px solid #ccc',
                fontSize: 14,
                boxSizing: 'border-box'
              }}
            />
            <select
              value={filterZone}
              onChange={e => setFilterZone(e.target.value)}
              style={{
                minWidth: 120,
                padding: '8px 12px',
                borderRadius: 6,
                border: '1px solid #ccc',
                fontSize: 14,
                boxSizing: 'border-box'
              }}
            >
              {ZONES.map(zone => (
                <option key={zone} value={zone}>{zone}</option>
              ))}
            </select>
          </div>

          {/* 위치 입력 및 추가 */}
          <div style={{ display: 'flex', gap: 8 }}>
            <input
              type="text"
              value={newCctv}
              onChange={e => setNewCctv(e.target.value)}
              placeholder="CCTV 위치 입력"
              style={{
                flex: 1,
                padding: '8px 12px',
                borderRadius: 6,
                border: '1px solid #ccc',
                fontSize: 14,
                boxSizing: 'border-box'
              }}
            />
            <button
              onClick={handleAddCctv}
              style={{
                padding: '8px 16px',
                backgroundColor: '#364599ff',
                color: '#fff',
                border: 'none',
                borderRadius: 6,
                fontWeight: '600',
                cursor: 'pointer',
                userSelect: 'none'
              }}
            >
              + 추가
            </button>
          </div>
        </div>
      </div>

      {/* CCTV 목록 테이블 */}
      <table style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left' }}>
        <thead>
          <tr style={{ borderBottom: '2px solid #ddd' }}>
            <th style={{ width: 40, padding: '10px 8px' }}></th>
            <th style={{ padding: '10px 12px', width: 40 }}>번호</th>
            <th style={{ padding: '10px 12px' }}>위치</th>
            <th style={{ padding: '10px 12px', width: 130 }}>설치일</th>
          </tr>
        </thead>
        <tbody>
          {pagedCctvs.length === 0 ? (
            <tr>
              <td colSpan={4} style={{ padding: 20, textAlign: 'center', color: '#777' }}>
                검색 결과가 없습니다.
              </td>
            </tr>
          ) : (
            pagedCctvs.map((cctv, idx) => {
              const isChecked = selectedIds.includes(cctv.id)
              const handleRowClick = () => {
                if (isChecked) {
                  setSelectedIds(selectedIds.filter(sel => sel !== cctv.id))
                } else {
                  setSelectedIds([...selectedIds, cctv.id])
                }
              }
              return (
                <tr key={cctv.id} style={{ borderBottom: '1px solid #eee' }}>
                  <td style={{ padding: '8px', verticalAlign: 'middle' }}>
                    <input
                      type="checkbox"
                      checked={isChecked}
                      onChange={e => handleCheckboxChange(cctv.id, e.target.checked)}
                      aria-label={`${cctv.location} 선택`}
                    />
                  </td>
                  <td style={{ padding: '8px 12px', verticalAlign: 'middle' }}>
                    {(currentPage - 1) * PAGE_SIZE + idx + 1}
                  </td>
                  <td
                    style={{ padding: '8px 12px', cursor: 'pointer', userSelect: 'none', verticalAlign: 'middle' }}
                    onClick={handleRowClick}
                  >
                    {cctv.location}
                  </td>
                  <td
                    style={{ padding: '8px 12px', cursor: 'pointer', userSelect: 'none', verticalAlign: 'middle' }}
                    onClick={handleRowClick}
                  >
                    {cctv.installedAt}
                  </td>
                </tr>
              )
            })
          )}
        </tbody>
      </table>

      {/* 페이지네이션 및 선택 삭제 버튼 */}
      <div style={{ textAlign: 'right', marginTop: 12 }}>
        <Pagination />
        <button
          onClick={handleDeleteSelected}
          disabled={selectedIds.length === 0}
          style={{
            padding: '10px 18px',
            backgroundColor: selectedIds.length === 0 ? '#ccc' : '#ef4444',
            color: '#fff',
            border: 'none',
            borderRadius: 6,
            fontWeight: 'bold',
            cursor: selectedIds.length === 0 ? 'not-allowed' : 'pointer',
            userSelect: 'none'
          }}
        >
          선택 CCTV 삭제
        </button>
      </div>
    </div>
  )
}

export default CctvManagement