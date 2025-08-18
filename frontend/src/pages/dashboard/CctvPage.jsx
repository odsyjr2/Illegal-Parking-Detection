import { useState, useEffect } from "react";
import Hls from "hls.js";
import { MapContainer, TileLayer, Marker, Popup } from "react-leaflet";
import "leaflet/dist/leaflet.css";

export default function CctvPage() {
  const [selected, setSelected] = useState(null);

  // ✅ API 응답 구조 그대로 하드코딩
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
          cctvurl: "http://cctvsec.ktict.co.kr/4306/QtoPXrKQLl68YLsNjwgu2JcekHo1Ndyf8PwSzb+fKkWA6RByMZZaAlUmda+JIiXeBM0429YhDuCnv2SdoosIGAOSSaD2NcOACpvOo5kQ354="
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
          cctvurl: "http://cctvsec.ktict.co.kr/sample2/"
        }
      ]
    }
  };

  const cctvList = cctvData.response.data;

  // ✅ 선택된 CCTV 영상 재생
  useEffect(() => {
    if (selected?.cctvurl) {
      const video = document.getElementById("cctv-player");
      if (Hls.isSupported()) {
        const hls = new Hls();
        hls.loadSource(selected.cctvurl);
        hls.attachMedia(video);
      } else if (video.canPlayType("application/vnd.apple.mpegurl")) {
        video.src = selected.cctvurl;
      }
    }
  }, [selected]);

  return (
    <div style={{ display: "flex", height: "100vh" }}>
      
      {/* 왼쪽 - 선택 박스 + 영상 */}
      <div style={{ flex: "0 0 320px", padding: 12, background: "#fff" }}>
        <h3>CCTV 목록</h3>
        <select
          style={{ width: "100%", padding: 8 }}
          value={selected?.cctvname || ""}
          onChange={(e) =>
            setSelected(cctvList.find(c => c.cctvname === e.target.value) || null)
          }
        >
          <option value="">--- CCTV 선택 ---</option>
          {cctvList.map(c => (
            <option key={c.cctvname} value={c.cctvname}>
              {c.cctvname}
            </option>
          ))}
        </select>

        {selected?.cctvurl && (
          <video
            id="cctv-player"
            controls
            autoPlay
            muted
            style={{ marginTop: 12, width: "100%" }}
          />
        )}
      </div>

      {/* 오른쪽 - 지도 */}
      <div style={{ flex: 1 }}>
        <MapContainer
          center={selected ? [selected.coordy, selected.coordx] : [35.0411, 126.8102]}
          zoom={12}
          style={{ height: "100%", width: "100%" }}
        >
          <TileLayer
            attribution="&copy; OpenStreetMap contributors"
            url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
          />
          {cctvList.map(cctv => (
            <Marker
              key={cctv.cctvname}
              position={[cctv.coordy, cctv.coordx]}
              eventHandlers={{
                click: () => setSelected(cctv)
              }}
            >
              <Popup>{cctv.cctvname}</Popup>
            </Marker>
          ))}
        </MapContainer>
      </div>
    </div>
  );
}