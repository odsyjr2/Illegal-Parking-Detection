import { useEffect, useRef } from 'react'

// 📍 지도에 표시할 위치 목록
const locations = [
  { label: '강남구1', lat: 37.5172, lng: 127.0473 },
  { label: '강남구2', lat: 37.5171, lng: 127.0470 },
  { label: '관악구', lat: 37.4784, lng: 126.9516 },
  { label: '송파구', lat: 37.5145, lng: 127.1056 }
]

function MapPage({ selectedLocation, onLocationChange }) {
  const mapRef = useRef(null) // 🗺️ 실제 지도를 삽입할 DOM ref
  const mapInstance = useRef(null) // 🗺️ Map 객체를 저장할 ref (초기화 후 유지)
  const markerRefs = useRef([]) // 📍 마커 객체 배열을 저장하여 재사용 관리

  const kakaoApiKey = import.meta.env.VITE_KAKAOMAP_KEY

  // ✅ map 객체는 한 번만 만들고 저장
  useEffect(() => {
    if (!kakaoApiKey) return

    const renderMarkers = () => {
      const map = mapInstance.current
      if (!map) return

      // 🔁 기존 마커 제거
      markerRefs.current.forEach(m => m.setMap(null))
      markerRefs.current = []

      // 📍 마커 생성
      locations.forEach((loc) => {
        // ✅ 현재 선택된 마커와 비교
        const isSelected = selectedLocation?.label === loc.label

        // 🖼️ 마커 이미지 설정 (선택된 마커는 빨간색)
        const markerImage = new window.kakao.maps.MarkerImage(
          isSelected
            ? 'https://t1.daumcdn.net/localimg/localimages/07/mapapidoc/marker_red.png'
            : 'https://t1.daumcdn.net/localimg/localimages/07/mapapidoc/markerStar.png',
          new window.kakao.maps.Size(36, 36)
        )

        // 📍 마커 생성
        const marker = new window.kakao.maps.Marker({
          map,
          position: new window.kakao.maps.LatLng(loc.lat, loc.lng),
          title: loc.label,
          image: markerImage
        })

        // 📌 마커 저장
        markerRefs.current.push(marker)

        // 💬 마커 클릭시 위치 선택 이벤트
        window.kakao.maps.event.addListener(marker, 'click', () => {
          onLocationChange?.({ ...loc, label: loc.label })
        })
      })
    }

    // ✅ 최초 1회 지도 생성
    const initMap = () => {
      window.kakao.maps.load(() => {
        const defaultCenter = new window.kakao.maps.LatLng(37.5665, 126.9780) // 서울 중심 기본값

        const map = new window.kakao.maps.Map(mapRef.current, {
          center: defaultCenter,
          level: 7 // ✅ 줌 레벨은 여기서만 설정됨
        })

        mapInstance.current = map

        // 📍 초기 마커 그리기
        renderMarkers()
      })
    }

    // 📦 스크립트 동적 삽입 + map 생성
    if (!window.kakao || !window.kakao.maps) {
      const script = document.createElement('script')
      script.src = `//dapi.kakao.com/v2/maps/sdk.js?appkey=${kakaoApiKey}&autoload=false`
      script.async = true
      script.onload = initMap
      document.head.appendChild(script)
    } else {
      initMap()
    }

    // 📌 selectedLocation 변경 시 마커 다시 렌더링
  }, [kakaoApiKey]) // 🚨 스크립트와 지도는 한 번만 생성되므로 selectedLocation은 여기서 분리

  // 🎯 선택된 위치가 바뀔 때 → panTo + 마커 갱신
  useEffect(() => {
    const map = mapInstance.current
    if (!map) return

    if (selectedLocation) {
      const newCenter = new window.kakao.maps.LatLng(selectedLocation.lat, selectedLocation.lng)
      map.panTo(newCenter)
    }

    // 마커 스타일 (선택된 마커 빨간색으로) 갱신
    if (window.kakao && window.kakao.maps) {
      // 해당 시점에 Kakao 객체가 로딩되어 있다면 마커 다시 그림
      const renderMarkers = () => {
        markerRefs.current.forEach(m => m.setMap(null))
        markerRefs.current = []

        locations.forEach((loc) => {
          const isSelected = selectedLocation?.label === loc.label
          const markerImage = new window.kakao.maps.MarkerImage(
            isSelected
              ? '../public/MapPin1.png'
              : '../public/MapPin2.png',
            new window.kakao.maps.Size(36, 36)
          )

          const marker = new window.kakao.maps.Marker({
            map,
            position: new window.kakao.maps.LatLng(loc.lat, loc.lng),
            title: loc.label,
            image: markerImage
          })

          markerRefs.current.push(marker)

          window.kakao.maps.event.addListener(marker, 'click', () => {
            onLocationChange?.({ ...loc, label: loc.label })
          })
        })
      }

      renderMarkers()
    }
  }, [selectedLocation])

  return (
    <div ref={mapRef} style={{ width: '100%', height: '94vh' }} />
  )
}

export default MapPage
