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
        value={selectedCctv?.cctvname || ""}
        onChange={(e) => {
          const selected = cctvList.find(
            (c) => c.cctvname === e.target.value
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
          <option key={idx} value={c.cctvname}>
            {c.cctvname || "CCTV 미선택"}
          </option>
        ))}
      </select>

      {selectedCctv?.cctvurl && (
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

  // CCTV 리스트 (임시 하드코딩)
  const cctvList = [
    {
      roadsectionid: "",
      coordx: 126.8102,
      coordy: 35.0411,
      cctvresolution: "",
      filecreatetime: "",
      cctvtype: 1,
      cctvformat: "HLS",
      cctvname: "[국도1호선]나주산포",
      cctvurl: "http://",
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
      cctvurl: "http://",
    },
  ];

  // HLS CCTV 플레이어 연결 + cleanup 추가
  useEffect(() => {
    let hls;
    if (selectedCctv?.cctvurl) {
      const video = document.getElementById("cctv-player");
      if (video) {
        if (Hls.isSupported()) {
          hls = new Hls();
          hls.loadSource(selectedCctv.cctvurl);
          hls.attachMedia(video);
        } else if (video.canPlayType("application/vnd.apple.mpegurl")) {
          video.src = selectedCctv.cctvurl;
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
                        label: selectedCctv.cctvname,
                        lat: selectedCctv.coordy,
                        lng: selectedCctv.coordx,
                      }
                    : null
                }
                onLocationChange={(loc) => {
                  const c = cctvList.find(
                    (cctv) =>
                      cctv.cctvname === loc?.label ||
                      (cctv.coordx === loc?.lng && cctv.coordy === loc?.lat)
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