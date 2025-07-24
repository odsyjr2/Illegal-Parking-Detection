import { useEffect, useRef } from 'react'

// 🗺️ 지도에 표시할 위치 목록 예시
const locations = [
  { label: '강남구1', lat: 37.5172, lng: 127.0473 },
  { label: '강남구2', lat: 37.5171, lng: 127.0470 },
  { label: '관악구', lat: 37.4784, lng: 126.9516 },
  { label: '송파구', lat: 37.5145, lng: 127.1056 },
]

function MapPage({ selectedLocation, onLocationChange }) {
  const mapRef = useRef(null)
  const mapInstance = useRef(null)
  // 🚩 { [label]: Marker } 구조. label은 유니크해야 함
  const markerRefs = useRef({})

  const kakaoApiKey = '6586ab08c67a4dbc213f8a1e22f22adf'
  //const kakaoApiKey = import.meta.env.VITE_KAKAOMAP_KEY

  // ✅ 최초 1회: Kakao Map 객체만 생성
  useEffect(() => {
    if (!kakaoApiKey) return

    const initMap = () => {
      window.kakao.maps.load(() => {
        const defaultCenter = new window.kakao.maps.LatLng(37.5665, 126.9780)
        const map = new window.kakao.maps.Map(mapRef.current, {
          center: defaultCenter,
          level: 7,
        })
        mapInstance.current = map
      })
    }

    if (!window.kakao || !window.kakao.maps) {
      const script = document.createElement('script')
      script.src = `//dapi.kakao.com/v2/maps/sdk.js?appkey=${kakaoApiKey}&autoload=false`
      script.async = true
      script.onload = initMap
      document.head.appendChild(script)
    } else {
      initMap()
    }
  }, [kakaoApiKey])

  // 🔄 locations가 변할 때만 마커 추가, 삭제, 위치/이미지 갱신
  useEffect(() => {
    const map = mapInstance.current
    if (!map || !window.kakao || !window.kakao.maps) return

    const markerMap = markerRefs.current
    const nextLabels = locations.map(loc => loc.label)

    // 1. 기존에 있었지만, locations에 없는 마커 setMap(null) 후 제거
    Object.keys(markerMap).forEach(label => {
      if (!nextLabels.includes(label)) {
        markerMap[label].setMap(null)
        delete markerMap[label]
      }
    })

    // 2. 추가 & 위치/이미지 갱신
    locations.forEach((loc) => {
      const isSelected = selectedLocation?.label === loc.label
      const markerImage = new window.kakao.maps.MarkerImage(
        isSelected
          ? '../public/MapPin1.png'
          : '../public/MapPin2.png',
        new window.kakao.maps.Size(36, 36)
      )
      if (markerMap[loc.label]) {
        // 위치가 바뀌었으면 setPosition
        markerMap[loc.label].setPosition(new window.kakao.maps.LatLng(loc.lat, loc.lng))
        // 선택 마커 여부에 따라 이미지 갱신
        markerMap[loc.label].setImage(markerImage)
      } else {
        // 신규 마커 생성
        const marker = new window.kakao.maps.Marker({
          map,
          position: new window.kakao.maps.LatLng(loc.lat, loc.lng),
          title: loc.label,
          image: markerImage,
        })
        markerMap[loc.label] = marker
        window.kakao.maps.event.addListener(marker, 'click', () => {
          onLocationChange?.({ ...loc, label: loc.label })
        })
      }
    })
  }, [locations, selectedLocation])

  // 선택된 위치가 바뀌면 지도 중심 이동만 처리
  useEffect(() => {
    const map = mapInstance.current
    if (!map || !selectedLocation) return
    const newCenter = new window.kakao.maps.LatLng(selectedLocation.lat, selectedLocation.lng)
    map.panTo(newCenter)
  }, [selectedLocation])

  return (
    <div ref={mapRef} style={{ width: '100%', height: '94vh' }} />
  )
}

export default MapPage