import React, { useState, useEffect, useMemo } from 'react'

const ZONES = ['전체', '관악구', '강남구', '서초구']
const PAGE_SIZE = 15

const KAKAO_REST_API_KEY = '9fabbd28c079827af4ab0436f07293ec'

function CctvManagement() {
  const [cctvs, setCctvs] = useState([])
  const [loading, setLoading] = useState(false)

  const [newLatitude, setNewLatitude] = useState('')
  const [newLongitude, setNewLongitude] = useState('')
  const [newLocation, setNewLocation] = useState('')

  const [searchText, setSearchText] = useState('')
  const [filterZone, setFilterZone] = useState('전체')
  const [selectedIds, setSelectedIds] = useState([])
  const [currentPage, setCurrentPage] = useState(1)

  // 카카오 정방향 지오코딩 (주소 -> 좌표)
  async function forwardGeocode(address) {
    const url = `https://dapi.kakao.com/v2/local/search/address.json?query=${encodeURIComponent(address)}`
    const res = await fetch(url, {
      headers: { Authorization: `KakaoAK ${KAKAO_REST_API_KEY}` },
    })
    if (!res.ok) throw new Error('주소 변환 실패')
    const data = await res.json()
    if (!data.documents.length) throw new Error('유효한 주소를 찾을 수 없습니다')
    const loc = data.documents[0]
    return {
      latitude: parseFloat(loc.y),
      longitude: parseFloat(loc.x),
    }
  }

  // 카카오 역지오코딩 (좌표 -> 주소)
  async function reverseGeocode(lat, lng) {
    const url = `https://dapi.kakao.com/v2/local/geo/coord2address.json?x=${lng}&y=${lat}`
    const res = await fetch(url, {
      headers: { Authorization: `KakaoAK ${KAKAO_REST_API_KEY}` },
    })
    if (!res.ok) throw new Error('역지오코딩 실패')
    const data = await res.json()
    if (!data.documents.length) throw new Error('주소를 찾을 수 없습니다')
    return (
      data.documents[0].road_address?.address_name ||
      data.documents[0].address?.address_name ||
      '주소 정보 없음'
    )
  }

  // CCTV 목록 불러오기
  useEffect(() => {
    async function fetchCctvs() {
      setLoading(true)
      try {
        const res = await fetch('http://localhost:8080/api/cctvs')
        if (!res.ok) throw new Error('CCTV 목록 불러오기 실패')
        const data = await res.json()
        setCctvs(data)
      } catch (e) {
        alert('CCTV 목록을 불러오는 데 실패했습니다.')
      } finally {
        setLoading(false)
      }
    }
    fetchCctvs()
  }, [])

  // 필터링
  const filteredCctvs = useMemo(() => {
    const lowerSearch = searchText.toLowerCase()
    return cctvs.filter(cctv => {
      if (filterZone !== '전체' && !cctv.location.includes(filterZone)) return false
      if (!cctv.location.toLowerCase().includes(lowerSearch)) return false
      return true
    })
  }, [cctvs, searchText, filterZone])

  // 페이징
  const totalPages = Math.ceil(filteredCctvs.length / PAGE_SIZE) || 1
  const pagedCctvs = useMemo(() => {
    const startIdx = (currentPage - 1) * PAGE_SIZE
    return filteredCctvs.slice(startIdx, startIdx + PAGE_SIZE)
  }, [filteredCctvs, currentPage])

  useEffect(() => {
    if (currentPage > totalPages) {
      setCurrentPage(totalPages)
      setSelectedIds([])
    }
  }, [totalPages, currentPage])

  // 선택 토글
  const toggleRowSelection = (id) => {
    setSelectedIds(prev =>
      prev.includes(id) ? prev.filter(sid => sid !== id) : [...prev, id]
    )
  }

  // 체크박스 체인지
  const handleCheckboxChange = (id, checked) => {
    setSelectedIds(prev =>
      checked ? [...prev, id] : prev.filter(sid => sid !== id)
    )
  }

  // CCTV 신규 추가 (위치 또는 위도/경도 중 하나만 입력해도 작동)
  const handleAddCctv = async () => {
    const locationTrim = newLocation.trim()
    const latTrim = newLatitude.trim()
    const lngTrim = newLongitude.trim()

    if (!locationTrim && (!latTrim || !lngTrim)) {
      alert('도로명주소 또는 위도/경도 중 하나 이상 입력하세요.')
      return
    }

    let latitude = parseFloat(latTrim)
    let longitude = parseFloat(lngTrim)
    let location = locationTrim

    try {
      // 주소만 있고 좌표가 없거나 잘못된 경우 → 좌표 변환
      if (location && (isNaN(latitude) || isNaN(longitude))) {
        const coords = await forwardGeocode(location)
        latitude = coords.latitude
        longitude = coords.longitude
      }

      // 좌표만 있고 주소 없으면 → 주소 변환
      if (!location && !isNaN(latitude) && !isNaN(longitude)) {
        location = await reverseGeocode(latitude, longitude)
      }

      if (!location || isNaN(latitude) || isNaN(longitude)) {
        alert('유효한 도로명주소 또는 위도/경도를 입력하세요.')
        return
      }

      const payload = { location, latitude, longitude }

      const res = await fetch('http://localhost:8080/api/cctvs', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      })
      if (!res.ok) throw new Error('추가 실패')

      const addedCctv = await res.json()
      setCctvs(prev => [...prev, addedCctv])

      setNewLocation('')
      setNewLatitude('')
      setNewLongitude('')
      setCurrentPage(totalPages) // 마지막 페이지 이동
    } catch (e) {
      alert('CCTV 추가에 실패했습니다: ' + e.message)
    }
  }

  // CCTV 삭제
  const handleDeleteSelected = async () => {
    if (selectedIds.length === 0) {
      alert('삭제할 CCTV를 하나 이상 선택하세요.')
      return
    }
    if (!window.confirm(`선택한 CCTV ${selectedIds.length}개를 삭제하시겠습니까?`)) return

    try {
      await Promise.all(
        selectedIds.map(id =>
          fetch(`http://localhost:8080/api/cctvs/${id}`, { method: 'DELETE' })
        )
      )
      setCctvs(prev => prev.filter(c => !selectedIds.includes(c.id)))
      setSelectedIds([])
    } catch {
      alert('삭제 중 오류가 발생했습니다.')
    }
  }

  // 페이지 변경
  const goToPage = (page) => {
    if (page < 1 || page > totalPages) return
    setCurrentPage(page)
    setSelectedIds([])
  }

  // 페이지네이션 스타일
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
    <div style={{ background: '#fff', padding: 20, borderRadius: 10, margin: '20px auto'}}>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 16, gap: 12 }}>
        <h2>📹 CCTV 관리</h2>
        {/* 검색 + 구역 선택 */}
        <div style={{ display: 'flex', gap: 12, minWidth: 320 }}>
          <input
            type="text"
            placeholder="위치명으로 검색"
            value={searchText}
            onChange={e => setSearchText(e.target.value)}
            style={{
              flex: 1,
              padding: '8px 12px',
              borderRadius: 6,
              border: '1px solid #ccc',
              fontSize: 14,
              boxSizing: 'border-box',
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
              boxSizing: 'border-box',
            }}
          >
            {ZONES.map(zone => (
              <option key={zone} value={zone}>{zone}</option>
            ))}
          </select>
        </div>
      </div>

      {/* 신규 CCTV 입력 */}
      <div style={{ display: 'flex', gap: 8, marginBottom: 16 }}>
        <input
          type="text"
          placeholder="CCTV 위치 (예: 서초동 123)"
          value={newLocation}
          onChange={e => setNewLocation(e.target.value)}
          style={{
            flex: 2,
            padding: '8px 12px',
            borderRadius: 6,
            border: '1px solid #ccc',
            fontSize: 14,
            boxSizing: 'border-box',
          }}
        />
        <input
          type="text"
          placeholder="위도 (예: 37.123456)"
          value={newLatitude}
          onChange={e => setNewLatitude(e.target.value)}
          style={{
            flex: 1,
            padding: '8px 12px',
            borderRadius: 6,
            border: '1px solid #ccc',
            fontSize: 14,
            boxSizing: 'border-box',
          }}
        />
        <input
          type="text"
          placeholder="경도 (예: 127.123456)"
          value={newLongitude}
          onChange={e => setNewLongitude(e.target.value)}
          style={{
            flex: 1,
            padding: '8px 12px',
            borderRadius: 6,
            border: '1px solid #ccc',
            fontSize: 14,
            boxSizing: 'border-box',
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
            userSelect: 'none',
          }}
          aria-label="새 CCTV 추가"
        >
          + 추가
        </button>
      </div>

      {/* 로딩 표시 */}
      {loading && <p style={{ marginBottom: 12 }}>데이터 로딩 중...</p>}

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
              const handleRowClick = () => toggleRowSelection(cctv.id)
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

      {/* 페이지네이션 및 삭제 버튼 */}
      <div style={{ textAlign: 'right', marginTop: 12 }}>
        <Pagination />
        <button
          onClick={handleDeleteSelected}
          disabled={selectedIds.length === 0}
          style={{
            marginLeft: 12,
            padding: '10px 18px',
            backgroundColor: selectedIds.length === 0 ? '#ccc' : '#ef4444',
            color: '#fff',
            border: 'none',
            borderRadius: 6,
            fontWeight: 'bold',
            cursor: selectedIds.length === 0 ? 'not-allowed' : 'pointer',
            userSelect: 'none',
          }}
          aria-label="선택 CCTV 삭제"
        >
          선택 CCTV 삭제
        </button>
      </div>
    </div>
  )
}

export default CctvManagement