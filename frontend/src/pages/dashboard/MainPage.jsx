// MainPage.jsx
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

// CCTV 선택 UI
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

  // CCTV 리스트 (임시 하드코딩)
  // const cctvList = [
  //   {
  //     streamId: "cctv_000",
  //     streamName: "가양대교북단(고양)",
  //     streamUrl: "https://openapi.its.go.kr/stream/cctv001",
  //     location: "경기도 고양시 덕양구 가양대교북단",
  //     latitude: 37.6158,
  //     longitude: 126.8441,
  //     streamSource: "korean_its_api",
  //     active: true,
  //     discoveredAt: "2023-12-29T10:33:54.567Z",
  //   },
  //   {
  //     streamId: "cctv_001",
  //     streamName: "[국도1호선]나주산포",
  //     streamUrl: "http://cctvsec.ktict.co.kr/4306/QtoPXrKQLl68YLsNjwgu2JcekHo1Ndyf8PwSzb+fKkWA6RByMZZaAlUmda+JIiXeBM0429YhDuCnv2SdoosIGAOSSaD2NcOACpvOo5kQ354=",
  //     location: "전남 나주시 산포면 등정리 860-17",
  //     latitude: 35.0411,
  //     longitude: 126.8102,
  //     streamSource: "ktict_cctv_api",
  //     active: true,
  //     discoveredAt: "2023-12-29T10:33:54.567Z",
  //   },
  //   {
  //     streamId: "cctv_002",
  //     streamName: "[국도22호선]광주너릿재T",
  //     streamUrl: "http://cctvsec.ktict.co.kr/4316/tmGlyHi1I47WrXEhMPLGQFcJHva4/izTPv12JaH8+byrIjzOe/mRJfDBx/Cph814Y8ry153TMzeVZ5uK3S9kllBSgjbhBYfFfWuw8jbhNZ0=",
  //     location: "광주 동구 선교동 482",
  //     latitude: 35.0811,
  //     longitude: 126.9516,
  //     streamSource: "ktict_cctv_api",
  //     active: true,
  //     discoveredAt: "2023-12-29T10:33:54.567Z",
  //   },
  //   {
  //     streamId: "cctv_003",
  //     streamName: "[국도1호선]나주칠석교차로",
  //     streamUrl: "http://cctvsec.ktict.co.kr/4935/xRj9/fXMHhpbMa+k+94QSQk/f94JSvmmCNBiqzs0Po2ktGvJFL0EACLMrD5Ymq/fYQx3S1jwrJc/CqbEOrwnglgSmrMDc6wz4LBbyD8Ltvk=",
  //     location: "전남 나주시 남평읍 평산리 8-1",
  //     latitude: 35.065308,
  //     longitude: 126.842247,
  //     streamSource: "ktict_cctv_api",
  //     active: true,
  //     discoveredAt: "2023-12-29T10:33:54.567Z",
  //   },
  // ];

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


  // HLS CCTV 플레이어 연결 + cleanup 추가
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
      <AlertBox
        alerts={alerts}
        onDismiss={(id) => {
          setAlerts((prev) => prev.filter((a) => a.id !== id));
        }}
      />

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