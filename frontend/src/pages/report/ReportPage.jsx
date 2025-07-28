import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import exifr from 'exifr';

const statusColorMap = {
  진행중: '#3b82f6',
  완료: '#10b981',
  접수: '#f59e0b',
};
const REASON_OPTIONS = [
  '소화전 주변 5m 이내','횡단보도','교차로 모퉁이 5m 이내','버스 정류장','택시 승강장',
  '어린이 보호 구역','황색 실선/이중 실선 구역','노란색 점선 (정차만 가능)',
  '인도 또는 자전거 전용 도로 침범','도로 통행 방해','안전 표지판이 설치된 곳','주차 금지 구역','이중 주차'
];
const REGION_OPTIONS = ['강남', '관악', '송파', '서초', '기타'];

function ReportPage() {
  const [reports, setReports] = useState([]);
  const [title, setTitle] = useState('');
  const [reason, setReason] = useState(REASON_OPTIONS[0]);
  const [region, setRegion] = useState(REGION_OPTIONS[0]);
  const [location, setLocation] = useState('');
  const [memo, setMemo] = useState('');
  const [photo, setPhoto] = useState(null);
  const [photoURL, setPhotoURL] = useState(null);
  const [latitude, setLatitude] = useState('');
  const [longitude, setLongitude] = useState('');
  const [manualLocation, setManualLocation] = useState(false); // true: 지역/상세위치, false: 좌표자동
  const navigate = useNavigate();

  // 사진 및 위치 EXIF 추출
  const handlePhotoChange = async (e) => {
    const file = e.target.files[0];
    setPhoto(file);

    if (photoURL) URL.revokeObjectURL(photoURL);
    const url = URL.createObjectURL(file);
    setPhotoURL(url);

    try {
      const exif = await exifr.parse(file);
      if (exif?.latitude && exif?.longitude) {
        setLatitude(exif.latitude);
        setLongitude(exif.longitude);
        setManualLocation(false);
        setRegion(REGION_OPTIONS[0]);
        setLocation('');
      } else {
        setLatitude('');
        setLongitude('');
        setManualLocation(true);    // 수동 입력 UI 노출
      }
    } catch {
      setLatitude('');
      setLongitude('');
      setManualLocation(true);
    }
  };

  // 신고 내역 조회(GET)
  const fetchReports = async () => {
    try {
      const res = await fetch("http://localhost:8080/api/human-reports");
      const data = await res.json();
      setReports(data);
    } catch {
      setReports([]);
    }
  };

  useEffect(() => {
    fetchReports();
    return () => {
      if (photoURL) URL.revokeObjectURL(photoURL);
    };
    // eslint-disable-next-line
  }, []);

  // 신고 등록(POST)
  const handleSubmit = async (e) => {
    e.preventDefault();
    // 좌표 or 지역/상세위치 둘 중 하나만(필수)
    const payload = {
      title,
      reason,
      region: manualLocation ? region : null,
      location: manualLocation ? location : null,
      memo,
      imageURL: photoURL || '',
      latitude: manualLocation ? null : latitude,
      longitude: manualLocation ? null : longitude,
      // userID: 'testuser1', // 로그인 연동시 사용
    };

    try {
      const res = await fetch("http://localhost:8080/api/human-reports", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      if (!res.ok) throw new Error();
      setTitle('');
      setReason(REASON_OPTIONS[0]);
      setRegion(REGION_OPTIONS[0]);
      setLocation('');
      setMemo('');
      setPhoto(null);
      setLatitude('');
      setLongitude('');
      setManualLocation(false);
      if (photoURL) URL.revokeObjectURL(photoURL);
      setPhotoURL(null);
      await fetchReports();
    } catch {
      alert("등록 실패! (백엔드, 네트워크 등 확인)");
    }
  };

  const handleComplete = (id) => {
    setReports(reports.map(r => r.id === id ? { ...r, status: '완료' } : r));
  };
  const handlePath = (id) => {
    navigate(`/map/${id}`);
  };

  return (
    <div style={{ maxWidth: 1000, margin: '40px auto', padding: 20, borderRadius: 10, background: '#f9fafe', minHeight: '100vh' }}>
      <h1 style={{ marginBottom: 28, fontSize: 25 }}>신고 접수</h1>
      <form onSubmit={handleSubmit} style={{ background: '#fff', padding: 24, borderRadius: 12, boxShadow: '0 2px 12px rgba(0,0,0,0.03)', marginBottom: 38 }}>
        <div style={{ marginBottom: 16 }}>
          <span style={{ fontWeight: 'bold' }}>사진 첨부: </span>
          <input type="file" accept="image/*" onChange={handlePhotoChange} style={{ marginLeft: 10 }} required />
        </div>
        {photoURL && (
          <div style={{ marginBottom: 16 }}>
            <img src={photoURL} alt="미리보기" style={{ width: 180, borderRadius: 8 }} /><br/>
            {manualLocation ? (
              <div style={{ fontSize: 13, color: '#a22', marginTop: 5 }}>
                사진에 위치정보가 없습니다. 직접 지역/상세위치를 입력하세요.
              </div>
            ) : (
              (latitude && longitude) && (
                <div style={{ fontSize: 13, color: '#295', marginTop: 5 }}>
                  📍 위치정보: {latitude}, {longitude}
                </div>
              )
            )}
          </div>
        )}

        {manualLocation && (
          <>
            <div style={{ marginBottom: 16 }}>
              <label style={{ fontWeight: 'bold' }}>지역: </label>
              <select value={region} onChange={e => setRegion(e.target.value)} style={{ width: '100%', padding: 10 }}>
                {REGION_OPTIONS.map(opt => <option key={opt}>{opt}</option>)}
              </select>
            </div>
            <div style={{ marginBottom: 16 }}>
              <input
                placeholder="상세 위치 (도로명, 건물명 등)"
                value={location}
                onChange={e => setLocation(e.target.value)}
                style={{
                  width: '100%', padding: 12, borderRadius: 7,
                  border: '1px solid #d9e2ec', background: '#f8fafb'
                }}
                required
              />
            </div>
          </>
        )}

        <div style={{ marginBottom: 16 }}>
          <input
            placeholder="제목"
            type="text"
            value={title}
            onChange={e => setTitle(e.target.value)}
            style={{
              width: '100%', padding: 12, fontSize: 16,
              borderRadius: 7, border: '1px solid #d9e2ec', background: '#f8fafb', marginBottom: 10
            }}
            required
          />
        </div>
        <div style={{ marginBottom: 16 }}>
          <label style={{ fontWeight: 'bold' }}>신고 사유: </label>
          <select value={reason} onChange={e => setReason(e.target.value)} style={{ width: '100%', padding: 10 }}>
            {REASON_OPTIONS.map(opt => <option key={opt} value={opt}>{opt}</option>)}
          </select>
        </div>
        <div style={{ marginBottom: 16 }}>
          <textarea
            placeholder="추가 설명 (선택)"
            value={memo}
            onChange={e => setMemo(e.target.value)}
            rows={3}
            style={{
              width: '100%',
              padding: 12,
              fontSize: 15,
              borderRadius: 7,
              border: '1px solid #d9e2ec',
              background: '#f8fafb'
            }}
          />
        </div>
        <button type="submit" style={{ background: '#337aff', color: '#fff', border: 'none', padding: '10px 26px', borderRadius: 8, cursor: 'pointer', fontWeight: 600 }}>제출</button>
      </form>

      <h2 style={{ fontWeight: 700, fontSize: 20, marginBottom: 22 }}>신고 내역</h2>
      <div>
        {reports.length === 0 ? (
          <p style={{ color: '#888', textAlign: 'center', marginTop: 36 }}>신고 내역이 없습니다.</p>
        ) : (
          reports.map(report => (
            <div key={report.id} style={{ background: '#fff', borderRadius: 10, boxShadow: '0 2px 9px rgba(0,0,0,0.06)', padding: '18px 15px', marginBottom: 18, display: 'flex', flexDirection: 'column', gap: 9 }}>
              <div>
                <strong>{report.title}</strong>
                <span style={{
                  marginLeft: 8, padding: '2px 10px', background: '#f0f7ff', borderRadius: 12, fontSize: 13,
                  color: statusColorMap[report.status] || '#999'
                }}>{report.status || '접수'}</span>
              </div>
              {report.imageURL && (
                <div>
                  <img src={report.imageURL} alt="첨부사진" style={{ width: 120, borderRadius: 5 }} />
                </div>
              )}
              <div style={{ fontSize: 14, color: '#486', marginBottom: 3 }}>
                사유: {report.reason}
              </div>
              {/* 위치정보 표시방식: 좌표 있으면 그거, 없으면 지역+상세위치 */}
              {(report.latitude && report.longitude) ? (
                <div style={{ fontSize: 13, color: '#328', marginBottom: 3 }}>
                  위치(좌표): {report.latitude}, {report.longitude}
                </div>
              ) : (report.region || report.location) && (
                <div style={{ fontSize: 13, color: '#328', marginBottom: 3 }}>
                  위치: {report.region} {report.location}
                </div>
              )}
              <div style={{ fontSize: 13, color: '#555', marginBottom: 3 }}>
                📝 {report.memo}
              </div>
              {report.status === '진행중' && (
                <div style={{ marginTop: 8 }}>
                  <button
                    type="button"
                    onClick={() => handlePath(report.id)}
                    style={{
                      background: '#eee',
                      color: '#2277e5',
                      border: 'none',
                      padding: '6px 14px',
                      borderRadius: 7,
                      marginRight: 7,
                      cursor: 'pointer'
                    }}
                  >
                    경로 보기
                  </button>
                  <button
                    type="button"
                    onClick={() => handleComplete(report.id)}
                    style={{
                      background: '#10b981',
                      color: '#fff',
                      border: 'none',
                      padding: '6px 14px',
                      borderRadius: 7,
                      cursor: 'pointer'
                    }}
                  >
                    단속완료
                  </button>
                </div>
              )}
            </div>
          ))
        )}
      </div>
    </div>
  );
}

export default ReportPage;
