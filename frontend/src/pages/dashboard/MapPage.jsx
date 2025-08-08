import { useState, useEffect, useRef } from 'react'
import axios from 'axios'

// 🧭 예시 위치(기존 유지)
const locations = [
  { label: '강남구1', lat: 37.5172, lng: 127.0473 },
  { label: '강남구2', lat: 37.5171, lng: 127.0470 },
  { label: '관악구', lat: 37.4784, lng: 126.9516 },
  { label: '송파구', lat: 37.5145, lng: 127.1056 },
]

const escapeHtml = (str = '') => str.replace(/[&<>"']/g, s => ({
  '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'
}[s]))

function MapPage({ selectedLocation, onLocationChange }) {
  // ✅ 진행중 신고 목록 상태
  const [ongoing, setOngoing] = useState([])

  const carMarkersRef = useRef({}) // { [id]: kakao.maps.Marker }
  const mapRef = useRef(null)
  const mapInstance = useRef(null)
  const markerRefs = useRef({})   // 행정구역 마커 { [label]: Marker }
  const infoWindowRef = useRef(null) // 하나만 재사용
  const didAutoFitRef = useRef(false) // 처음 한 번만 자동 맞춤

  const kakaoApiKey = 'cc0a3f17267a09a8e2670bb54f681f23'

  // ✅ Kakao Map 최초 1회 로딩
  useEffect(() => {
    if (!kakaoApiKey) return

    const initMap = () => {
      window.kakao.maps.load(() => {
        const defaultCenter = new window.kakao.maps.LatLng(37.4836, 127.0327) // 서초구 중심
        const map = new window.kakao.maps.Map(mapRef.current, {
          center: defaultCenter,
          level: 7,
        })
        mapInstance.current = map
        infoWindowRef.current = new window.kakao.maps.InfoWindow({ zIndex: 3 })

        // 지도 빈 곳 클릭 시 닫기
        window.kakao.maps.event.addListener(map, 'click', () => {
          infoWindowRef.current && infoWindowRef.current.close()
        })
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

  // ✅ 좌측 리스트 마커(행정구역) 동기화 — 기존 로직 유지 + 클릭 시 간단 인포윈도우
  useEffect(() => {
    const map = mapInstance.current
    if (!map || !window.kakao || !window.kakao.maps) return

    const markerMap = markerRefs.current
    const nextLabels = locations.map(loc => loc.label)

    // 제거
    Object.keys(markerMap).forEach(label => {
      if (!nextLabels.includes(label)) {
        markerMap[label].setMap(null)
        delete markerMap[label]
      }
    })

    // 추가/갱신
    locations.forEach((loc) => {
      const markerImage = new window.kakao.maps.MarkerImage(
        '/MapPin2.png',
        new window.kakao.maps.Size(36, 36)
      )
      if (markerMap[loc.label]) {
        markerMap[loc.label].setPosition(new window.kakao.maps.LatLng(loc.lat, loc.lng))
        markerMap[loc.label].setImage(markerImage)
      } else {
        const marker = new window.kakao.maps.Marker({
          map,
          position: new window.kakao.maps.LatLng(loc.lat, loc.lng),
          title: loc.label,
          image: markerImage,
        })
        markerMap[loc.label] = marker
        window.kakao.maps.event.addListener(marker, 'click', () => {
          onLocationChange?.({ ...loc, label: loc.label })
          // 행정구역 마커 클릭 시 간단 인포윈도우
          if (infoWindowRef.current) {
            const content = `<div style="padding:8px 10px;min-width:160px;">
              <div style="font-weight:700;margin-bottom:4px;">${escapeHtml(loc.label)}</div>
              <div style="font-size:12px;color:#666;">(${loc.lat.toFixed(5)}, ${loc.lng.toFixed(5)})</div>
            </div>`
            infoWindowRef.current.setContent(content)
            infoWindowRef.current.open(map, marker)
          }
        })
      }
    })
  }, [locations, selectedLocation])

  // ✅ 선택된 위치로 패닝 — 기존 유지
  useEffect(() => {
    const map = mapInstance.current
    if (!map || !selectedLocation) return
    const newCenter = new window.kakao.maps.LatLng(selectedLocation.lat, selectedLocation.lng)
    map.panTo(newCenter)
  }, [selectedLocation])

  // ✅ 진행중 신고 주기적 조회 (10초 간격)
  useEffect(() => {
    let timer

    const fetchOngoing = async () => {
      try {
        const res = await axios.get('http://localhost:8080/api/human-reports')
        const list = Array.isArray(res.data) ? res.data : []
        const onlyOngoing = list
          .filter(r => r.status === '진행중')
          .filter(r => r.latitude && r.longitude)
          .map(r => ({
            id: r.id,
            lat: parseFloat(r.latitude),
            lng: parseFloat(r.longitude),
            title: r.title || '신고',
            status: r.status,
            location: r.location,
            createdAt: r.createdAt,
            imageURL: r.imageURL, // "/files/.." 같은 형태 가정
            reason: r.reason,
          }))
        setOngoing(onlyOngoing)
      } catch (e) {
        console.error('진행중 신고 조회 실패:', e)
      }
    }

    fetchOngoing()
    timer = setInterval(fetchOngoing, 10000)
    return () => clearInterval(timer)
  }, [])

  // ✅ 진행중 차량(Car) 마커 동기화 + 클릭 시 인포윈도우
  useEffect(() => {
    const map = mapInstance.current
    if (!map || !window.kakao || !window.kakao.maps) return

    const markers = carMarkersRef.current
    const nextIds = new Set(ongoing.map(o => String(o.id)))

    // 1) 삭제: 이제 진행중이 아닌 마커 제거
    Object.keys(markers).forEach(id => {
      if (!nextIds.has(id)) {
        markers[id].setMap(null)
        delete markers[id]
      }
    })

    // 2) 추가/갱신
    const carImage = new window.kakao.maps.MarkerImage(
      '/car.png', // public/car.png 배치 필요
      new window.kakao.maps.Size(50, 50)
    )

    ongoing.forEach(o => {
      if (!o.lat || !o.lng || isNaN(o.lat) || isNaN(o.lng)) return
      const pos = new window.kakao.maps.LatLng(o.lat, o.lng)

      if (markers[o.id]) {
        // 위치 갱신
        markers[o.id].setPosition(pos)
      } else {
        const marker = new window.kakao.maps.Marker({
          map,
          position: pos,
          image: carImage,
          title: String(o.title ?? o.id),
          clickable: true,
        })
        markers[o.id] = marker

        // 📌 클릭 시 인포윈도우 오픈
        window.kakao.maps.event.addListener(marker, 'click', () => {
          if (!infoWindowRef.current) return
          const title = escapeHtml(o.title || '신고')
          const loc = escapeHtml(o.location || '')
          const created = o.createdAt ? escapeHtml(String(o.createdAt).slice(0,10)) : ''

          const content = `
            <div style="padding:10px 12px;min-width:220px;max-width:260px;">              <div style="font-weight:700;margin-bottom:2px;">${title}</div>
              <div style="font-size:12px;color:#555;margin-bottom:4px;">상태: ${o.status}</div>
              <div style="font-size:12px;color:#555;word-break:break-all;">위치: ${loc}</div>
              <div style="font-size:12px;color:#888;margin-top:4px;">등록일: ${created}</div>
            </div>`

          infoWindowRef.current.setContent(content)
          infoWindowRef.current.open(map, marker)
        })
      }
    })

    // 3) 화면에 모두 보이도록 자동 맞춤 — 처음 한 번만
    if (ongoing.length > 0 && !didAutoFitRef.current) {
      const bounds = new window.kakao.maps.LatLngBounds()
      ongoing.forEach(o => {
        if (!o.lat || !o.lng || isNaN(o.lat) || isNaN(o.lng)) return
        bounds.extend(new window.kakao.maps.LatLng(o.lat, o.lng))
      })
      if (!bounds.isEmpty()) map.setBounds(bounds)
      didAutoFitRef.current = true // 이후에는 사용자 제어 유지
    }
  }, [ongoing])

  return (
    <div ref={mapRef} style={{ width: '100%', height: '94vh' }} />
  )
}

export default MapPage
