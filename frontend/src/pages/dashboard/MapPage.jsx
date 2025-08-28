import { useState, useEffect, useRef } from "react";
import axios from "axios";

// HTML 이스케이프 함수
const escapeHtml = (str = '') =>
  str.replace(/[&<>"']/g, s => ({
    '&': '&amp;', '<': '&lt;', '>': '&gt;',
    '"': '&quot;', "'": '&#39;'
  }[s]));

function MapPage({ selectedLocation, cctvData, onCctvSelect }) {
  const [ongoing, setOngoing] = useState([]);
  const [isMapReady, setIsMapReady] = useState(false);

  const carMarkersRef = useRef([]);
  const cctvMarkersRef = useRef([]);
  const mapRef = useRef(null);
  const mapInstance = useRef(null);
  const infoWindowRef = useRef(null);
  const didAutoFitRef = useRef(false);

  const kakaoApiKey = '9fabbd28c079827af4ab0436f07293ec';

  // Kakao 지도 초기화
  useEffect(() => {
    if (!kakaoApiKey) return;

    const initMap = () => {
      window.kakao.maps.load(() => {
        const defaultCenter = new window.kakao.maps.LatLng(37.4836, 127.0327);
        const map = new window.kakao.maps.Map(mapRef.current, {
          center: defaultCenter,
          level: 7,
        });
        mapInstance.current = map;
        infoWindowRef.current = new window.kakao.maps.InfoWindow({ zIndex: 3 });

        window.kakao.maps.event.addListener(map, 'click', () => {
          infoWindowRef.current?.close();
        });

        setIsMapReady(true);
      });
    };

    // Kakao 스크립트 로딩
    if (!window.kakao || !window.kakao.maps) {
      // 스크립트 중복 방지
      if (!document.getElementById("kakao-map-script")) {
        const script = document.createElement('script');
        script.id = "kakao-map-script";
        script.src = `//dapi.kakao.com/v2/maps/sdk.js?appkey=${kakaoApiKey}&autoload=false`;
        script.async = true;
        script.onload = initMap;
        document.head.appendChild(script);
      } else {
        // 이미 추가된 경우 onload 없이 바로 실행
        initMap();
      }
    } else {
      initMap();
    }
  }, [kakaoApiKey]);

  // 선택된 위치로 패닝
  useEffect(() => {
    if (!isMapReady || !mapInstance.current || !selectedLocation) return;
    const map = mapInstance.current;
    const { lat, lng } = selectedLocation;
    if (typeof lat !== 'number' || typeof lng !== 'number') return;
    const newCenter = new window.kakao.maps.LatLng(lat, lng);
    map.panTo(newCenter);
  }, [selectedLocation, isMapReady]);

  // 진행중 신고 조회 (폴링)
  useEffect(() => {
    let timer;
    const fetchOngoing = async () => {
      try {
        const res = await axios.get('/api/human-reports');
        const list = Array.isArray(res.data) ? res.data : [];
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
          }));
        setOngoing(onlyOngoing);
      } catch (e) {
        console.error('진행중 신고 조회 실패:', e);
      }
    };

    fetchOngoing();
    timer = setInterval(fetchOngoing, 10000);
    return () => clearInterval(timer);
  }, []);

  // 차량(Car) 마커
  useEffect(() => {
    if (!isMapReady || !mapInstance.current || !window.kakao || !window.kakao.maps) return;
    const map = mapInstance.current;

    const defaultCarImage = new window.kakao.maps.MarkerImage(
      '/car.png', new window.kakao.maps.Size(50, 50));
    const activeCarImage = new window.kakao.maps.MarkerImage(
      '/car.png', new window.kakao.maps.Size(50, 50));

    // 기존 마커 제거
    carMarkersRef.current.forEach(marker => marker.setMap(null));
    carMarkersRef.current = [];

    ongoing.forEach(o => {
      if (!o.lat || !o.lng || isNaN(o.lat) || isNaN(o.lng)) return;
      const pos = new window.kakao.maps.LatLng(o.lat, o.lng);
      const marker = new window.kakao.maps.Marker({
        map,
        position: pos,
        image: defaultCarImage,
        title: String(o.title ?? o.id),
        clickable: true,
      });
      carMarkersRef.current.push(marker);

      window.kakao.maps.event.addListener(marker, 'click', () => {
        // 모든 차량 마커 기본 이미지로
        carMarkersRef.current.forEach(m => m.setImage(defaultCarImage));
        // 클릭한 차량만 active 이미지로
        marker.setImage(activeCarImage);

        if (!infoWindowRef.current) return;
        const title = escapeHtml(o.title || '신고');
        const loc = escapeHtml(o.location || '');
        const created = o.createdAt ? escapeHtml(String(o.createdAt).slice(0, 10)) : '';
        const content = `
          <div style="padding:10px 12px;min-width:220px;max-width:260px;">
            <div style="font-weight:700;margin-bottom:2px;">${title}</div>
            <div style="font-size:12px;color:#555;margin-bottom:4px;">상태: ${o.status}</div>
            <div style="font-size:12px;color:#555;word-break:break-all;">위치: ${loc}</div>
            <div style="font-size:12px;color:#888;margin-top:4px;">등록일: ${created}</div>
          </div>`;
        infoWindowRef.current.setContent(content);
        infoWindowRef.current.open(map, marker);
      });
    });

    // 자동 bounds 맞춤
    if (ongoing.length > 0 && !didAutoFitRef.current) {
      const bounds = new window.kakao.maps.LatLngBounds();
      ongoing.forEach(o => bounds.extend(new window.kakao.maps.LatLng(o.lat, o.lng)));
      if (!bounds.isEmpty()) map.setBounds(bounds);
      didAutoFitRef.current = true;
    }
  }, [ongoing, isMapReady]);

  // CCTV 마커 및 클릭 이벤트
  useEffect(() => {
    if (!isMapReady || !mapInstance.current || !window.kakao || !window.kakao.maps) return;
    const map = mapInstance.current;

    const cctvList = Array.isArray(cctvData) ? cctvData : [];
    const defaultImage = new window.kakao.maps.MarkerImage(
      '/MapPin2.png', new window.kakao.maps.Size(36, 36));
    const activeImage = new window.kakao.maps.MarkerImage(
      '/MapPin1.png', new window.kakao.maps.Size(36, 36));

    // 기존 CCTV 마커 제거
    cctvMarkersRef.current.forEach(marker => marker.setMap(null));
    cctvMarkersRef.current = [];

    cctvList.forEach(c => {
      const pos = new window.kakao.maps.LatLng(c.latitude, c.longitude);
      const marker = new window.kakao.maps.Marker({
        map,
        position: pos,
        title: c.streamName,
        image: defaultImage,
        clickable: true,
      });
      cctvMarkersRef.current.push(marker);

      window.kakao.maps.event.addListener(marker, 'click', () => {
        // 모든 CCTV 마커 기본 이미지로
        cctvMarkersRef.current.forEach(m => m.setImage(defaultImage));
        // 클릭한 CCTV만 active 이미지로
        marker.setImage(activeImage);
        onCctvSelect?.(c);

        if (infoWindowRef.current) {
          const content = `
            <div style="padding:8px 10px;min-width:180px;">
              <div style="font-weight:700;margin-bottom:4px;">${escapeHtml(c.streamName)}</div>
              <div style="font-size:12px;color:#666;">(${c.latitude?.toFixed(5)}, ${c.longitude?.toFixed(5)})</div>
            </div>`;
          infoWindowRef.current.setContent(content);
          infoWindowRef.current.open(map, marker);
        }
      });
    });
  }, [cctvData, onCctvSelect, isMapReady]);

  // 선택 상태에 따라 CCTV 마커 active 이미지 동기화
  useEffect(() => {
    if (!isMapReady || !window.kakao || !window.kakao.maps) return;
    const cctvList = Array.isArray(cctvData) ? cctvData : [];
    const defaultImage = new window.kakao.maps.MarkerImage('/MapPin2.png', new window.kakao.maps.Size(36, 36));
    const activeImage = new window.kakao.maps.MarkerImage('/MapPin1.png', new window.kakao.maps.Size(36, 36));

    cctvMarkersRef.current.forEach((marker, idx) => {
      const cctv = cctvList[idx];

      if (
        cctv &&
        (
          cctv.streamName === selectedLocation?.label ||
          (cctv.latitude === selectedLocation?.lat && cctv.longitude === selectedLocation?.lng)
        )
      ) {
        marker.setImage(activeImage);
      } else {
        marker.setImage(defaultImage);
      }
    });
  }, [selectedLocation, cctvData, isMapReady]);

  return <div ref={mapRef} style={{ width: "100%", height: "94vh" }} />;
}

export default MapPage;