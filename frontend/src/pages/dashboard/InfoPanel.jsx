import { useEffect, useState, useMemo } from 'react'
import { Bar, Line } from 'react-chartjs-2'
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  BarElement,
  Title,
  Tooltip,
  Legend,
  ArcElement,
  LineElement,
  PointElement
} from 'chart.js'

ChartJS.register(
  CategoryScale,
  LinearScale,
  BarElement,
  Title,
  Tooltip,
  Legend,
  ArcElement,
  LineElement,
  PointElement
)

const korWeekDays = ['일', '월', '화', '수', '목', '금', '토']

function extractRegionName(location) {
  if (!location) return '';
  // '구', '동', '읍', '면'으로 끝나는 문자열 추출 (마지막 값)
  const match = location.match(/([가-힣]+[구|동|읍|면])/g);
  return match ? match[match.length - 1] : '';
}

function InfoPanel({ selectedLocation }) {
  const [rawData, setRawData] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  const todayStr = new Date().toISOString().slice(0, 10)

  // 선택된 위치에서 구/동명 추출
  const regionName = extractRegionName(selectedLocation?.location || '');

  // 현황통계: 해당 지역만 필터
  const locationStatusFromReports = useMemo(() => {
    if (!rawData || !regionName) return [];
    // location에서 구/동명 일치 + 오늘 날짜
    const regionReports = rawData.filter(
      r =>
        r.location &&
        extractRegionName(r.location) === regionName &&
        r.createdAt?.slice(0, 10) === todayStr
    );
    return [
      { label: '감지 차량 수', value: regionReports.length },
      {
        label: '진행중',
        value: regionReports.filter(r => r.status === '진행중').length
      },
      {
        label: '완료',
        value: regionReports.filter(r => r.status === '완료').length
      }
    ];
  }, [rawData, regionName, todayStr]);

  // 최근 7일 날짜 생성
  const dates = useMemo(() => {
    const getDateNDaysAgo = n => {
      const d = new Date()
      d.setDate(d.getDate() - n)
      return d
    }
    const formatDate = date => date.toISOString().slice(0, 10)
    return [...Array(7)].map((_, i) => {
      const d = getDateNDaysAgo(6 - i)
      return formatDate(d)
    })
  }, [])

  useEffect(() => {
    const fetchData = async () => {
      setLoading(true)
      setError(null)
      try {
        const res = await fetch('http://localhost:8080/api/human-reports')
        const data = await res.json()
        setRawData(data)
      } catch (e) {
        setError('데이터를 불러오는 중 오류가 발생했습니다.')
      } finally {
        setLoading(false)
      }
    }
    fetchData()
  }, [])

  // 7일간 날짜별 신고 건수 집계
  const dailyCounts = useMemo(() => {
    if (!rawData) return Array(7).fill(0)
    const dailyMap = {}
    dates.forEach(date => {
      dailyMap[date] = 0
    })
    rawData.forEach(({ createdAt }) => {
      const date = createdAt.slice(0, 10)
      if (dailyMap[date] !== undefined) dailyMap[date]++
    })
    return dates.map(date => dailyMap[date])
  }, [rawData, dates])

  const todayIndex = dates.length - 1
  const todayCount = dailyCounts[todayIndex] || 0
  const maxCount = Math.max(...dailyCounts)
  const avgCount = (dailyCounts.reduce((a, b) => a + b, 0) / dailyCounts.length).toFixed(1)

  // 시간대별 신고 건수 (4구간)
  const timeRanges = [
    { label: '00~06시', start: 0, end: 6 },
    { label: '06~12시', start: 6, end: 12 },
    { label: '12~18시', start: 12, end: 18 },
    { label: '18~24시', start: 18, end: 24 }
  ]
  const timeRangeCounts = useMemo(() => {
    if (!rawData) return Array(4).fill(0)
    const validDates = new Set(dates)
    const counts = [0, 0, 0, 0]
    rawData.forEach(({ createdAt }) => {
      const date = createdAt.slice(0, 10)
      if (!validDates.has(date)) return
      const hour = Number(createdAt.length > 10 ? createdAt.slice(11, 13) : '00')
      const idx = timeRanges.findIndex(r => hour >= r.start && hour < r.end)
      if (idx !== -1) counts[idx]++
    })
    return counts
  }, [rawData, dates])

  const weekLabels = dates.map(d => {
    const dt = new Date(d)
    return `${dt.getDate()}(${korWeekDays[dt.getDay()]})`
  })

  const gridStyle = {
    display: 'grid',
    gridTemplateColumns: '1fr',
    gridTemplateRows: '1fr 1fr',
    gap: 30,
    maxWidth: 700,
    maxHeight: 700,
    height: 'calc(100vh - 70px)',
    margin: '10px auto'
  }

  const bigPanelStyle = {
    gridColumn: '1',
    gridRow: '2',
    background: '#fff',
    borderRadius: 18,
    padding: '10px 30px 24px 30px',
    boxShadow: '0 2px 7px #e8e8e8',
    minHeight: 300,
    display: 'flex',
    flexDirection: 'column',
    justifyContent: 'flex-start'
  }

  const subPanelStyle = {
    gridColumn: '1',
    gridRow: '3',
    background: '#fff',
    borderRadius: 14,
    padding: 20,
    boxShadow: '0 2px 7px #e8e8e8',
    minWidth: 0,
    minHeight: 180,
    display: 'flex',
    flexDirection: 'column',
    alignItems: 'center',
    justifyContent: 'flex-start'
  }

  if (loading) return <div>로딩 중...</div>
  if (error) return <div>{error}</div>

  // 선택된 지역 통계 또는 기본
  const displayItems = locationStatusFromReports.length > 0
    ? locationStatusFromReports
    : [
        { label: '감지 차량 수', value: '-' },
        { label: '진행중', value: '-' },
        { label: '완료', value: '-' }
      ]

  return (
    <div style={gridStyle}>
      {/* 실시간 현황 */}
      <section style={{ gridRow: '1' }}>
        <h3 style={{ margin: '0 0 10px 0', color: '#222', fontWeight: '700' }}>
          실시간 현황{regionName ? ` - ${regionName}` : ''}
        </h3>
        <ul
          style={{
            listStyle: 'none',
            padding: 0,
            marginBottom: '20px',
            display: 'flex',
            gap: '24px'
          }}
        >
          {displayItems.map((item, idx) => (
            <li
              key={idx}
              style={{
                flex: 1,
                background: '#fff',
                borderRadius: 16,
                padding: '18px 20px',
                boxShadow: '0 3px 8px rgba(0,0,0,0.12)',
                textAlign: 'center'
              }}
            >
              <div style={{ fontWeight: 700, fontSize: 20, color: '#2563eb' }}>{item.value}</div>
              <div style={{ marginTop: 6, fontSize: 14, color: '#555' }}>{item.label}</div>
            </li>
          ))}
        </ul>
      </section>

      {/* 7일 신고현황 + 주요 지표 */}
      <section style={bigPanelStyle}>
        <h2 style={{ margin: 0, fontSize: 22, fontWeight: 700, color: '#2977ef' }}>
          📊 최근 7일 신고 현황
        </h2>
        <div
          style={{
            display: 'flex',
            gap: 32,
            alignItems: 'flex-end',
            marginTop: 22,
            marginBottom: 8
          }}
        >
          <div style={{ textAlign: 'right' }}>
            <div style={{ fontSize: 15, color: '#777' }}>오늘</div>
            <div style={{ fontWeight: 700, fontSize: 22, color: '#337aff' }}>{todayCount}건</div>
          </div>
          <div style={{ textAlign: 'right' }}>
            <div style={{ fontSize: 15, color: '#777' }}>7일 최고</div>
            <div style={{ fontWeight: 700, fontSize: 22, color: '#ef4444' }}>{maxCount}건</div>
          </div>
          <div style={{ textAlign: 'right' }}>
            <div style={{ fontSize: 15, color: '#777' }}>7일 평균</div>
            <div style={{ fontWeight: 700, fontSize: 22, color: '#333' }}>{avgCount}건</div>
          </div>
        </div>
        <div style={{ width: '99%', maxWidth: 700, height: 'calc(100% - 130px)', marginTop: 12 }}>
          <Bar
            data={{
              labels: weekLabels,
              datasets: [
                {
                  label: '일별 신고',
                  data: dailyCounts,
                  backgroundColor: weekLabels.map((_, i) =>
                    i === weekLabels.length - 1 ? '#2977ef' : 'rgba(51,122,255,0.23)'
                  )
                }
              ]
            }}
            options={{
              plugins: { legend: { display: false } },
              scales: {
                x: { type: 'category' },
                y: {
                  beginAtZero: true,
                  stepSize: 1,
                  max: maxCount + 1
                }
              },
              responsive: true,
              maintainAspectRatio: false
            }}
            height={300}
          />
        </div>
      </section>

      {/* 시간대별 신고 현황 (라인 차트) */}
      <section style={subPanelStyle}>
        <div style={{ fontSize: 19, fontWeight: 700, marginBottom: 0, color: '#2d3c50' }}>
          ⏰ 시간대별 신고
        </div>
        <div style={{ width: '100%' }}>
          <Line
            data={{
              labels: timeRanges.map(r => r.label),
              datasets: [
                {
                  label: '시간대별',
                  data: timeRangeCounts,
                  borderColor: '#17b8fc',
                  backgroundColor: 'rgba(41,119,239,0.13)',
                  tension: 0.4,
                  fill: true,
                  pointRadius: 5
                }
              ]
            }}
            options={{
              maintainAspectRatio: false,
              plugins: { legend: { display: false } },
              scales: { y: { beginAtZero: true } },
              responsive: true
            }}
          />
        </div>
      </section>
      <section style={{ gridRow: '4', padding: 10 }}></section>
    </div>
  )
}

export default InfoPanel