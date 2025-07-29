import React, { useState, useEffect } from 'react';
import axios from 'axios';

// 상태별 컬러 매핑
const statusColorMap = {
  진행중: '#3b82f6',
  완료: '#10b981'
};

function ReportPage() {
  // 📌 localStorage에서 초기화 + mock 데이터 없을 경우 자동 세팅
  const [reports, setReports] = useState(() => {
    const saved = localStorage.getItem('humanReports');
    if (saved) return JSON.parse(saved);

    const mock = [
      {
        id: 1,
        title: '불법 주차',
        reason: '버스 정류장 앞에 불법 주차된 차량',
        status: '진행중',
        photoUrl: '',
        latitude: 37.514575,
        longitude: 127.105399,
        roadAddress: '서울특별시 송파구 올림픽로 300',
        region: '송파',
        date: '2025-07-28'
      },
      {
        id: 2,
        title: '쓰레기 무단투기',
        reason: '상가 골목에 쓰레기 더미',
        status: '완료',
        photoUrl: '',
        latitude: 37.497942,
        longitude: 127.027621,
        roadAddress: '서울특별시 강남구 테헤란로 152',
        region: '강남',
        date: '2025-07-25'
      }
    ];
    localStorage.setItem('humanReports', JSON.stringify(mock));
    return mock;
  });

  // 지역 추출
  const extractRegionFromAddress = (address) => {
    if (!address) return '기타';
    if (address.includes('강남구')) return '강남';
    if (address.includes('관악구')) return '관악';
    if (address.includes('송파구')) return '송파';
    return '기타';
  };

  const [suggestions, setSuggestions] = useState([]);
  const [addressInput, setAddressInput] = useState('');
  const [latitude, setLatitude] = useState('');
  const [longitude, setLongitude] = useState('');
  const [roadAddress, setRoadAddress] = useState('');
  const [error, setError] = useState('');
  const [photo, setPhoto] = useState(null);
  const [reason, setReason] = useState('');

  // 📌 사진 변경 핸들러
  const handlePhotoChange = e => setPhoto(e.target.files[0]);

  // 📌 신고 제출
  const handleSubmit = async (e) => {
    e.preventDefault();

    const formData = new FormData();
    formData.append('file', photo); // 📷 사진
    formData.append('userID', 'user123'); // 사용자 ID는 추후 로그인 시스템 연동 시 대체
    formData.append('title', '사용자신고');
    formData.append('reason', reason);
    formData.append('latitude', latitude);
    formData.append('longitude', longitude);
    formData.append('location', roadAddress);
    formData.append('region', extractRegionFromAddress(roadAddress));
    formData.append('status', '접수');

    try {
      const res = await axios.post('/api/human-reports', formData, {
        headers: { 'Content-Type': 'multipart/form-data' }
      });
      alert('신고가 등록되었습니다.');
      setPhoto(null);
      setReason('');
      setAddressInput('');
      setLatitude('');
      setLongitude('');
      setRoadAddress('');
    } catch (err) {
      console.error(err);
      alert('신고 등록 실패');
    }
  };

  // 📌 단속완료 처리
  const handleComplete = id => {
    const updated = reports.map(r =>
      r.id === id ? { ...r, status: '완료' } : r
    );
    setReports(updated);
    localStorage.setItem('humanReports', JSON.stringify(updated));
  };

  // 📌 경로보기
  const handlePath = id => {
    alert('경로 보기 기능은 추후 구현됩니다.');
  };

  // 📌 GPS로 현재 위치 가져오기
  const handleGetLocation = () => {
    if (!navigator.geolocation) {
      setError('위치 정보를 지원하지 않는 브라우저입니다.');
      return;
    }

    navigator.geolocation.getCurrentPosition(
      async (position) => {
        const lat = position.coords.latitude;
        const lng = position.coords.longitude;
        setLatitude(lat);
        setLongitude(lng);

        try {
          const response = await axios.get('https://dapi.kakao.com/v2/local/geo/coord2address.json', {
            params: { x: lng, y: lat },
            headers: {
              Authorization: `KakaoAK 31190e0b91ccecdd1178d3525ef71da3`
            }
          });
          const address = response.data.documents[0]?.road_address?.address_name || '주소 없음';
          setRoadAddress(address);
          setError('');
        } catch (err) {
          console.error(err);
          setRoadAddress('주소 조회 실패');
        }
      },
      err => {
        console.error(err);
        setError('위치 접근 실패: 권한을 허용했는지 확인하세요.');
      }
    );
  };

  // 📌 주소로 좌표 검색
  const handleAddressSearch = async () => {
    try {
      const response = await axios.get('https://dapi.kakao.com/v2/local/search/address.json', {
        params: { query: addressInput },
        headers: {
          Authorization: `KakaoAK 31190e0b91ccecdd1178d3525ef71da3
`
        }
      });
      const result = response.data.documents[0];
      if (result) {
        setLatitude(result.y);
        setLongitude(result.x);
        setRoadAddress(result.address.address_name);
        setError('');
      } else {
        setError('해당 주소를 찾을 수 없습니다.');
      }
    } catch (err) {
      console.error(err);
      setError('주소 검색 중 오류가 발생했습니다.');
    }
  };

  // 📌 자동완성
  useEffect(() => {
    const timer = setTimeout(async () => {
      if (!addressInput.trim()) {
        setSuggestions([]);
        return;
      }

      try {
        const response = await axios.get('https://dapi.kakao.com/v2/local/search/address.json', {
          params: { query: addressInput },
          headers: {
            Authorization: `KakaoAK 31190e0b91ccecdd1178d3525ef71da3`
          }
        });
        setSuggestions(response.data.documents);
      } catch (err) {
        console.error('자동완성 실패:', err);
      }
    }, 300);

    return () => clearTimeout(timer);
  }, [addressInput]);

  return (
    <div style={{ maxWidth: 1000, margin: '40px auto', padding: 20, borderRadius: 10, background: '#f9fafe', minHeight: '100vh' }}>
      <h1 style={{ marginBottom: 28, fontSize: 25, color: '#000' }}>신고 접수</h1>

      {/* 📍 주소 입력 & 위치 버튼 */}
      <div style={{ display: 'flex', alignItems: 'center', marginBottom: 16 }}>
        <div style={{ position: 'relative', flex: 1 }}>
          <input
            type="text"
            value={addressInput}
            onChange={e => setAddressInput(e.target.value)}
            placeholder="도로명 주소 입력"
            style={{ width: '100%', padding: '10px 38px 10px 12px', borderRadius: 8, fontSize: 14 }}
          />
          <button
            type="button"
            onClick={handleGetLocation}
            title="내 위치"
            style={{
              position: 'absolute',
              top: '50%',
              right: 8,
              transform: 'translateY(-50%)',
              background: '#eef2ff',
              border: 'none',
              borderRadius: '50%',
              width: 24,
              height: 24,
              cursor: 'pointer'
            }}
          >📍</button>

          {/* 자동완성 목록 */}
          {suggestions.length > 0 && (
            <ul style={{
              position: 'absolute',
              top: '100%',
              left: 0,
              right: 0,
              background: '#fff',
              border: '1px solid #ccc',
              zIndex: 100,
              maxHeight: 200,
              overflowY: 'auto',
              listStyle: 'none',
              margin: 0,
              padding: 0
            }}>
              {suggestions.map((item, idx) => (
                <li
                  key={idx}
                  onClick={() => {
                    setAddressInput(item.address.address_name);
                    setLatitude(item.y);
                    setLongitude(item.x);
                    setRoadAddress(item.address.address_name);
                    setSuggestions([]);
                  }}
                  style={{ padding: '10px 12px', cursor: 'pointer' }}
                >
                  {item.address.address_name}
                </li>
              ))}
            </ul>
          )}
        </div>

        <button
          type="button"
          onClick={handleAddressSearch}
          style={{
            marginLeft: 10,
            background: '#337aff',
            color: '#fff',
            padding: '10px 16px',
            border: 'none',
            borderRadius: 8
          }}
        >
          주소 검색
        </button>
      </div>

      {roadAddress && (
        <div style={{ marginBottom: 16, padding: '10px 12px', background: '#f2f4f7', borderRadius: 6, fontSize: 14 }}>
          📍 <strong>{roadAddress}</strong> ({latitude}, {longitude})
        </div>
      )}

      {error && <div style={{ color: 'red', marginBottom: 10 }}>{error}</div>}

      {/* 신고 폼 */}
      <form onSubmit={handleSubmit} style={{ background: '#fff', padding: 24, borderRadius: 12, marginBottom: 40 }}>
        <div style={{ marginBottom: 16 }}>
          <label><strong>사진 첨부:</strong>
            <input type="file" accept="image/*" onChange={handlePhotoChange} style={{ marginLeft: 10 }} />
          </label>
        </div>
        {photo && <img src={URL.createObjectURL(photo)} alt="미리보기" style={{ width: 180, borderRadius: 8, marginBottom: 16 }} />}
        <textarea
          placeholder="신고 사유를 입력하세요"
          value={reason}
          onChange={e => setReason(e.target.value)}
          rows={4}
          required
          style={{ width: '100%', padding: 12, fontSize: 16, borderRadius: 8, border: '1px solid #ccc' }}
        />
        <button type="submit" style={{
          background: '#337aff',
          color: '#fff',
          padding: '10px 20px',
          border: 'none',
          borderRadius: 8,
          marginTop: 16,
          cursor: 'pointer'
        }}>
          제출
        </button>
      </form>

      {/* 신고 내역 */}
      <h2 style={{ fontWeight: 700, fontSize: 20, marginBottom: 22 }}>신고 내역</h2>
      {reports.length === 0 ? (
        <p style={{ textAlign: 'center', color: '#888' }}>신고 내역이 없습니다.</p>
      ) : (
        reports.map(report => (
          <div
            key={report.id}
            style={{
              background: '#fff',
              borderRadius: 10,
              boxShadow: '0 2px 9px rgba(0,0,0,0.06)',
              padding: 16,
              marginBottom: 16
            }}
          >
            <div style={{ display: 'flex', alignItems: 'center', flexWrap: 'wrap', gap: 8 }}>
              <strong>{report.title}</strong>
              <span style={{
                padding: '2px 10px',
                background: '#eef6ff',
                borderRadius: 12,
                fontSize: 13,
                color: statusColorMap[report.status]
              }}>{report.status}</span>
              {report.roadAddress && (
                <span style={{ fontSize: 12, color: '#666' }}>
                  📍 {report.roadAddress} ({report.latitude}, {report.longitude})
                </span>
              )}
            </div>
            {report.photoUrl && (
              <img src={report.photoUrl} alt="첨부사진" style={{ width: 120, marginTop: 8, borderRadius: 6 }} />
            )}
            <div style={{ fontSize: 15, color: '#444', marginTop: 8 }}>{report.reason}</div>
            {report.status === '진행중' && (
              <div style={{ marginTop: 10 }}>
                <button onClick={() => handlePath(report.id)} style={{
                  background: '#eee', color: '#2277e5', border: 'none',
                  padding: '6px 14px', borderRadius: 7, marginRight: 7
                }}>
                  경로 보기
                </button>
                <button onClick={() => handleComplete(report.id)} style={{
                  background: '#10b981', color: '#fff', border: 'none',
                  padding: '6px 14px', borderRadius: 7
                }}>
                  단속완료
                </button>
              </div>
            )}
          </div>
        ))
      )}
    </div>
  );
}

export default ReportPage;
