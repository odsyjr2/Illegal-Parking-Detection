import React from 'react'
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

// 차트 요소 등록
ChartJS.register(CategoryScale, LinearScale, BarElement, Title, Tooltip, Legend)

function ReportsPage() {
  // 데이터 샘플 (월~일: 1=월, 2=화 ...)
  const dataList = [12, 19, 7, 14, 18, 9, 15]
  const labels = ['1', '2', '3', '4', '5', '6', '7']
  const korDays = ['월', '화', '수', '목', '금', '토', '일']

  // 오늘이 무슨 요일?
  const now = new Date()
  // getDay(): 일요일=0, 월=1 ... 토=6 → 월=0 ~ 일=6 맞추기
  const dayIdx = ((now.getDay() + 6) % 7)
  const todayCount = dataList[dayIdx]
  const monthMax = Math.max(...dataList)
  const monthAvg = (dataList.reduce((a, b) => a + b, 0) * 4) / (7 * 4)

  const chartData = {
    labels: labels.map((num, i) =>
      (i === dayIdx ? `${num} (오늘)` : num)
    ),
    datasets: [
      {
        label: '신고 건수',
        data: dataList,
        backgroundColor: labels.map((_, i) =>
          i === dayIdx ? '#2977ef' : 'rgba(51, 122, 255, 0.5)'
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
          callback: function(val, idx) {
            return `${labels[idx]} (${korDays[idx]})`
          }
        },
        grid: { display: false }
      }
    },
    layout: { autoPadding: true },
  }

  return (
    <div style={{ background: '#fff', padding: 28, borderRadius: 12, minWidth: 400 }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 20 }}>
        <h2 style={{ margin: 0, fontSize: 22, fontWeight: 700 }}>📊 오늘의 신고 현황</h2>
        <div style={{
          display: 'flex',
          gap: 28,
          alignItems: 'flex-start'
        }}>
          <div style={{ textAlign: 'right' }}>
            <div style={{ fontSize: 15, color: '#777' }}>오늘</div>
            <div style={{ fontWeight: 700, fontSize: 19, color: '#337aff' }}>{todayCount}건</div>
          </div>
          <div style={{ textAlign: 'right' }}>
            <div style={{ fontSize: 15, color: '#777' }}>한달 최다</div>
            <div style={{ fontWeight: 700, fontSize: 19, color: '#ef4444' }}>{monthMax}건</div>
          </div>
          <div style={{ textAlign: 'right' }}>
            <div style={{ fontSize: 15, color: '#777' }}>월평균</div>
            <div style={{ fontWeight: 700, fontSize: 19, color: '#333' }}>{monthAvg.toFixed(1)}건</div>
          </div>
        </div>
      </div>
      <div style={{
        height: 340, maxWidth: 830,
        margin: '0 auto',
        padding: '0 12px 12px 0',
      }}>
        <Bar data={chartData} options={options} />
      </div>
    </div>
  )
}

export default ReportsPage
