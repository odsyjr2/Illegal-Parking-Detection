import React, { useState } from 'react'

// 상태별 컬러 매핑
const statusColorMap = {
  진행중: '#3b82f6',
  완료: '#10b981'
}

function ReportPage() {
  // 🟡 초기 mock 데이터 (DB 연동 전 임시)
  const [reports, setReports] = useState([
    {
      id: 1,
      title: '불법 주차',
      reason: '횡단보도 인근에 주차된 차량',
      status: '진행중',
      photoUrl: ''
    },
    {
      id: 2,
      title: '쓰레기 무단투기',
      reason: '건물 입구에 많은 쓰레기',
      status: '완료',
      photoUrl: ''
    }
  ])

  // 폼 상태 관리
  const [photo, setPhoto] = useState(null)
  const [reason, setReason] = useState('')

  // 첨부파일 처리
  const handlePhotoChange = e => {
    const file = e.target.files[0]
    setPhoto(file)
  }

  // 신고 접수 처리
  const handleSubmit = e => {
    e.preventDefault()
    const url = photo ? URL.createObjectURL(photo) : ''
    setReports([
      ...reports,
      {
        id: reports.length + 1,
        title: '사용자신고',
        reason,
        status: '진행중',
        photoUrl: url
      }
    ])
    setReason('')
    setPhoto(null)
  }

  // 단속완료 버튼
  const handleComplete = (id) => {
    setReports(reports.map(r =>
      r.id === id ? { ...r, status: '완료' } : r
    ))
  }

  // 경로보기 버튼
  const handlePath = (id) => {
    alert('경로보기(예시): 해당 신고의 단속 경로/위치를 띄워줍니다.')
  }

  return (
    <div style={{
      maxWidth: 1000,
      margin: '40px auto',
      padding: 20,
      borderRadius: 10,
      background: '#f9fafe',
      minHeight: '100vh'
    }}>
      <h1 style={{ marginBottom: 28, fontSize: 25, color: '#000000ff' }}>신고 접수</h1>
      
      {/* 신고 폼 */}
      <form onSubmit={handleSubmit} style={{
        background: '#fff',
        padding: 24,
        borderRadius: 12,
        boxShadow: '0 2px 12px rgba(0,0,0,0.03)',
        marginBottom: 38
      }}>
        <div style={{ marginBottom: 16 }}>
          <label>
            <span style={{ fontWeight: 'bold' }}>사진 첨부: </span>
            <input type="file" accept="image/*" onChange={handlePhotoChange} style={{ marginLeft: 10 }} />
          </label>
        </div>
        {photo && (
          <div style={{ marginBottom: 16 }}>
            <img src={URL.createObjectURL(photo)} alt="미리보기" style={{ width: 180, borderRadius: 8 }} />
          </div>
        )}
        <div style={{ marginBottom: 16 }}>
          <textarea
            placeholder="신고 사유를 입력하세요"
            value={reason}
            onChange={e => setReason(e.target.value)}
            rows={4}
            style={{
              width: '100%',
              padding: 12,
              fontSize: 16,
              borderRadius: 7,
              border: '1px solid #d9e2ec',
              background: '#f8fafb'
            }}
            required
          />
        </div>
        <button
          type="submit"
          style={{
            background: '#337aff',
            color: '#fff',
            border: 'none',
            padding: '10px 26px',
            borderRadius: 8,
            cursor: 'pointer',
            fontWeight: 600
          }}
        >
          제출
        </button>
      </form>
      
      {/* 신고 내역 카드 리스트 */}
      <h2 style={{ fontWeight: 700, fontSize: 20, marginBottom: 22 }}>신고 내역</h2>
      <div>
        {reports.length === 0 ? (
          <p style={{ color: '#888', textAlign: 'center', marginTop: 36 }}>신고 내역이 없습니다.</p>
        ) : (
          reports.map(report => (
            <div
              key={report.id}
              style={{
                background: '#fff',
                borderRadius: 10,
                boxShadow: '0 2px 9px rgba(0,0,0,0.06)',
                padding: '18px 15px',
                marginBottom: 18,
                display: 'flex',
                flexDirection: 'column',
                gap: 9
              }}
            >
              <div>
                <strong>{report.title}</strong>
                <span style={{
                  marginLeft: 8,
                  padding: '2px 10px',
                  background: '#f0f7ff',
                  borderRadius: 12,
                  fontSize: 13,
                  color: statusColorMap[report.status] || '#999'
                }}>{report.status}</span>
              </div>
              {report.photoUrl && (
                <div>
                  <img src={report.photoUrl} alt="첨부사진" style={{ width: 120, borderRadius: 5 }} />
                </div>
              )}
              <div style={{ fontSize: 15, color: '#444' }}>
                {report.reason}
              </div>
              <div>
                {report.status === '진행중' && (
                  <>
                    <button
                      type="button"
                      onClick={() => handlePath(report.id)}
                      style={{
                        background: '#eee', color: '#2277e5', border: 'none',
                        padding: '6px 14px', borderRadius: 7, marginRight: 7, cursor: 'pointer'
                      }}
                    >
                      경로 보기
                    </button>
                    <button
                      type="button"
                      onClick={() => handleComplete(report.id)}
                      style={{
                        background: '#10b981', color: '#fff', border: 'none',
                        padding: '6px 14px', borderRadius: 7, cursor: 'pointer'
                      }}
                    >
                      단속완료
                    </button>
                  </>
                )}
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  )
}

export default ReportPage