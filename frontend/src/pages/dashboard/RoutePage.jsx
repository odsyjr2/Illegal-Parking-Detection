import { useEffect, useRef, useState } from 'react';
import Papa from 'papaparse';

const KAKAO_JS_KEY = 'cc0a3f17267a09a8e2670bb54f681f23';
const KAKAO_REST_KEY = '31190e0b91ccecdd1178d3525ef71da3';

const VEHICLE_COLORS = ['#FF0000', '#00AAFF', '#00CC00'];
const VEHICLE_FILES = [
  '/vehicle_route_1.csv',
  '/vehicle_route_2.csv',
  '/vehicle_route_3.csv'
];

const VEHICLE_MARKERS = [
  'https://t1.daumcdn.net/localimg/localimages/07/mapapidoc/marker_red.png',
  'https://t1.daumcdn.net/localimg/localimages/07/mapapidoc/markerStar.png',
  'https://t1.daumcdn.net/localimg/localimages/07/mapapidoc/markerStar.png'
];

function RoutePage() {
  const mapRef = useRef(null);
  const mapInstance = useRef(null);
  const [vehicleRoutes, setVehicleRoutes] = useState([]);

  const initMap = () => {
    const center = new window.kakao.maps.LatLng(37.5665, 126.9780);
    const map = new window.kakao.maps.Map(mapRef.current, {
      center,
      level: 6,
    });
    mapInstance.current = map;
  };

  const fetchAddress = async (lat, lng) => {
    const res = await fetch(`https://dapi.kakao.com/v2/local/geo/coord2address.json?x=${lng}&y=${lat}`, {
      headers: {
        Authorization: `KakaoAK ${KAKAO_REST_KEY}`,
      },
    });
    const json = await res.json();
    const road = json.documents?.[0]?.road_address?.address_name || '';
    const jibun = json.documents?.[0]?.address?.address_name || '';
    return road || jibun || '주소 없음';
  };

  const drawRouteOnMap = (sections, color) => {
    const linePath = [];

    sections.forEach((section) => {
      section.roads.forEach((road) => {
        for (let i = 0; i < road.vertexes.length; i += 2) {
          const lng = road.vertexes[i];
          const lat = road.vertexes[i + 1];
          linePath.push(new window.kakao.maps.LatLng(lat, lng));
        }
      });
    });

    const map = mapInstance.current;
    const polyline = new window.kakao.maps.Polyline({
      path: linePath,
      strokeWeight: 5,
      strokeColor: color,
      strokeOpacity: 0.8,
      strokeStyle: 'solid',
    });

    polyline.setMap(map);
  };

  const loadMultipleVehicleFiles = async () => {
    const routes = [];

    for (let i = 0; i < VEHICLE_FILES.length; i++) {
      const file = VEHICLE_FILES[i];
      const color = VEHICLE_COLORS[i % VEHICLE_COLORS.length];
      const markerIcon = VEHICLE_MARKERS[i % VEHICLE_MARKERS.length];
      const res = await fetch(file);
      const text = await res.text();

      await new Promise((resolve) => {
        Papa.parse(text, {
          header: true,
          skipEmptyLines: true,
          complete: async (results) => {
            const data = results.data.map(row => ({
              x: parseFloat(row['경도']),
              y: parseFloat(row['위도'])
            })).filter(p => !isNaN(p.x) && !isNaN(p.y));

            if (data.length < 2) return resolve();

            if (i === 0 && data[0]) {
              const map = mapInstance.current;
              map.setCenter(new window.kakao.maps.LatLng(data[0].y, data[0].x));
            }

            const origin = data[0];
            const destination = data[data.length - 1];
            const waypoints = data.slice(1, -1);

            const res = await fetch('https://apis-navi.kakaomobility.com/v1/waypoints/directions', {
              method: 'POST',
              headers: {
                Authorization: `KakaoAK ${KAKAO_REST_KEY}`,
                'Content-Type': 'application/json'
              },
              body: JSON.stringify({ origin, destination, waypoints })
            });

            const json = await res.json();
            const sections = json.routes?.[0]?.sections || [];
            const summary = json.routes?.[0]?.summary;

            drawRouteOnMap(sections, color);

            const addresses = [];
            for (let j = 0; j < data.length; j++) {
              const coord = data[j];
              const address = await fetchAddress(coord.y, coord.x);
              addresses.push({ text: address, lat: coord.y, lng: coord.x });

              // 마커 생성 + 클릭 시 panTo 이벤트 추가
              const marker = new window.kakao.maps.Marker({
                position: new window.kakao.maps.LatLng(coord.y, coord.x),
                map: mapInstance.current,
                image: new window.kakao.maps.MarkerImage(
                  markerIcon,
                  new window.kakao.maps.Size(16, 16)
                )
              });
              window.kakao.maps.event.addListener(marker, 'click', () => {
                mapInstance.current.panTo(marker.getPosition());
              });
            }

            // 출발 오버레이
            new window.kakao.maps.CustomOverlay({
              position: new window.kakao.maps.LatLng(data[0].y, data[0].x),
              content: `<div style="background:#fff;color:${color};padding:2px 6px;font-size:11px;border-radius:8px;border:1px solid ${color};transform:translate(-50%,-100%)">출발</div>`
            }).setMap(mapInstance.current);

            // 도착 오버레이
            new window.kakao.maps.CustomOverlay({
              position: new window.kakao.maps.LatLng(data[data.length - 1].y, data[data.length - 1].x),
              content: `<div style="background:#fff;color:${color};padding:2px 6px;font-size:11px;border-radius:8px;border:1px solid ${color};transform:translate(-50%,-100%)">도착</div>`
            }).setMap(mapInstance.current);

            routes.push({
              id: `차량${i + 1}`,
              color,
              addresses,
              distance: (summary?.distance / 1000).toFixed(1),
              duration: Math.ceil(summary?.duration / 60)
            });

            resolve();
          }
        });
      });
    }

    setVehicleRoutes(routes);
  };

  const handleAddressClick = (lat, lng) => {
    const map = mapInstance.current;
    if (map) {
      map.panTo(new window.kakao.maps.LatLng(lat, lng));
    }
  };

  useEffect(() => {
    if (!window.kakao || !window.kakao.maps) {
      const script = document.createElement('script');
      script.src = `//dapi.kakao.com/v2/maps/sdk.js?appkey=${KAKAO_JS_KEY}&autoload=false`;
      script.async = true;
      script.onload = () => {
        window.kakao.maps.load(() => {
          initMap();
          loadMultipleVehicleFiles();
        });
      };
      document.head.appendChild(script);
    } else {
      window.kakao.maps.load(() => {
        initMap();
        loadMultipleVehicleFiles();
      });
    }
  }, []);

  return (
    <div style={{ display: 'flex' }}>
      <div ref={mapRef} style={{ width: '70%', height: '95vh',}} />
      <div style={{ 
        width: '30%', 
        padding: '1rem', 
        overflowY: 'auto', 
        backgroundColor: '#f9f9f9', 
        borderLeft: '1px solid #ccc', 
        height: '90vh', 
        paddingBottom: '20px' }}>
        <h3 style={{ marginBottom: '1rem' }}>🚗 차량별 경로</h3>
        {vehicleRoutes.map((vehicle, idx) => (
          <div key={idx} style={{ 
            marginBottom: idx === vehicleRoutes.length - 1 ? '2rem' : '1rem', // 마지막 아이템은 더 크게
            padding: '10px',
            background: '#fff',
            borderRadius: '8px',
            boxShadow: '0 1px 3px rgba(0,0,0,0.1)'
          }}>
            <div style={{ fontWeight: 'bold', color: vehicle.color }}>{vehicle.id}</div>
            <div style={{ fontSize: '13px', margin: '4px 0', color: '#555' }}>
              📏 거리: {vehicle.distance}km &nbsp;&nbsp; ⏱ 시간: {vehicle.duration}분
            </div>
            <ol style={{ paddingLeft: '1.2rem', fontSize: '14px', marginTop: '8px' }}>
              {vehicle.addresses.map((addr, i) => (
                <li
                  key={i}
                  onClick={() => handleAddressClick(addr.lat, addr.lng)}
                  style={{ marginBottom: '6px', cursor: 'pointer', color: '#0066cc' }}
                >
                  {addr.text}
                </li>
              ))}
            </ol>
          </div>
        ))}
      </div>
    </div>
  );
}

export default RoutePage;