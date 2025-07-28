import React, { useState, useEffect } from 'react';

// 상태 색상 매핑
const statusColorMap = {
  접수: '#f59e0b',
  처리중: '#3b82f6',
  완료: '#10b981'
};

// 필터 옵션들
const STATUS_OPTIONS = ['전체', '접수', '처리중', '완료'];
const REGION_OPTIONS = ['전체', '강남', '관악', '송파', '기타'];
const DATE_OPTIONS = ['전체', '오늘', '이번주', '이번달'];

// 날짜 필터 유틸 함수
const isDateInRange = (reportDateStr, filter) => {
  if (!reportDateStr) return false;
  const reportDate = new Date(reportDateStr);
  const today = new Date();

  const normalize = (date) => new Date(date.getFullYear(), date.getMonth(), date.getDate());
  const normalizedReportDate = normalize(reportDate);
  const normalizedToday = normalize(today);

  switch (filter) {
    case '오늘':
      return normalizedReportDate.getTime() === normalizedToday.getTime();

    case '이번주': {
      const day = today.getDay(); // 0 (일) ~ 6 (토)
      // 이번주 일요일
      const startOfWeek = normalize(new Date(today.getFullYear(), today.getMonth(), today.getDate() - day));
      const endOfWeek = new Date(startOfWeek);
      endOfWeek.setDate(startOfWeek.getDate() + 6);
      return normalizedReportDate >= startOfWeek && normalizedReportDate <= endOfWeek;
    }

    case '이번달':
      return (
        reportDate.getFullYear() === today.getFullYear() &&
        reportDate.getMonth() === today.getMonth()
      );

    default:
      return true;
  }
};

function SearchPage() {
  // 내부 state로 관리 (서버에서 데이터 받아와 세팅)
  const [reports, setReports] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  // 필터 상태
  const [query, setQuery] = useState('');
  const [status, setStatus] = useState('전체');
  const [region, setRegion] = useState('전체');
  const [date, setDate] = useState('전체');

  // 서버에서 신고 목록 가져오기
  useEffect(() => {
    setLoading(true);
    setError(null);
    fetch('/api/human-reports')
      .then(res => {
        if (!res.ok) throw new Error(`서버 오류: ${res.status}`);
        return res.json();
      })
      .then(data => {
        // Backend에서 받은 데이터에 title, status, region, location, date 이름 맞춰 변환 필요하면 아래처럼 처리
        // 여기서는 date가 없으면 createdAt을 date로 매핑 예시도 가능
        const mapped = data.map(item => ({
          id: item.id,
          title: item.title || '',
          content: item.reason || '',
          status: item.status || '',
          region: item.region || '기타',
          location: item.location || '',
          date: item.createdAt ? item.createdAt.slice(0, 10) : '' // 날짜 문자열 (YYYY-MM-DD)만 추출
        }));
        setReports(mapped);
      })
      .catch(err => {
        console.error(err);
        setError('신고 목록을 불러오는데 실패했습니다.');
        setReports([]); // fallback 데이터 쓸 수도 있음
      })
      .finally(() => setLoading(false));
  }, []);

  // 필터링 적용
  const filteredReports = reports.filter(report =>
    (status === '전체' || report.status === status) &&
    (region === '전체' || report.region === region) &&
    (date === '전체' || isDateInRange(report.date, date)) &&
    (query === '' ||
      report.title.toLowerCase().includes(query.toLowerCase()) ||
      report.content.toLowerCase().includes(query.toLowerCase()))
  );

  return (
    <div style={{
      backgroundColor: '#f0f2f5',
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
        {/* 검색창 */}
        <input
          type="text"
          placeholder="검색어를 입력하세요"
          value={query}
          onChange={e => setQuery(e.target.value)}
          style={{ width: '90%', padding: 12, marginBottom: 20, fontSize: 18 }}
        />

        {/* 필터 그룹 */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: 18, marginBottom: 30 }}>
          <FilterGroup title="처리상태" options={STATUS_OPTIONS} selected={status} onSelect={setStatus} />
          <FilterGroup title="지역" options={REGION_OPTIONS} selected={region} onSelect={setRegion} />
          <FilterGroup title="날짜" options={DATE_OPTIONS} selected={date} onSelect={setDate} />
        </div>

        {/* 상태 표시 및 에러 */}
        {loading && <p style={{textAlign: 'center'}}>로딩 중...</p>}
        {error && <p style={{color: '#f44336', textAlign: 'center'}}>{error}</p>}

        {/* 신고 카드 리스트 */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
          {filteredReports.length === 0 && !loading ? (
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
  );
}

export default SearchPage;

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