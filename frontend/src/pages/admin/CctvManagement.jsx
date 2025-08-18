import React, { useState, useEffect, useMemo } from 'react'
import './CctvManagement.css'  // 분리한 CSS 임포트

const PAGE_SIZE = 15
const KAKAO_REST_API_KEY = '9fabbd28c079827af4ab0436f07293ec'

function CctvManagement() {
  const [cctvs, setCctvs] = useState([])
  const [loading, setLoading] = useState(false)

  const [newLatitude, setNewLatitude] = useState('')
  const [newLongitude, setNewLongitude] = useState('')
  const [newLocation, setNewLocation] = useState('')
  const [newStreamUrl, setNewStreamUrl] = useState('')

  const [searchText, setSearchText] = useState('')
  const [filterZone, setFilterZone] = useState('전체')
  const [selectedIds, setSelectedIds] = useState([])
  const [currentPage, setCurrentPage] = useState(1)
  const [newInstallationDate, setNewInstallationDate] = useState('');

  // 카카오 정방향 지오코딩 (주소 → 좌표)
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

  // 카카오 역지오코딩 (좌표 → 주소)
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

  // 카카오 주소검색 팝업 열기 함수 (optional, 본인이 원하면 사용)
  function openAddressPopup(onComplete) {
    if (!window.daum) {
      alert('카카오 주소검색 스크립트가 로드되지 않았습니다.')
      return
    }
    new window.daum.Postcode({
      oncomplete: function(data) {
        onComplete(data.address)
      },
    }).open()
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
      } catch {
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
    return cctvs.filter((cctv) => {
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

  // 위도/경도 변경 시 역지오코딩으로 주소 자동 갱신
  useEffect(() => {
    const lat = parseFloat(newLatitude)
    const lng = parseFloat(newLongitude)
    if (isNaN(lat) || isNaN(lng)) return
    reverseGeocode(lat, lng)
      .then(addr => setNewLocation(addr))
      .catch(() => {})
  }, [newLatitude, newLongitude])

  // 선택 토글
  const toggleRowSelection = (id) => {
    setSelectedIds((prev) =>
      prev.includes(id) ? prev.filter((sid) => sid !== id) : [...prev, id]
    )
  }

  // 체크박스 변경
  const handleCheckboxChange = (id, checked) => {
    setSelectedIds((prev) =>
      checked ? [...prev, id] : prev.filter((sid) => sid !== id)
    )
  }

  // 신규 CCTV 추가
  const handleAddCctv = async () => {
    const locationTrim = newLocation.trim()
    const latTrim = newLatitude.trim()
    const lngTrim = newLongitude.trim()
    const dateTrim = newInstallationDate.trim();
    const urlTrim = newStreamUrl.trim()

    if (!locationTrim) {
      alert('도로명주소를 입력하거나 주소검색으로 선택하세요.')
      return
    }
    if (!dateTrim) {
      alert('설치일을 선택하세요.');
      return;
    }
    if (!urlTrim) {
      alert('스트리밍 URL을 입력하세요.')
      return
    }

    let latitude = parseFloat(latTrim)
    let longitude = parseFloat(lngTrim)

    try {
      if (isNaN(latitude) || isNaN(longitude)) {
        const coords = await forwardGeocode(locationTrim)
        latitude = coords.latitude
        longitude = coords.longitude
      }

      if (!locationTrim || isNaN(latitude) || isNaN(longitude)) {
        alert('유효한 도로명주소 및 위도/경도를 입력하세요.')
        return
      }
      const payload = { location: locationTrim, latitude, longitude, installationDate: newInstallationDate, streamUrl: urlTrim,}
      const res = await fetch('http://localhost:8080/api/cctvs', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      })
      if (!res.ok) throw new Error('추가 실패')

      const addedCctv = await res.json()
      setCctvs((prev) => [...prev, addedCctv])

      setNewLocation('')
      setNewLatitude('')
      setNewLongitude('')
      setCurrentPage(totalPages)
      setNewInstallationDate('')
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
        selectedIds.map((id) =>
          fetch(`http://localhost:8080/api/cctvs/${id}`, { method: 'DELETE' })
        )
      )
      setCctvs((prev) => prev.filter((c) => !selectedIds.includes(c.id)))
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
    if (totalPages <= 0) return null
    const pages = [...Array(totalPages).keys()].map(i => i + 1)
    return (
      <div className="pagination-container">
        <button
          className={`pag-btn ${currentPage === 1 ? 'disabled' : ''}`}
          onClick={() => goToPage(currentPage - 1)}
          disabled={currentPage === 1}
          aria-label="이전 페이지"
        >
          &lt;
        </button>

        {pages.map(page => (
          <button
            key={page}
            className={`pag-btn ${page === currentPage ? 'active' : ''}`}
            onClick={() => goToPage(page)}
            aria-current={page === currentPage ? 'page' : undefined}
          >
            {page}
          </button>
        ))}

        <button
          className={`pag-btn ${currentPage === totalPages ? 'disabled' : ''}`}
          onClick={() => goToPage(currentPage + 1)}
          disabled={currentPage === totalPages}
          aria-label="다음 페이지"
        >
          &gt;
        </button>
      </div>
    )
  }

  return (
    <div className="cctv-container">
      <div className="header-area">
        <h2>📹 CCTV 관리</h2>
        <div className="search-filter-area">
          <input
            type="text"
            placeholder="위치명으로 검색"
            value={searchText}
            onChange={(e) => setSearchText(e.target.value)}
            className="search-input"
          />
          <select
            value={filterZone}
            onChange={(e) => setFilterZone(e.target.value)}
            className="zone-select"
          >
            <option value="전체">전체</option>
            <option value="관악구">관악구</option>
            <option value="강남구">강남구</option>
            <option value="서초구">서초구</option>
          </select>
        </div>
      </div>

      <div className="new-cctv-input-area">
        <input
          type="text"
          placeholder="도로명 주소 (예: 서초동 123)"
          value={newLocation}
          onChange={(e) => setNewLocation(e.target.value)}
          className="location-input"
        />
        <button
          type="button"
          onClick={() => openAddressPopup(setNewLocation)}
          className="address-search-button"
        >
          주소검색
        </button>
        <input
          type="text"
          placeholder="URL (예: http:// ... )"
          value={newStreamUrl}
          onChange={(e) => setNewStreamUrl(e.target.value)}
          className="lat-lng-input"
        />
        <label>
          설치일:
          <input
            type="date"
            value={newInstallationDate}
            onChange={(e) => setNewInstallationDate(e.target.value)}
            className="lat-lng-input"
          />
        </label>
        <button onClick={handleAddCctv} className="add-button" aria-label="새 CCTV 추가">
          + 추가
        </button>
      </div>
        <input
          type="text"
          placeholder="위도 (예: 37.123456)"
          value={newLatitude}
          onChange={(e) => setNewLatitude(e.target.value)}
          className="lat-lng-input"
        />
        <input
          type="text"
          placeholder="경도 (예: 127.123456)"
          value={newLongitude}
          onChange={(e) => setNewLongitude(e.target.value)}
          className="lat-lng-input"
        />

      {loading && <p className="loading-text">데이터 로딩 중...</p>}

      <table className="cctv-table">
        <thead>
          <tr>
            <th style={{ width: 40 }}></th>
            <th style={{ width: 40 }}>번호</th>
            <th>위치</th>
            <th style={{ width: 130 }}>설치일</th>
          </tr>
        </thead>
        <tbody>
          {pagedCctvs.length === 0 ? (
            <tr>
              <td colSpan={4} className="empty-text">
                검색 결과가 없습니다.
              </td>
            </tr>
          ) : (
            pagedCctvs.map((cctv, idx) => {
              const isChecked = selectedIds.includes(cctv.id)
              const handleRowClick = () => toggleRowSelection(cctv.id)
              return (
                <tr
                  key={cctv.id}
                  className="cctv-row"
                  onClick={handleRowClick}
                >
                  <td>
                    <input
                      type="checkbox"
                      checked={isChecked}
                      onChange={(e) => handleCheckboxChange(cctv.id, e.target.checked)}
                      aria-label={`${cctv.location} 선택`}
                      onClick={e => e.stopPropagation()}
                    />
                  </td>
                  <td>{(currentPage - 1) * PAGE_SIZE + idx + 1}</td>
                  <td>{cctv.location}</td>
                  <td>{cctv.installationDate || '-'}</td>
                </tr>
              )
            })
          )}
        </tbody>
      </table>

      <div className="pagination-delete-area">
        <Pagination />
        <button
          onClick={handleDeleteSelected}
          disabled={selectedIds.length === 0}
          className="delete-button"
          aria-label="선택 CCTV 삭제"
        >
          선택 CCTV 삭제
        </button>
      </div>
    </div>
  )
}

export default CctvManagement