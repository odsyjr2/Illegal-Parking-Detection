import MapPage from './MapPage'
import InfoPanel from './InfoPanel'
import RoutePage from './RoutePage'
import './MainPage.css'
import { useState } from 'react'


// 임시로 단속경로 패널
function RoutePanel() {
  return (
    <div className="route-panel" style={{ textAlign: 'center' }}>
      <RoutePage/>
    </div>
  )
}

// 지도쪽에 위치 선택 UI와 지도를 함께 묶는 컴포넌트 (감시 위치 선택 UI 포함)
function MapWithLocationSelector({ selectedLocation, onLocationChange, locations }) {
  return (
    <div style={{ position: 'relative', height: '100%' }}>
      {/* 위치 선택 UI - 지도 위쪽 왼쪽에 고정 */}
      <div style={{
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
        marginRight: -40, // 좀 튀어나오는 룩 조절
      }}>
        <select
          value={selectedLocation?.label || ''}
          onChange={e => {
            const loc = locations.find(l => l.label === e.target.value)
            if (loc) onLocationChange(loc)
          }}
          style={{
            width: '100%',
            padding: 8,
            borderRadius: 6,
            border: '1px solid #ccc',
            cursor: 'pointer',
            fontSize: 14,
            outline: 'none'
          }}
        >
          <option value="">--- 감시 위치 선택 ---</option>
          {locations.map(loc => (
            <option key={loc.label} value={loc.label}>{loc.label}</option>
          ))}
        </select>

        <div style={{
          background: '#e0e0e0',
          height: 80,
          borderRadius: 8,
          display: 'flex',
          justifyContent: 'center',
          alignItems: 'center',
          fontWeight: '600',
          color: '#555',
          userSelect: 'none',
        }}>
          <span>{selectedLocation?.label || '위치 미선택'}</span>
        </div>
      </div>

      {/* 실제 지도 */}
      <MapPage selectedLocation={selectedLocation} onLocationChange={onLocationChange} />
    </div>
  )
}

function MainPage() {
  const [selectedLocation, setSelectedLocation] = useState(null)
  const [tab, setTab] = useState('map')

  // 감시 위치 목록 (InfoPanel과 동일하게 공유)
  const locations = [
    { label: '강남구', lat: 37.5172, lng: 127.0473 },
    { label: '관악구', lat: 37.4784, lng: 126.9516 },
    { label: '송파구', lat: 37.5145, lng: 127.1056 },
  ]

  return (
    <div style={{ padding: "40px", background: "#f0f2f6", height: '100vh', boxSizing: 'border-box' }}>
      {/* 탭 버튼 영역 */}
      <div className="main-tabs">
        <button
          className={tab === 'map' ? 'active' : ''}
          onClick={() => setTab('map')}
        >지도현황</button>
        <button
          className={tab === 'route' ? 'active' : ''}
          onClick={() => setTab('route')}
        >단속경로</button>
      </div>

      {/* 메인 레이아웃 */}
      <div className="main-layout" style={{ height: 'calc(100% - 60px)' }}>
        <div className="main-map" style={{ position: 'relative' }}>
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

        <div className="side-panel" style={{ overflowY: 'auto' }}>
          <InfoPanel
            selectedLocation={selectedLocation}
            onLocationChange={setSelectedLocation}
          />
        </div>
      </div>
    </div>
  )
}

export default MainPage