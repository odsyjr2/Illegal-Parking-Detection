function InfoPanel({ selectedLocation, onLocationChange }) {
  // 각 지역별로 상태 정보 준비
  const locationStatus = {
    '강남구': [
      { label: '감지 차량 수', value: 11 },
      { label: '비정상 주차', value: 2 },
      { label: '최근 알림', value: 0 },
    ],
    '관악구': [
      { label: '감지 차량 수', value: 9 },
      { label: '비정상 주차', value: 1 },
      { label: '최근 알림', value: 3 },
    ],
    '송파구': [
      { label: '감지 차량 수', value: 16 },
      { label: '비정상 주차', value: 0 },
      { label: '최근 알림', value: 1 },
    ],
  };

  // 셀렉트 옵션용 위치 목록
  const locations = [
    { label: '강남구', lat: 37.5172, lng: 127.0473 },
    { label: '관악구', lat: 37.4784, lng: 126.9516 },
    { label: '송파구', lat: 37.5145, lng: 127.1056 },
  ];

  // 현황 표시할 지역
  const curLabel = selectedLocation?.label;
  const displayInfo = locationStatus[curLabel] || [
    { label: '감지 차량 수', value: '-' },
    { label: '비정상 주차', value: '-' },
    { label: '최근 알림', value: '-' },
  ];

  return (
    <div>
      {/* 상태 요약 */}
      <div className="info-panel">
        <h3>주요 현황</h3>
        <ul>
          {displayInfo.map((item, idx) => (
            <li key={idx}><b>{item.label}</b>: {item.value}</li>
          ))}
        </ul>
      </div>

      {/* 위치 선택 */}
      <div className="preview-box" style={{ marginTop: '1rem' }}>
        <h4>감시 위치 선택</h4>
        <select
          style={{ width: '100%', padding: '0.5rem' }}
          value={curLabel || ''}
          onChange={(e) => {
            const loc = locations.find(loc => loc.label === e.target.value)
            if (loc) onLocationChange(loc)
          }}
        >
          <option value="">--- 감시 위치 선택 ---</option>
          {locations.map((loc) => (
            <option key={loc.label} value={loc.label}>{loc.label}</option>
          ))}
        </select>

        <div style={{
          background: '#e0e0e0',
          height: 180,
          display: 'flex',
          justifyContent: 'center',
          alignItems: 'center',
          marginTop: 10
        }}>
          <span>{curLabel || '위치 미선택'}</span>
        </div>
      </div>

      {/* 나머지는 그대로 */}
      <div className="control-buttons" style={{ marginTop: '1rem', display: 'flex', gap: '1rem', justifyContent: 'flex-end' }}>
        <button onClick={() => alert('데이터 새로고침')}>새로고침</button>
        <button onClick={() => alert('이상 감지 시작')}>이상감지</button>
      </div>

      <button style={{
        width: '100%',
        padding: '12px',
        backgroundColor: '#0066cc',
        color: '#fff',
        fontWeight: 'bold',
        border: 'none',
        borderRadius: '6px',
        fontSize: '16px',
        cursor: 'pointer',
        marginTop: '20px'
      }}>경로 보기</button>
    </div>
  );
}

export default InfoPanel;
