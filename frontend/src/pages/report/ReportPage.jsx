import React, { useState, useEffect } from 'react';
import axios from 'axios';

// 상태별 컬러 매핑
const statusColorMap = {
  접수: '#f59e0b',
  진행중: '#3b82f6',
  완료: '#10b981'
};

function ReportPage() {
  const [reports, setReports] = useState([]);

  const fetchReports = async () => {
    try {
      const res = await axios.get('http://localhost:8080/api/human-reports');
      setReports(res.data);
    } catch (err) {
      console.error('신고 목록 불러오기 실패:', err);
    }
  };

  useEffect(() => {
    fetchReports();
  }, []);

  // 지역 추출
  const extractRegionFromAddress = (address) => {
    if (!address) return '기타';
    if (address.includes('강남구')) return '강남';
    if (address.includes('관악구')) return '관악';
    if (address.includes('송파구')) return '송파';
    if (address.includes('동대문구')) return '동대문';
    return '기타';
  };

  const [suggestions, setSuggestions] = useState([]);
  const [addressInput, setAddressInput] = useState('');
  const [latitude, setLatitude] = useState('');
  const [longitude, setLongitude] = useState('');
  const [region, setRegion] = useState(''); 
  const [roadAddress, setRoadAddress] = useState('');
  const [error, setError] = useState('');
  const [photo, setPhoto] = useState(null);
  const [reason, setReason] = useState('');

  // 📌 사진 변경 핸들러
  const handlePhotoChange = e => setPhoto(e.target.files[0]);

  // 📌 신고 제출
  const handleSubmit = async (e) => {
    e.preventDefault();

    const storedUser = JSON.parse(localStorage.getItem('user'));
    if (!storedUser?.id) {
      alert('사용자 정보가 없습니다. 다시 로그인해주세요.');
      return;
    }

    const formData = new FormData();
    formData.append('file', photo); // 📷 사진
    formData.append('userID', storedUser.email); // 사용자 ID는 추후 로그인 시스템 연동 시 대체
    formData.append('title', '사용자신고');
    formData.append('reason', reason);
    formData.append('latitude', latitude);
    formData.append('longitude', longitude);
    formData.append('location', roadAddress);
    formData.append('region', extractRegionFromAddress(roadAddress));
    formData.append('status', '진행중');

    try {
      await axios.post('http://localhost:8080/api/human-reports', formData, {
        headers: { 'Content-Type': 'multipart/form-data' }
      });
      alert('신고가 등록되었습니다.');
      await fetchReports();
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

  // ✅ 공통 상태 변경 함수 (ADMIN 전용 버튼에서 사용)
  const handleSetStatus = async (id, status) => {
    try {
      await axios.patch(`http://localhost:8080/api/human-reports/${id}/status`, { status });
      await fetchReports();
    } catch (err) {
      console.error('상태 변경 실패:', err);
      alert('상태 변경에 실패했습니다.');
    }
  };

  // 📌 단속완료 처리 (기존 유지, 내부적으로 공통 함수 사용)
  const handleComplete = async id => handleSetStatus(id, '완료');

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

  const handleDaumPostcode = () => {
    new window.daum.Postcode({
      oncomplete: async function (data) {
        const fullAddress = data.roadAddress || data.jibunAddress || '';
        setRoadAddress(fullAddress);
        setRegion(extractRegionFromAddress(fullAddress));

        try {
          const res = await axios.get('https://dapi.kakao.com/v2/local/search/address.json', {
            params: { query: fullAddress },
            headers: {
              Authorization: `KakaoAK 31190e0b91ccecdd1178d3525ef71da3`
            }
          });
          const result = res.data.documents[0];
          setLatitude(result?.y || '');
          setLongitude(result?.x || '');
        } catch (err) {
          console.error('좌표 변환 실패:', err);
        }
      }
    }).open();
  };

  const storedUser = JSON.parse(localStorage.getItem('user'));
  const currentUserID = storedUser?.email;
  const currentRole = storedUser?.role;

  // ✅ 조건에 따라 보여줄 신고 내역 선택
  const filteredReports = currentRole === 'ADMIN'
    ? reports
    : reports.filter(report => report.userID === currentUserID);

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
            onClick={handleDaumPostcode}  // ✅ 클릭 시 주소 검색 UI 호출
            placeholder="도로명 주소 입력"
            style={{
              width: '100%',
              padding: '10px 48px 10px 12px',  // 오른쪽 여백 확보!
              borderRadius: 8,
              fontSize: 14,
              boxSizing: 'border-box'
            }}
          />
          <button
            type="button"
            onClick={handleGetLocation}
            title="내 위치"
            style={{
              position: 'absolute',
              top: '50%',
              right: 12,
              transform: 'translateY(-50%)',
              background: '#eef2ff',
              border: 'none',
              borderRadius: '50%',
              width: 28,
              height: 28,
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center'
            }}
          >
            📍
          </button>
        </div>
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
    {filteredReports.length === 0 ? (
      <p style={{ textAlign: 'center', color: '#888' }}>신고 내역이 없습니다.</p>
    ) : (
      <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
        {filteredReports.map(report => (
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
              위치: {report.location} ({report.latitude}, {report.longitude})
            </div>
            {report.imageURL && (
              <img
                src={`http://localhost:8080${report.imageURL}`}
                alt="첨부사진"
                style={{ width: 160, borderRadius: 8 }}
              />
            )}
            <div style={{ fontSize: 15, color: '#444' }}>{report.reason}</div>
            <div style={{ fontSize: 13, color: '#999', display: 'flex', gap: 12, alignItems: 'center', justifyContent: 'space-between' }}>
              <div style={{ display: 'flex', gap: 12 }}>
                <span> 지역: {report.region}</span>
                <span> 등록일: {report.createdAt?.slice(0, 10)}</span>
              </div>

              {/* ✅ ADMIN 전용 상태 변경 버튼 */}
              {currentRole === 'ADMIN' && (
                  <div style={{ display: 'flex', gap: 8 }}>
                    <button
                      type="button"
                      onClick={() => handleSetStatus(report.id, '진행중')}
                      disabled={report.status === '진행중'}
                      style={{
                        padding: '8px 16px',
                        borderRadius: 8,
                        border: '1px solid #c7d2fe',
                        background: report.status === '진행중' ? '#e0e7ff' : '#fff',
                        cursor: report.status === '진행중' ? 'not-allowed' : 'pointer',
                        minWidth: 80
                      }}
                    >
                      진행중
                    </button>
                    <button
                      type="button"
                      onClick={() => handleSetStatus(report.id, '완료')}
                      disabled={report.status === '완료'}
                      style={{
                        padding: '8px 16px',
                        borderRadius: 8,
                        border: '1px solid #2563eb',
                        background: report.status === '완료' ? '#2563eb' : '#3b82f6',
                        color: '#fff',
                        cursor: report.status === '완료' ? 'not-allowed' : 'pointer',
                        minWidth: 80
                      }}
                    >
                      완료
                    </button>
                  </div>
                )}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

export default ReportPage;
