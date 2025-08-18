import { useState, useEffect } from "react";
import axios from "axios";
import Hls from "hls.js/dist/hls.min.js"; // Vite 호환 import
import MapPage from "./MapPage";
import InfoPanel from "./InfoPanel";
import RoutePage from "./RoutePage";
import "./MainPage.css";

function AlertBox({ alerts, onDismiss }) {
  return (
    <div className="alert-box">
      {alerts.map((alert) => (
        <div
          key={alert.id}
          className="alert-item"
          onClick={() => onDismiss(alert.id)}
        >
          {alert.message}
        </div>
      ))}
    </div>
  );
}

function RoutePanel() {
  return (
    <div className="route-panel" style={{ textAlign: "center" }}>
      <RoutePage />
    </div>
  );
}

function CctvSelector({ cctvList, selectedCctv, onSelect }) {
  return (
    <div
      style={{
        position: "absolute",
        top: 10,
        left: 10,
        zIndex: 1000,
        backgroundColor: "white",
        borderRadius: 10,
        boxShadow: "0 2px 12px rgba(0,0,0,0.15)",
        padding: 12,
        width: 280,
        display: "flex",
        flexDirection: "column",
        gap: 10,
        userSelect: "none",
      }}
    >
      <select
        value={selectedCctv?.streamName || ""}
        onChange={(e) => {
          const selected = cctvList.find(
            (c) => c.streamName === e.target.value
          );
          if (selected) onSelect(selected);
        }}
        style={{
          width: "100%",
          padding: 8,
          borderRadius: 6,
          border: "1px solid #ccc",
          cursor: "pointer",
          fontSize: 14,
          outline: "none",
        }}
      >
        <option value="">--- CCTV 선택 ---</option>
        {cctvList.map((c, idx) => (
          <option key={idx} value={c.streamName}>
            {c.streamName || "CCTV 미선택"}
          </option>
        ))}
      </select>

      {selectedCctv?.streamUrl && (
        <video
          id="cctv-player"
          controls
          autoPlay
          muted
          style={{
            width: "100%",
            borderRadius: 8,
          }}
        />
      )}
    </div>
  );
}

function MainPage() {
  const [selectedCctv, setSelectedCctv] = useState(null);
  const [tab, setTab] = useState("map");
  const [alerts, setAlerts] = useState([]);
  const [cctvList, setCctvList] = useState([]);

  // CCTV 리스트 불러오기
  useEffect(() => {
    const fetchCctvs = async () => {
      try {
        const response = await axios.get('http://localhost:8080/api/cctvs');
        const data = response.data.map(item => ({
          ...item,
          streamName: item.streamName || item.location || "(이름 없음)"
        }));
        setCctvList(data);
      } catch (error) {
        console.error("CCTV 데이터를 불러오는데 실패했습니다.", error);
      }
    };
    fetchCctvs();
  }, []);

  // 신규 신고 알림 폴링 + 알림 상태 관리
  useEffect(() => {
    let interval;

    const fetchAndCheckReports = async () => {
      try {
        const res = await axios.get('http://localhost:8080/api/human-reports');
        console.log('신규 신고 원본 데이터:', res.data);

        if (Array.isArray(res.data)) {
          const unread = res.data.filter(item => !item.read);
          if (unread.length > 0) {
            const latest = unread[0];
            setAlerts(prev => {
              if (prev.some(a => a.id === latest.id)) {
                console.log(`이미 알림이 있는 신고 ID: ${latest.id}`);
                return prev;
              }
              console.log(`새로운 알림 추가 - 신고 ID: ${latest.id}`);
              return [...prev, { id: latest.id, message: `${latest.title || '신고'}가 접수되었습니다!` }];
            });
          } else {
            console.log('미열람 신규 신고 없음');
          }
        }
      } catch (e) {
        console.error('신규 신고 조회 오류:', e);
      }
    };

    // 페이지 진입시 즉시 호출
    fetchAndCheckReports();

    // 이후 10초 간격으로 실행
    interval = setInterval(fetchAndCheckReports, 10000);

    return () => clearInterval(interval);
  }, []);

  // 알림 클릭 시 읽음 처리 API 호출 후 알림 제거
  const dismissAlert = async (id) => {
    try {
      await axios.patch(`http://localhost:8080/api/human-reports/${id}/read`, {});
    } catch (error) {
      console.error('읽음 처리 실패:', error);
    } finally {
      setAlerts(prev => prev.filter(a => a.id !== id));
    }
  };

  // HLS CCTV 플레이어 연결 + cleanup
  useEffect(() => {
    let hls;
    if (selectedCctv?.streamUrl) {
      const video = document.getElementById("cctv-player");
      if (video) {
        if (Hls.isSupported()) {
          hls = new Hls();
          hls.loadSource(selectedCctv.streamUrl);
          hls.attachMedia(video);
        } else if (video.canPlayType("application/vnd.apple.mpegurl")) {
          video.src = selectedCctv.streamUrl;
        }
      }
    }
    return () => {
      if (hls) hls.destroy();
    };
  }, [selectedCctv]);

  return (
    <div
      style={{
        padding: "40px",
        background: "#f0f2f6",
        height: "100vh",
        boxSizing: "border-box",
      }}
    >
      {/* 알림 박스 */}
      <AlertBox alerts={alerts} onDismiss={dismissAlert} />

      {/* 탭 버튼 */}
      <div className="main-tabs">
        <button
          className={tab === "map" ? "active" : ""}
          onClick={() => setTab("map")}
        >
          지도현황
        </button>
        <button
          className={tab === "route" ? "active" : ""}
          onClick={() => setTab("route")}
        >
          단속경로
        </button>
      </div>

      {/* 메인 레이아웃 */}
      <div
        className="main-layout"
        style={{
          height: "calc(100% - 60px)",
          display: "flex",
        }}
      >
        <div
          style={{
            flex: tab === "map" ? "1 1 70%" : "1 1 100%",
            position: "relative",
          }}
        >
          {tab === "map" ? (
            <>
              {/* CCTV 선택 */}
              <CctvSelector
                cctvList={cctvList}
                selectedCctv={selectedCctv}
                onSelect={setSelectedCctv}
              />

              {/* 지도 */}
              <MapPage
                selectedLocation={
                  selectedCctv
                    ? {
                        label: selectedCctv.streamName,
                        lat: selectedCctv.latitude, // 위도
                        lng: selectedCctv.longitude, // 경도
                      }
                    : null
                }
                onLocationChange={(loc) => {
                  const c = cctvList.find(
                    (cctv) =>
                      cctv.streamName === loc?.label ||
                      (cctv.latitude === loc?.lat &&
                        cctv.longitude === loc?.lng)
                  );
                  if (c) setSelectedCctv(c);
                }}
                cctvData={cctvList}
                onCctvSelect={setSelectedCctv}
              />
            </>
          ) : (
            <RoutePanel />
          )}
        </div>

        {/* 사이드 InfoPanel */}
        {tab === "map" && (
          <div
            className="side-panel"
            style={{ flex: "0 0 25%", overflowY: "auto" }}
          >
            <InfoPanel
              selectedLocation={selectedCctv}
              onLocationChange={setSelectedCctv}
            />
          </div>
        )}
      </div>
    </div>
  );
}

export default MainPage;