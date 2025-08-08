import React from 'react'
import { Bar, Line } from 'react-chartjs-2'

function InfoPanel({ selectedLocation, onLocationChange }) {
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
  }
  const weeklyStats = [
    { day: '월', detected: 10, abnormal: 2 },
    { day: '화', detected: 11, abnormal: 0 },
    { day: '수', detected: 8, abnormal: 1 },
    { day: '목', detected: 13, abnormal: 3 },
    { day: '금', detected: 9, abnormal: 1 },
    { day: '토', detected: 15, abnormal: 0 },
    { day: '일', detected: 12, abnormal: 2 },
  ]
  const timeRangeStatus = [
    { range: '00~06시', count: 3 },
    { range: '06~12시', count: 7 },
    { range: '12~18시', count: 5 },
    { range: '18~24시', count: 8 },
  ]
  const sectionStatus = [
    { section: '1구역', detected: 4, abnormal: 1 },
    { section: '2구역', detected: 5, abnormal: 0 },
    { section: '3구역', detected: 2, abnormal: 1 },
  ]
  const locations = [
    { label: '강남구', lat: 37.5172, lng: 127.0473 },
    { label: '관악구', lat: 37.4784, lng: 126.9516 },
    { label: '송파구', lat: 37.5145, lng: 127.1056 },
  ]
  const curLabel = selectedLocation?.label
  const displayInfo = locationStatus[curLabel] || [
    { label: '감지 차량 수', value: '-' },
    { label: '비정상 주차', value: '-' },
    { label: '최근 알림', value: '-' },
  ]

  const weeklyBarData = {
    labels: weeklyStats.map(s => s.day),
    datasets: [
      { label: '감지 차량 수', data: weeklyStats.map(s => s.detected), backgroundColor: '#3b82f6' },
      { label: '비정상 주차', data: weeklyStats.map(s => s.abnormal), backgroundColor: '#ef4444' }
    ]
  }
  const weeklyBarOptions = {
    responsive: true,
    plugins: { legend: { position: 'top', labels: { font: { size: 13 } } } },
    scales: { x: { stacked: true }, y: { stacked: true, beginAtZero: true, stepSize: 1 } },
    maintainAspectRatio: false,
  }
  const timeLineData = {
    labels: timeRangeStatus.map(t => t.range),
    datasets: [{
      label: '신고 건수',
      data: timeRangeStatus.map(t => t.count),
      fill: true,
      borderColor: '#3b82f6',
      backgroundColor: 'rgba(59,130,246,0.3)',
      tension: 0.3,
      pointRadius: 5,
    }]
  }
  const timeLineOptions = {
    responsive: true,
    plugins: { legend: { display: false } },
    scales: { y: { beginAtZero: true, stepSize: 1 } },
    maintainAspectRatio: false,
  }

  return (
    <div style={{ position: 'relative', fontFamily: "'Noto Sans KR', sans-serif", fontSize: 14, color: '#333', height: '100%' }}>

      {/* 실시간 현황 */}
      <div style={{
        background: '#f9fafb',
        borderRadius: 14,
        padding: '20px 24px',
        boxShadow: '0 2px 12px rgba(0,0,0,0.1)',
        marginBottom: '1.5rem',
      }}>

        {/* 주간 통계 그래프 */}
        <h4 style={{ margin: '0 0 16px 0', fontWeight: '700', color: '#222' }}>주간 통계</h4>
        <div style={{ height: 200 }}>
          <Bar data={weeklyBarData} options={weeklyBarOptions} />
        </div>
      </div>

      {/* 시간대별 현황 그래프 */}
      <div style={{
        background: '#fff',
        borderRadius: 14,
        padding: '18px 24px',
        boxShadow: '0 2px 12px rgba(0,0,0,0.1)',
        marginBottom: '1.5rem',
        height: 220,
      }}>
        <h4 style={{ margin: '0 0 16px 0', fontWeight: '700', color: '#222' }}>시간대별 현황</h4>
        <div style={{ height: 140 }}>
          <Line data={timeLineData} options={timeLineOptions} />
        </div>
      </div>
        <h3 style={{ margin: '0 0 10px 0', color: '#222', fontWeight: '700' }}>실시간 현황</h3>
        <ul style={{ listStyle: 'none', padding: 0, marginBottom: '20px', display: 'flex', gap: '24px' }}>
          {displayInfo.map((item, idx) => (
            <li key={idx} style={{
              flex: 1,
              background: '#fff',
              borderRadius: 16,
              padding: '18px 20px',
              boxShadow: '0 3px 8px rgba(0,0,0,0.12)',
              textAlign: 'center',
            }}>
              <div style={{ fontWeight: 700, fontSize: 20, color: '#2563eb' }}>{item.value}</div>
              <div style={{ marginTop: 6, fontSize: 14, color: '#555' }}>{item.label}</div>
            </li>
          ))}
        </ul>

      {/* 시단개별 현황 */}
      <div style={{ marginTop: '1rem' }}>
        <h4 style={{ marginBottom: 14, color: '#222', fontWeight: '700' }}>시단개별 현황</h4>
        <ul style={{ listStyle: 'none', paddingLeft: 0, margin: 0 }}>
          {sectionStatus.map((section, idx) => (
            <li key={idx} style={{
              padding: '12px 0',
              borderBottom: idx !== sectionStatus.length - 1 ? '1px solid #eee' : 'none',
              fontSize: 14,
              color: '#444',
              display: 'flex',
              justifyContent: 'space-between',
              maxWidth: 300,
            }}>
              <span><b>{section.section}</b></span>
              <span>
                감지 <span style={{ color: '#2563eb', fontWeight: '700' }}>{section.detected}</span> /
                비정상 <span style={{ color: '#ef4444', fontWeight: '700' }}>{section.abnormal}</span>
              </span>
            </li>
          ))}
        </ul>
      </div>
    </div>
  )
}

export default InfoPanel