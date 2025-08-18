import { useState, useEffect, useRef } from 'react'
import axios from 'axios'

// 🧭 예시 위치(기존 유지)
const locations = [
  { label: '강남구', lat: 37.5172, lng: 127.0473 },
  { label: '관악구', lat: 37.4784, lng: 126.9516 },
  { label: '송파구', lat: 37.5145, lng: 127.1056 },
]

const escapeHtml = (str = '') => str.replace(/[&<>"']/g, s => ({
  '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'
}[s]))

// ✅ API 응답 구조 그대로 하드코딩 (CCTV 데이터)
const cctvData = {
  response: {
    coordtype: 1,
    data: [
      {
        roadsectionid: "",
        coordx: 126.8102, // 경도(lng)
        coordy: 35.0411,  // 위도(lat)
        cctvresolution: "",
        filecreatetime: "",
        cctvtype: 1,
        cctvformat: "HLS",
        cctvname: "[국도1호선]나주산포",
        cctvurl: "http://sample1/"
      },
      {
        roadsectionid: "",
        coordx: 126.9516,
        coordy: 35.0811,
        cctvresolution: "",
        filecreatetime: "",
        cctvtype: 1,
        cctvformat: "HLS",
        cctvname: "[국도22호선]광주너릿재T",
        cctvurl: "http://sample2/"
      }
    ]
  }
}

function MapPage({ selectedLocation, onLocationChange, cctvData, onCctvSelect }) {
  // ✅ 진행중 신고 목록 상태
  const [ongoing, setOngoing] = useState([])

  const carMarkersRef = useRef({})     // 차량 마커 { [id]: Marker }
  const cctvMarkersRef = useRef({})    // CCTV 마커 { [idx]: Marker }
  const markerRefs = useRef({})        // 행정구역 마커 { [label]: Marker }
  const mapRef = useRef(null)
  const mapInstance = useRef(null)
  const infoWindowRef = useRef(null)
  const didAutoFitRef = useRef(false)

  const kakaoApiKey = '9fabbd28c079827af4ab0436f07293ec'

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

  // ✅ 좌측 리스트 마커(행정구역)
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

  // ✅ 선택된 위치로 패닝
  useEffect(() => {
    const map = mapInstance.current
    if (!map || !selectedLocation) return
    const newCenter = new window.kakao.maps.LatLng(selectedLocation.lat, selectedLocation.lng)
    map.panTo(newCenter)
  }, [selectedLocation])

  // ✅ 진행중 신고 조회
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
            imageURL: r.imageURL,
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

  // ✅ 진행중 차량(Car) 마커
  useEffect(() => {
    const map = mapInstance.current
    if (!map || !window.kakao || !window.kakao.maps) return

    const markers = carMarkersRef.current
    const nextIds = new Set(ongoing.map(o => String(o.id)))

    Object.keys(markers).forEach(id => {
      if (!nextIds.has(id)) {
        markers[id].setMap(null)
        delete markers[id]
      }
    })

    const carImage = new window.kakao.maps.MarkerImage(
      '/car.png',
      new window.kakao.maps.Size(50, 50)
    )

    ongoing.forEach(o => {
      if (!o.lat || !o.lng || isNaN(o.lat) || isNaN(o.lng)) return
      const pos = new window.kakao.maps.LatLng(o.lat, o.lng)

      if (markers[o.id]) {
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

        window.kakao.maps.event.addListener(marker, 'click', () => {
          if (!infoWindowRef.current) return
          const title = escapeHtml(o.title || '신고')
          const loc = escapeHtml(o.location || '')
          const created = o.createdAt ? escapeHtml(String(o.createdAt).slice(0,10)) : ''
          const content = `
            <div style="padding:10px 12px;min-width:220px;max-width:260px;">
              <div style="font-weight:700;margin-bottom:2px;">${title}</div>
              <div style="font-size:12px;color:#555;margin-bottom:4px;">상태: ${o.status}</div>
              <div style="font-size:12px;color:#555;word-break:break-all;">위치: ${loc}</div>
              <div style="font-size:12px;color:#888;margin-top:4px;">등록일: ${created}</div>
            </div>`
          infoWindowRef.current.setContent(content)
          infoWindowRef.current.open(map, marker)
        })
      }
    })

    if (ongoing.length > 0 && !didAutoFitRef.current) {
      const bounds = new window.kakao.maps.LatLngBounds()
      ongoing.forEach(o => {
        if (!o.lat || !o.lng || isNaN(o.lat) || isNaN(o.lng)) return
        bounds.extend(new window.kakao.maps.LatLng(o.lat, o.lng))
      })
      if (!bounds.isEmpty()) map.setBounds(bounds)
      didAutoFitRef.current = true
    }
  }, [ongoing])

  // ✅ CCTV 마커
  useEffect(() => {
    const map = mapInstance.current
    if (!map || !window.kakao || !window.kakao.maps) return

    const cctvList = cctvData?.response?.data ?? []   // ✅ props 사용
    const markers = cctvMarkersRef.current

    // 기존 CCTV 마커 제거
    Object.values(markers).forEach(m => m.setMap(null))
    cctvMarkersRef.current = {}

    const defaultImage = new window.kakao.maps.MarkerImage(
      '/MapPin2.png',
      new window.kakao.maps.Size(36, 36)
    )
    const activeImage = new window.kakao.maps.MarkerImage(
      '/MapPin1.png',
      new window.kakao.maps.Size(36, 36)
    )

    cctvList.forEach((c, idx) => {
      const pos = new window.kakao.maps.LatLng(c.coordy, c.coordx)
      const marker = new window.kakao.maps.Marker({
        map,
        position: pos,
        title: c.cctvname,
        image: defaultImage,
        clickable: true,
      })

      cctvMarkersRef.current[idx] = marker

      window.kakao.maps.event.addListener(marker, 'click', () => {
        // 모든 마커 기본 이미지로 리셋
        Object.values(cctvMarkersRef.current).forEach(m => m.setImage(defaultImage))
        marker.setImage(activeImage)

        // ✅ 선택된 CCTV 부모로 전달
        onCctvSelect?.(c)

        // 인포윈도우 표시
        if (infoWindowRef.current) {
          const content = `
            <div style="padding:8px 10px;min-width:180px;">
              <div style="font-weight:700;margin-bottom:4px;">${escapeHtml(c.cctvname)}</div>
              <div style="font-size:12px;color:#666;">(${c.coordy.toFixed(5)}, ${c.coordx.toFixed(5)})</div>
              <div style="font-size:12px;color:#007bff;cursor:pointer;">
                <a href="${escapeHtml(c.cctvurl)}" target="_blank">CCTV 보기</a>
              </div>
            </div>`
          infoWindowRef.current.setContent(content)
          infoWindowRef.current.open(map, marker)
        }
      })
    })
  }, [cctvData])  // ✅ props로 받은 값이 바뀔 때만 갱신

  return (
    <div ref={mapRef} style={{ width: '100%', height: '94vh' }} />
  )
}

export default MapPage
