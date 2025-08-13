// MainPage.jsx
import { useState, useEffect } from 'react';
import axios from 'axios'; // ✅ axios 반드시 import
import MapPage from './MapPage';
import InfoPanel from './InfoPanel';
import RoutePage from './RoutePage';
import './MainPage.css';

// =======================
// 알림 박스 컴포넌트
// =======================
  function AlertBox({ alerts, onDismiss }) {
    return (
      <div className="alert-box">
        {alerts.map(alert => (
          <div
            key={alert.id}
            className="alert-item"
            onClick={() => onDismiss(alert.id)}
          >
            {alert.message}
          </div>
        ))}
      </div>
    );
  }


// =======================
// 단속경로 패널
// =======================
function RoutePanel() {
  return (
    <div className="route-panel" style={{ textAlign: 'center' }}>
      <RoutePage />
    </div>
  );
}

// =======================
// 지도 + 위치 선택 UI
// =======================
function MapWithLocationSelector({ selectedLocation, onLocationChange, locations }) {
  return (
    <div style={{ position: 'relative', height: '100%' }}>
      {/* 왼쪽 위 위치 선택 UI */}
      <div
        style={{
          position: 'absolute',
          top: 10,
          left: 10,
          zIndex: 1000,
          backgroundColor: 'white',
          borderRadius: 10,
          boxShadow: '0 2px 12px rgba(0,0,0,0.15)',
          padding: 12,
          width: 240,
          display: 'flex',
          flexDirection: 'column',
          gap: 10,
          userSelect: 'none',
        }}
      >
        <select
          value={selectedLocation?.label || ''}
          onChange={e => {
            const loc = locations.find(l => l.label === e.target.value);
            if (loc) onLocationChange(loc);
          }}
          style={{
            width: '100%',
            padding: 8,
            borderRadius: 6,
            border: '1px solid #ccc',
            cursor: 'pointer',
            fontSize: 14,
            outline: 'none',
          }}
        >
          <option value="">--- 감시 위치 선택 ---</option>
          {locations.map(loc => (
            <option key={loc.label} value={loc.label}>
              {loc.label}
            </option>
          ))}
        </select>

        <div
          style={{
            background: '#e0e0e0',
            height: 160,
            borderRadius: 8,
            display: 'flex',
            justifyContent: 'center',
            alignItems: 'center',
            fontWeight: '600',
            color: '#555',
          }}
        >
          <span>{selectedLocation?.label || '위치 미선택'}</span>
        </div>
      </div>

      {/* 실제 지도 */}
      <MapPage selectedLocation={selectedLocation} onLocationChange={onLocationChange} />
    </div>
  );
}

// =======================
// 메인 페이지
// =======================
function MainPage() {
  const [selectedLocation, setSelectedLocation] = useState(null);
  const [tab, setTab] = useState('map');

  // 알림 상태 관리
  const [alerts, setAlerts] = useState([]);

  // 감시 위치 목록
  const locations = [
    { label: '강남구', lat: 37.5172, lng: 127.0473 },
    { label: '관악구', lat: 37.4784, lng: 126.9516 },
    { label: '송파구', lat: 37.5145, lng: 127.1056 },
  ];

  // 🚨 주기적으로 신고 목록 조회 (isRead = false → 알림)
  useEffect(() => {
    let timer;

    const fetchReports = async () => {
      try {
        const res = await axios.get('http://localhost:8080/api/human-reports');
        console.log('[신고 목록]', res.data);

        const data = Array.isArray(res.data) ? res.data : [];

        // read = false 또는 'false' → 미읽음 처리
        const unread = data.filter(
          item =>
            item.read === false ||
            item.read === 'false' ||
            String(item.read).toLowerCase() === 'false'
        );

        if (unread.length > 0) {
          setAlerts(prev => {
            // 첫 번째 미읽음만 사용
            const latest = unread[0];
            return [{
              id: latest.id,
              message: `${latest.title || '신고'}가 접수되었습니다.`,
            }];
            // 여러개인경우
            // const existingIds = new Set(prev.map(a => String(a.id)));
            // const newAlerts = unread
            //   .filter(item => !existingIds.has(String(item.id)))
            //   .map(item => ({
            //     id: item.id,
            //     message: `${item.title || '신고'}가 접수되었습니다.`,
            //   }));
            // return [...prev, ...newAlerts];
          });
        }
      } catch (error) {
        console.error('신고 조회 실패:', error);
      }
    };

    fetchReports();
    timer = setInterval(fetchReports, 10000); // 10초마다 갱신

    return () => clearInterval(timer);
  }, []);

  // 🚨 알림 클릭 시 읽음 처리 API 호출
  const dismissAlert = async (id) => {
    try {
      await axios.patch(`http://localhost:8080/api/human-reports/${id}/read`, {});
    } catch (error) {
      console.error('읽음 처리 실패:', error);
    } finally {
      setAlerts(prev => prev.filter(a => a.id !== id)); // UI 반영
    }
  };

  return (
    <div
      style={{
        padding: '40px',
        background: '#f0f2f6',
        height: '100vh',
        boxSizing: 'border-box',
      }}
    >
      {/* 알림 박스 */}
      <AlertBox alerts={alerts} onDismiss={dismissAlert} />

      {/* 탭 버튼 */}
      <div className="main-tabs">
        <button
          className={tab === 'map' ? 'active' : ''}
          onClick={() => setTab('map')}
        >
          지도현황
        </button>
        <button
          className={tab === 'route' ? 'active' : ''}
          onClick={() => setTab('route')}
        >
          단속경로
        </button>
      </div>

      {/* 메인 레이아웃 */}
      <div
        className="main-layout"
        style={{
          height: 'calc(100% - 60px)',
          display: 'flex',
        }}
      >
        {/* 왼쪽 영역 */}
        <div style={{ flex: tab === 'map' ? '1 1 70%' : '1 1 100%', position: 'relative' }}>
          {tab === 'map' ? (
            <MapWithLocationSelector
              selectedLocation={selectedLocation}
              onLocationChange={setSelectedLocation}
              locations={locations}
            />
          ) : (
            <RoutePanel />
          )}
        </div>

        {/* 오른쪽 InfoPanel - 지도 탭일 때만 표시 */}
        {tab === 'map' && (
          <div
            className="side-panel"
            style={{ flex: '0 0 30%', overflowY: 'auto' }}
          >
            <InfoPanel
              selectedLocation={selectedLocation}
              onLocationChange={setSelectedLocation}
            />
          </div>
        )}
      </div>
    </div>
  );
}

export default MainPage;