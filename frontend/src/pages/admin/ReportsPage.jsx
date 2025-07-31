import React, { useEffect, useState, useMemo } from 'react'
import { Bar } from 'react-chartjs-2'
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  BarElement,
  Title,
  Tooltip,
  Legend,
} from 'chart.js'

ChartJS.register(CategoryScale, LinearScale, BarElement, Title, Tooltip, Legend)

const korWeekDays = ['일', '월', '화', '수', '목', '금', '토']

function ReportsPage() {
  const [rawData, setRawData] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

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
        // TODO: 실제 API 호출로 교체
        // const res = await fetch(`/api/report?from=${dates[0]}&to=${dates[6]}`)
        // const data = await res.json()

        // 샘플 테스트 데이터 (일부 날짜 누락 가능)
        const data = [
          { date: dates[0], count: 10 },
          { date: dates[1], count: 14 },
          { date: dates[2], count: 7 },
          { date: dates[3], count: 21 },
          // dates[4] 누락
          { date: dates[5], count: 9 },
          { date: dates[6], count: 13 },
        ]

        setRawData(data)
      } catch (e) {
        setError('데이터를 불러오는 중 오류가 발생했습니다.')
      } finally {
        setLoading(false)
      }
    }
    fetchData()
  }, []) // 빈 배열! dates가 useMemo로 한 번 생성되어서 문제 없음

  const processedData = useMemo(() => {
    if (!rawData) return null
    const dataMap = {}
    rawData.forEach(({ date, count }) => {
      dataMap[date] = count
    })
    return dates.map(date => dataMap[date] || 0)
  }, [rawData, dates])

  const todayIndex = dates.length - 1

  const chartLabels = useMemo(() => {
    return dates.map(dateStr => {
      const d = new Date(dateStr)
      const day = d.getDate()
      const korDay = korWeekDays[d.getDay()]
      return `${day} (${korDay})`
    })
  }, [dates])

  if (loading) return <div>로딩 중...</div>
  if (error) return <div>{error}</div>

  const chartData = {
    labels: chartLabels.map((label, i) => (i === todayIndex ? `${label} (오늘)` : label)),
    datasets: [
      {
        label: '신고 건수',
        data: processedData,
        backgroundColor: chartLabels.map((_, i) =>
          i === todayIndex ? '#2977ef' : 'rgba(51, 122, 255, 0.5)'
        ),
        borderRadius: 5,
        barPercentage: 0.65,
      },
    ],
  }

  const options = {
    responsive: true,
    plugins: {
      legend: { display: false },
      title: { display: false },
      tooltip: { enabled: true },
    },
    scales: {
      y: {
        beginAtZero: true,
        ticks: { font: { size: 16 } },
        grid: { color: '#eee' },
      },
      x: {
        ticks: {
          font: { size: 16 },
          callback: function (val, idx) {
            return chartData.labels[idx]
          },
        },
        grid: { display: false },
      },
    },
    layout: { autoPadding: true },
  }

  return (
    <div style={{ background: '#fff', padding: 28, borderRadius: 12, minWidth: 400 }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 20 }}>
        <h2 style={{ margin: 0, fontSize: 22, fontWeight: 700 }}>📊 오늘의 신고 현황</h2>
        <div style={{ display: 'flex', gap: 28, alignItems: 'flex-start' }}>
          <div style={{ textAlign: 'right' }}>
            <div style={{ fontSize: 15, color: '#777' }}>오늘</div>
            <div style={{ fontWeight: 700, fontSize: 19, color: '#337aff' }}>{processedData[todayIndex]}건</div>
          </div>
          <div style={{ textAlign: 'right' }}>
            <div style={{ fontSize: 15, color: '#777' }}>한달 최다</div>
            <div style={{ fontWeight: 700, fontSize: 19, color: '#ef4444' }}>{Math.max(...processedData)}건</div>
          </div>
          <div style={{ textAlign: 'right' }}>
            <div style={{ fontSize: 15, color: '#777' }}>월평균</div>
            <div style={{ fontWeight: 700, fontSize: 19, color: '#333' }}>
              {(processedData.reduce((a, b) => a + b, 0) / processedData.length).toFixed(1)}건
            </div>
          </div>
        </div>
      </div>

      <div style={{ height: 340, maxWidth: 830, margin: '0 auto', padding: '0 12px 12px 0' }}>
        <Bar data={chartData} options={options} />
      </div>
    </div>
  )
}

export default ReportsPage