function MapPage({ selectedLocation, onLocationChange }) {
  return (
    <div
      onClick={() => {
        // 테스트용 위치 클릭시 임의 마커 선택
        onLocationChange({
          lat: 33.450701,
          lng: 126.570667,
          label: '제주도중앙',
        })
      }}
      style={{
        width: '100%',
        height: '100%',
        backgroundColor: '#cce6ff',
        display: 'flex',
        justifyContent: 'center',
        alignItems: 'center',
        cursor: 'pointer'
      }}
    >
      <div>
        <h2>지도 영역 📍</h2>
        {selectedLocation && (
          <p style={{ marginTop: '1rem' }}>
            현재 선택 위치: {selectedLocation.label}
          </p>
        )}
      </div>
    </div>
  )
}

export default MapPage
