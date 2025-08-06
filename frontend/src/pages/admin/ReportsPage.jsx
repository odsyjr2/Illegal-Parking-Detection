import React, { useEffect, useState, useMemo } from 'react'
import { Bar, Pie, Line } from 'react-chartjs-2'
import {
  Chart as ChartJS, CategoryScale, LinearScale, BarElement, Title, Tooltip, Legend, ArcElement, LineElement, PointElement
} from 'chart.js'

ChartJS.register(CategoryScale, LinearScale, BarElement, Title, Tooltip, Legend, ArcElement, LineElement, PointElement)

const korWeekDays = ['일', '월', '화', '수', '목', '금', '토']

function ReportsPage() {
  const [rawData, setRawData] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  // 최근 7일 날짜 생성
  const dates = useMemo(() => {
    const getDateNDaysAgo = (n) => {
      const d = new Date()
      d.setDate(d.getDate() - n)
      return d
    }
    const formatDate = (date) => date.toISOString().slice(0, 10)
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
        // 실제 호출로 교체하세요
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
    dates.forEach(date => (dailyMap[date] = 0))
    rawData.forEach(({ createdAt }) => {
      const date = createdAt.slice(0, 10)
      if (dailyMap[date] !== undefined) dailyMap[date]++
    })
    return dates.map(date => dailyMap[date])
  }, [rawData, dates])

  // 오늘
  const todayIndex = dates.length - 1
  const todayCount = dailyCounts[todayIndex]
  const maxCount = Math.max(...dailyCounts)
  const avgCount = (dailyCounts.reduce((a, b) => a + b, 0) / dailyCounts.length).toFixed(1)

  // 구역별 통계 (이번 주 데이터 기준)
  const regionCounts = useMemo(() => {
    if (!rawData) return {labels:[], data:[]}
    const regionMap = {}
    const validDates = new Set(dates)
    rawData.forEach(({ region, createdAt }) => {
      const date = createdAt.slice(0, 10)
      if (validDates.has(date)) {
        if (region) regionMap[region] = (regionMap[region] || 0) + 1
      }
    })
    return {
      labels: Object.keys(regionMap),
      data: Object.values(regionMap),
    }
  }, [rawData, dates])

  // 시간대별 (4구간)
  const timeRanges = [
    { label: '00~06시', start: 0, end: 6 },
    { label: '06~12시', start: 6, end: 12 },
    { label: '12~18시', start: 12, end: 18 },
    { label: '18~24시', start: 18, end: 24 },
  ]
  const timeRangeCounts = useMemo(() => {
    if (!rawData) return Array(4).fill(0)
    const validDates = new Set(dates)
    const counts = [0,0,0,0]
    rawData.forEach(({ createdAt }) => {
      const date = createdAt.slice(0, 10)
      if (!validDates.has(date)) return
      const hour = Number((createdAt.length > 10 ? createdAt.slice(11,13) : '00'))
      const idx = timeRanges.findIndex(r => hour >= r.start && hour < r.end)
      if (idx!==-1) counts[idx]++
    })
    return counts
  }, [rawData, dates])

  // 차트 라벨
  const weekLabels = dates.map(d => {
    const dt = new Date(d)
    return `${dt.getDate()}(${korWeekDays[dt.getDay()]})`
  })
  const chartColors = ['#1976d2','#ff9800','#43a047', '#ef5350','#6d4c41','#9c27b0','#0097a7']

  const gridStyle = {
    display: 'grid',
    gridTemplateColumns: '2.1fr 1.1fr',
    gridTemplateRows: '1.2fr 1.2fr',
    gap: 30,
    maxWidth: 1100,
    minHeight: 760,
    margin: '38px auto',
  }
  const bigPanelStyle = {
    gridColumn: '1', gridRow: '1 / span 2',
    background: 'linear-gradient(95deg, #eef5ff 0%, #e6effa 100%)',
    borderRadius: 18,
    padding: '32px 30px 24px 30px',
    boxShadow: '0 3px 14px #eaf2fe',
    minHeight: 540,
    display: 'flex', flexDirection: 'column', justifyContent:'flex-start'
  }
  const subPanelStyle = {
    background: '#fff',
    borderRadius: 14,
    padding: 20,
    boxShadow: '0 2px 7px #e8e8e8',
    minHeight: 245,
    minWidth: 0,
    display:'flex', flexDirection:'column', alignItems:'center', justifyContent:'flex-start'
  }

  if (loading) return <div>로딩 중...</div>
  if (error) return <div>{error}</div>

  return (
    <div style={gridStyle}>
      {/* 7일 신고현황 + 오늘/7일최고/7일평균 지표 */}
      <section style={bigPanelStyle}>
        <h2 style={{ margin: 0, fontSize: 22, fontWeight: 700, color:'#2977ef'}}>📊 최근 7일 신고 현황</h2>
        <div style={{ display: 'flex', gap: 32, alignItems: 'flex-end', marginTop: 22, marginBottom: 8 }}>
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
            <div style={{ fontWeight: 700, fontSize: 22, color: '#333' }}>
              {avgCount}건
            </div>
          </div>
        </div>
        <div style={{ width: '99%', maxWidth: 700, height: 'calc(100% - 130px)', marginTop: 22 }}>
          <Bar
            data={{
              labels: weekLabels,
              datasets: [
                {
                  label: '일별 신고',
                  data: dailyCounts,
                  backgroundColor: weekLabels.map((_,i)=>i===weekLabels.length-1 ? '#2977ef' : 'rgba(51,122,255,0.23)')
                }
              ]
            }}
            options={{
              plugins: {legend:{display:false}},
              scales: { y: {beginAtZero:true}},
              responsive: true,
              maintainAspectRatio: false,
            }}
            height={320}
          />
        </div>
      </section>
      {/* 구역별 신고 통계 */}
      <section style={{...subPanelStyle, gridColumn:'2', gridRow:'1', marginBottom: 18}}>
        <div style={{fontSize:19, fontWeight:700, marginBottom:12, color:'#2d3c50'}}>📍 구역별 신고 통계</div>
        <Pie
          data={{
            labels: regionCounts.labels,
            datasets: [
              {
                label: "구역별 신고",
                data: regionCounts.data,
                backgroundColor: chartColors,
              }
            ]
          }}
          options={{
            plugins:{legend:{position:'bottom', labels:{font:{size:15}}}},
            responsive:true,
          }}
          height={130}
        />
      </section>
      {/* 시간대별 신고 (4구간/라인그래프) */}
      <section style={{...subPanelStyle, gridColumn:'2', gridRow:'2', marginBottom: 18}}>
        <div style={{fontSize:19, fontWeight:700, marginBottom:12, color:'#2d3c50'}}>⏰ 시간대별 신고</div>
        <Line
          data={{
            labels: timeRanges.map(r=>r.label),
            datasets: [
              {
                label:'시간대별',
                data: timeRangeCounts,
                borderColor:'#17b8fc',
                backgroundColor:'rgba(41,119,239,0.13)',
                tension:0.4,
                fill:true,
                pointRadius:5,
              }
            ]
          }}
          options={{
            plugins: {legend:{display:false}},
            scales: { y: {beginAtZero:true}},
            responsive: true,
          }}
          height={110}
        />
      </section>
    </div>
  )
}

export default ReportsPage