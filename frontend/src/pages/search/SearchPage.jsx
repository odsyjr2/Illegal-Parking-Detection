import React, { useState, useEffect } from 'react';
import axios from 'axios';

const statusColorMap = {
  접수: '#f59e0b',
  진행중: '#3b82f6',
  완료: '#10b981'
};

const STATUS_OPTIONS = ['전체', '접수', '진행중', '완료'];
const DATE_OPTIONS = ['전체', '오늘', '이번주', '이번달'];

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
      const day = today.getDay();
      const startOfWeek = normalize(new Date(today.getFullYear(), today.getMonth(), today.getDate() - day));
      const endOfWeek = new Date(startOfWeek);
      endOfWeek.setDate(startOfWeek.getDate() + 6);
      return normalizedReportDate >= startOfWeek && normalizedReportDate <= endOfWeek;
    }
    case '이번달':
      return reportDate.getFullYear() === today.getFullYear() && reportDate.getMonth() === today.getMonth();
    default:
      return true;
  }
};

function SearchPage() {
  const [reports, setReports] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const [query, setQuery] = useState('');
  const [status, setStatus] = useState('전체');
  const [region, setRegion] = useState('전체');
  const [date, setDate] = useState('전체');

  useEffect(() => {
    setLoading(true);
    axios.get('http://localhost:8080/api/human-reports')
      .then(res => {
        const mapped = res.data.map(item => ({
          id: item.id,
          title: item.title || '',
          content: item.reason || '',
          status: item.status || '접수',
          region: item.region || '기타',
          location: item.location || '',
          imageURL: item.imageURL || '',
          date: item.createdAt ? item.createdAt.slice(0, 10) : ''
        }));
        setReports(mapped);
      })
      .catch(err => {
        console.error(err);
        setError('신고 목록을 불러오는데 실패했습니다.');
        setReports([]);
      })
      .finally(() => setLoading(false));
  }, []);

    // 지역 필터 옵션을 reports 데이터에서 구 이름으로 동적 생성
  const regionOptions = React.useMemo(() => {
    const regionsSet = new Set();
    reports.forEach(report => {
      if (report.region) {
        // "00구 00동" -> "00구"만 추출
        const district = report.region.split(' ')[0] || '기타';
        regionsSet.add(district);
      }
    });
    return ['전체', ...Array.from(regionsSet)];
  }, [reports]);

  const filteredReports = reports.filter(report => {
    const reportDistrict = report.region ? report.region.split(' ')[0] : '기타';
    return (
      (status === '전체' || report.status === status) &&
      (region === '전체' || reportDistrict === region) &&
      (date === '전체' || isDateInRange(report.date, date)) &&
      (query === '' ||
        report.title.toLowerCase().includes(query.toLowerCase()) ||
        report.content.toLowerCase().includes(query.toLowerCase()))
    );
  });

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
        <input
          type="text"
          placeholder="검색어를 입력하세요"
          value={query}
          onChange={e => setQuery(e.target.value)}
          style={{ width: '90%', padding: 12, marginBottom: 20, fontSize: 18 }}
        />

        <div style={{ display: 'flex', flexDirection: 'column', gap: 18, marginBottom: 30 }}>
          <FilterGroup title="처리상태" options={STATUS_OPTIONS} selected={status} onSelect={setStatus} />
          <FilterGroup title="지역" options={regionOptions} selected={region} onSelect={setRegion} />
          <FilterGroup title="날짜" options={DATE_OPTIONS} selected={date} onSelect={setDate} />
        </div>

        {loading && <p style={{textAlign: 'center'}}>로딩 중...</p>}
        {error && <p style={{color: '#f44336', textAlign: 'center'}}>{error}</p>}

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
                {report.imageURL && (
                  <img
                    src={`http://localhost:8080${report.imageURL}`}
                    alt="신고 이미지"
                    style={{ width: 160, borderRadius: 8 }}
                  />
                )}
                <div style={{ fontSize: 15, color: '#444' }}>{report.content}</div>
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
  );
}
