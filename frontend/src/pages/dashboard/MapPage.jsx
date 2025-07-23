import React, { useEffect, useRef, useState } from 'react';

function MapPage({ selectedLocation }) {
  const mapRef = useRef(null);
  const markerRef = useRef(null);
  const [map, setMap] = useState(null);

useEffect(() => {
  const initMap = () => {
    const container = document.getElementById('map');
    const options = {
      center: new window.kakao.maps.LatLng(37.5665, 126.9780),
      level: 3,
    };
    const kakaoMap = new window.kakao.maps.Map(container, options);
    const marker = new window.kakao.maps.Marker({
      position: kakaoMap.getCenter(),
    });
    marker.setMap(kakaoMap);

    mapRef.current = kakaoMap;
    markerRef.current = marker;
    setMap(kakaoMap);
  };

  if (window.kakao && window.kakao.maps) {
    window.kakao.maps.load(initMap);
  } else {
    const existingScript = document.getElementById("kakao-map-script");
    if (!existingScript) {
      const script = document.createElement("script");
      script.id = "kakao-map-script";
      script.src = `https://dapi.kakao.com/v2/maps/sdk.js?appkey=cc0a3f17267a09a8e2670bb54f681f23&autoload=false`;
      script.async = true;
      document.head.appendChild(script);

      script.onload = () => window.kakao.maps.load(initMap);
    }
  }
}, []);

  useEffect(() => {
    if (!selectedLocation || !mapRef.current || !markerRef.current) return;

    const { lat, lng } = selectedLocation;
    const newCenter = new window.kakao.maps.LatLng(lat, lng);

    mapRef.current.setCenter(newCenter);
    markerRef.current.setPosition(newCenter);
  }, [selectedLocation]);

  return (
    <div style={{ width: '100%', height: '100%' }}>
      <div
        id="map"
        style={{
          width: '100%',
          height: '100vh',
          backgroundColor: '#dff7eb',
        }}
      ></div>
    </div>
  );
}

export default MapPage;
