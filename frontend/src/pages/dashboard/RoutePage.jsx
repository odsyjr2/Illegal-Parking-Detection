import { useEffect, useRef, useState } from 'react';

const KAKAO_JS_KEY = 'cc0a3f17267a09a8e2670bb54f681f23';
const KAKAO_REST_KEY = '31190e0b91ccecdd1178d3525ef71da3';

const VEHICLE_COLORS = ['#FF0000', '#00AAFF', '#00CC00', '#FF8C00', '#9370DB'];
const VEHICLE_MARKERS = [
  'https://t1.daumcdn.net/localimg/localimages/07/mapapidoc/marker_red.png',
  'https://t1.daumcdn.net/localimg/localimages/07/mapapidoc/markerStar.png',
  'https://t1.daumcdn.net/localimg/localimages/07/mapapidoc/markerStar.png',
  'https://t1.daumcdn.net/localimg/localimages/07/mapapidoc/marker_red.png',
  'https://t1.daumcdn.net/localimg/localimages/07/mapapidoc/markerStar.png'
];

// 백엔드 API 기본 URL
const BACKEND_API_URL = 'http://localhost:8080/api';

function RoutePage() {
  const mapRef = useRef(null);
  const mapInstance = useRef(null);
  const [vehicleRoutes, setVehicleRoutes] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [lastUpdated, setLastUpdated] = useState(null);

  const initMap = () => {
    const center = new window.kakao.maps.LatLng(37.5665, 126.9780);
    const map = new window.kakao.maps.Map(mapRef.current, {
      center,
      level: 6,
    });
    mapInstance.current = map;
  };

  // 백엔드에서 순찰 경로 데이터 가져오기
  const fetchPatrolRoutesFromAPI = async () => {
    try {
      setLoading(true);
      setError(null);
      
      console.log('🔍 백엔드에서 순찰 경로 조회 중...');
      
      const response = await fetch(`${BACKEND_API_URL}/patrol-routes`);
      
      if (!response.ok) {
        throw new Error(`API 요청 실패: ${response.status} ${response.statusText}`);
      }
      
      const result = await response.json();
      
      if (result.status !== 'SUCCESS') {
        throw new Error(result.message || 'API 응답 오류');
      }
      
      const routesData = result.data;
      console.log('📋 받은 경로 데이터:', routesData);
      
      if (!routesData || !routesData.routes || Object.keys(routesData.routes).length === 0) {
        console.warn('⚠️ 순찰 경로 데이터가 없습니다');
        setVehicleRoutes([]);
        setLastUpdated(null);
        return [];
      }
      
      // 백엔드 데이터를 기존 형식으로 변환
      const convertedRoutes = Object.entries(routesData.routes).map(([vehicleKey, routePoints], index) => {
        const vehicleId = vehicleKey.replace('vehicle_', '');
        const data = routePoints.map(point => ({
          x: point.경도,
          y: point.위도,
          place: point.장소
        }));
        
        return {
          vehicleKey,
          vehicleId: parseInt(vehicleId),
          data,
          color: VEHICLE_COLORS[index % VEHICLE_COLORS.length],
          markerIcon: VEHICLE_MARKERS[index % VEHICLE_MARKERS.length]
        };
      });
      
      setLastUpdated(routesData.updatedAt);
      console.log(`✅ ${convertedRoutes.length}대 차량 경로 데이터 변환 완료`);
      
      return convertedRoutes;
      
    } catch (error) {
      console.error('❌ 순찰 경로 조회 실패:', error);
      setError(error.message);
      return [];
    } finally {
      setLoading(false);
    }
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

  const loadPatrolRoutesFromAPI = async () => {
    try {
      console.log('🚀 순찰 경로 로딩 시작...');
      
      // 백엔드에서 경로 데이터 가져오기
      const convertedRoutes = await fetchPatrolRoutesFromAPI();
      
      if (convertedRoutes.length === 0) {
        console.warn('⚠️ 표시할 순찰 경로가 없습니다');
        setVehicleRoutes([]);
        return;
      }
      
      const routes = [];

      // 각 차량별 경로 처리
      for (let i = 0; i < convertedRoutes.length; i++) {
        const { vehicleKey, vehicleId, data, color, markerIcon } = convertedRoutes[i];
        
        if (data.length < 2) {
          console.warn(`⚠️ 차량 ${vehicleId}: 경로 데이터 부족 (${data.length}개 지점)`);
          continue;
        }

        // 첫 번째 차량의 첫 번째 지점으로 지도 중심 설정
        if (i === 0 && data[0]) {
          const map = mapInstance.current;
          map.setCenter(new window.kakao.maps.LatLng(data[0].y, data[0].x));
        }

        // 카카오 네비 API로 경로 그리기
        const origin = data[0];
        const destination = data[data.length - 1];
        const waypoints = data.slice(1, -1);

        try {
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

          // 지도에 경로 그리기
          drawRouteOnMap(sections, color);

          // 주소 정보와 마커 생성
          const addresses = [];
          for (let j = 0; j < data.length; j++) {
            const coord = data[j];
            
            // 백엔드에서 이미 장소명을 제공하므로 그것을 사용
            const placeName = coord.place || await fetchAddress(coord.y, coord.x);
            addresses.push({ text: placeName, lat: coord.y, lng: coord.x });

            // 마커 생성
            const marker = new window.kakao.maps.Marker({
              position: new window.kakao.maps.LatLng(coord.y, coord.x),
              map: mapInstance.current,
              image: new window.kakao.maps.MarkerImage(
                markerIcon,
                new window.kakao.maps.Size(16, 16)
              )
            });
            
            // 마커 클릭 이벤트
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
            id: `차량${vehicleId}`,
            color,
            addresses,
            distance: summary ? (summary.distance / 1000).toFixed(1) : '계산중',
            duration: summary ? Math.ceil(summary.duration / 60) : 0
          });

          console.log(`✅ 차량 ${vehicleId} 경로 처리 완료`);
          
        } catch (navError) {
          console.error(`❌ 차량 ${vehicleId} 네비게이션 API 오류:`, navError);
          
          // 네비게이션 API 실패시에도 기본 정보는 표시
          const addresses = data.map(coord => ({
            text: coord.place || '위치 정보',
            lat: coord.y,
            lng: coord.x
          }));
          
          routes.push({
            id: `차량${vehicleId}`,
            color,
            addresses,
            distance: '미계산',
            duration: 0
          });
        }
      }

      setVehicleRoutes(routes);
      console.log(`🎯 총 ${routes.length}대 차량 경로 로딩 완료`);
      
    } catch (error) {
      console.error('❌ 순찰 경로 로딩 실패:', error);
      setError(`경로 로딩 실패: ${error.message}`);
    }
  };

  const handleAddressClick = (lat, lng) => {
    const map = mapInstance.current;
    if (map) {
      map.panTo(new window.kakao.maps.LatLng(lat, lng));
    }
  };

  // 새로고침 함수
  const refreshRoutes = () => {
    if (mapInstance.current) {
      loadPatrolRoutesFromAPI();
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
          loadPatrolRoutesFromAPI();
        });
      };
      document.head.appendChild(script);
    } else {
      window.kakao.maps.load(() => {
        initMap();
        loadPatrolRoutesFromAPI();
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
        
        {/* 헤더 및 컨트롤 */}
        <div style={{ marginBottom: '1rem' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.5rem' }}>
            <h3 style={{ margin: 0 }}>🚗 차량별 경로</h3>
            <button 
              onClick={refreshRoutes}
              disabled={loading}
              style={{
                padding: '5px 10px',
                background: loading ? '#ccc' : '#007bff',
                color: 'white',
                border: 'none',
                borderRadius: '4px',
                cursor: loading ? 'not-allowed' : 'pointer',
                fontSize: '12px'
              }}
            >
              {loading ? '로딩...' : '새로고침'}
            </button>
          </div>
          
          {/* 상태 표시 */}
          {lastUpdated && (
            <div style={{ fontSize: '11px', color: '#666', marginBottom: '0.5rem' }}>
              마지막 업데이트: {new Date(lastUpdated).toLocaleString()}
            </div>
          )}
          
          {error && (
            <div style={{ 
              fontSize: '12px', 
              color: '#dc3545', 
              background: '#f8d7da', 
              padding: '8px', 
              borderRadius: '4px', 
              marginBottom: '0.5rem' 
            }}>
              ⚠️ {error}
            </div>
          )}
          
          {loading && (
            <div style={{ 
              fontSize: '12px', 
              color: '#007bff', 
              background: '#d1ecf1', 
              padding: '8px', 
              borderRadius: '4px', 
              marginBottom: '0.5rem' 
            }}>
              🔄 순찰 경로를 불러오는 중...
            </div>
          )}
        </div>
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