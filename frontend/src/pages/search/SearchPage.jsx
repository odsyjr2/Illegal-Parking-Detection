import React, { useState } from 'react'

// 상태 색상 매핑
const statusColorMap = {
  접수: '#f59e0b',
  처리중: '#3b82f6',
  완료: '#10b981'
}

// 필터 옵션들
const STATUS_OPTIONS = ['전체', '접수', '처리중', '완료']
const REGION_OPTIONS = ['전체', '강남', '관악', '송파', '기타']
const DATE_OPTIONS = ['전체', '오늘', '이번주', '이번달']

// 날짜 필터 유틸 함수
const isDateInRange = (reportDateStr, filter) => {
  const reportDate = new Date(reportDateStr)
  const today = new Date()

  const normalize = (date) => new Date(date.getFullYear(), date.getMonth(), date.getDate())
  const normalizedReportDate = normalize(reportDate)
  const normalizedToday = normalize(today)

  switch (filter) {
    case '오늘':
      return normalizedReportDate.getTime() === normalizedToday.getTime()

    case '이번주': {
      const day = today.getDay()
      const startOfWeek = normalize(new Date(today.setDate(today.getDate() - day)))
      const endOfWeek = new Date(startOfWeek)
      endOfWeek.setDate(startOfWeek.getDate() + 6)
      return normalizedReportDate >= startOfWeek && normalizedReportDate <= endOfWeek
    }

    case '이번달':
      return (
        reportDate.getFullYear() === today.getFullYear() &&
        reportDate.getMonth() === today.getMonth()
      )

    default:
      return true
  }
}

function SearchPage({ reports }) {
  // ✅ 임시 데이터 (DB 없을 경우 대체)
  const fallbackReports = [
    {
      id: 1,
      title: '불법 주차 신고',
      content: '횡단보도에 차량이 주차되어 있습니다.',
      status: '접수',
      region: '관악',
      location: '서울 관악구 남부순환로',
      date: '2025-07-21'
    },
    {
      id: 2,
      title: '도로 파손',
      content: '강남대로 도로 포장 파손',
      status: '처리중',
      region: '강남',
      location: '서울 강남구 테헤란로',
      date: '2025-07-19'
    },
    {
      id: 3,
      title: '음식물 쓰레기 무단 투기',
      content: '송파구 골목길에 음식물 쓰레기 무단 투기',
      status: '완료',
      region: '송파',
      location: '서울 송파구 가락로',
      date: '2025-07-15'
    }
  ]

  const reportList = Array.isArray(reports) && reports.length > 0 ? reports : fallbackReports

  // 상태 관리
  const [query, setQuery] = useState('')
  const [status, setStatus] = useState('전체')
  const [region, setRegion] = useState('전체')
  const [date, setDate] = useState('전체')

  // 필터링
  const filteredReports = reportList.filter(report =>
    (status === '전체' || report.status === status) &&
    (region === '전체' || report.region === region) &&
    (date === '전체' || isDateInRange(report.date, date)) &&
    (query === '' || report.title.toLowerCase().includes(query.toLowerCase()) || report.content?.toLowerCase().includes(query.toLowerCase()))
  )

  return (
    <div style={{
      backgroundColor: '#f0f2f5', // 전체 배경
      minHeight: '100vh',
      paddingTop: 40,
      paddingBottom: 40,
      display: 'flex',
      justifyContent: 'center'
    }}>
      <div style={{
        maxWidth: 1000,
        width: '100%',
        backgroundColor: '#fff',
        padding: 24,
        borderRadius: 12,
        boxShadow: '0 4px 16px rgba(0,0,0,0.05)'
      }}>
        {/* 🔍 검색창 */}
        <input
          type="text"
          placeholder="검색어를 입력하세요"
          value={query}
          onChange={e => setQuery(e.target.value)}
          style={{ width: '90%', padding: 12, marginBottom: 20, fontSize: 18 }}
        />

        {/* ✅ 필터 그룹 */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: 18, marginBottom: 30 }}>
          <FilterGroup title="처리상태" options={STATUS_OPTIONS} selected={status} onSelect={setStatus} />
          <FilterGroup title="지역" options={REGION_OPTIONS} selected={region} onSelect={setRegion} />
          <FilterGroup title="날짜" options={DATE_OPTIONS} selected={date} onSelect={setDate} />
        </div>

        {/* 📄 신고 카드 리스트 */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
          {filteredReports.length === 0 ? (
            <p style={{ color: '#888', textAlign: 'center' }}>신고 내역이 없습니다.</p>
          ) : (
            filteredReports.map(report => (
              <div
                key={report.id}
                style={{
                  background: '#fff',
                  borderRadius: 12,
                  boxShadow: '0 2px 8px rgba(0,0,0,0.06)',
                  padding: '16px 14px',
                  display: 'flex',
                  flexDirection: 'column',
                  gap: 8
                }}
              >
                <div>
                  <strong>{report.title}</strong>
                  <span style={{
                    marginLeft: 8,
                    padding: '2px 10px',
                    background: '#f0f4ff',
                    borderRadius: 12,
                    fontSize: 13,
                    color: statusColorMap[report.status] || '#333'
                  }}>{report.status}</span>
                </div>
                <div style={{ fontSize: 14, color: '#666' }}>
                  위치: {report.location}
                </div>
                <div style={{ fontSize: 13, color: '#999', display: 'flex', gap: 12 }}>
                  <span>지역: {report.region}</span>
                  <span>날짜: {report.date}</span>
                </div>
              </div>
            ))
          )}
        </div>
      </div>
    </div>
  )
}

export default SearchPage

// ✅ 공통 필터 버튼 그룹
function FilterGroup({ title, options, selected, onSelect }) {
  return (
    <div>
      <strong>{title}:</strong>
      <div style={{ marginTop: 6, display: 'flex', flexWrap: 'wrap', gap: 8 }}>
        {options.map(opt => (
          <button
            key={opt}
            onClick={() => onSelect(opt)}
            style={{
              background: selected === opt ? '#4e84ff' : '#eee',
              color: selected === opt ? '#fff' : '#333',
              border: 'none',
              borderRadius: 16,
              padding: '6px 14px',
              cursor: 'pointer'
            }}
          >
            {opt}
          </button>
        ))}
      </div>
    </div>
  )
}