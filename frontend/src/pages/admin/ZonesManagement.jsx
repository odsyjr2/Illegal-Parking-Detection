import React, { useEffect, useState, useRef } from "react";

function ZonesManagement() {
  const [zones, setZones] = useState([]);
  const [newZoneName, setNewZoneName] = useState("");
  const [newAllowedStartTime, setNewAllowedStartTime] = useState("");
  const [newAllowedEndTime, setNewAllowedEndTime] = useState("");
  const [newSection, setNewSection] = useState({
    start: "",
    end: "",
    startTime: "",
    endTime: "",
    allowed: true,
  });
  const [selectedZoneId, setSelectedZoneId] = useState(null);
  const [selectedSectionIds, setSelectedSectionIds] = useState({});
  const [editingSectionId, setEditingSectionId] = useState(null);
  const [editingSectionInput, setEditingSectionInput] = useState({});
  const inputRefs = useRef({});
  const API_BASE = "http://localhost:8080/api";

  const ensureZoneRefs = (zoneId) => {
    if (!inputRefs.current[zoneId]) {
      inputRefs.current[zoneId] = {
        start: React.createRef(),
        end: React.createRef(),
        startTime: React.createRef(),
        endTime: React.createRef(),
      };
    }
    return inputRefs.current[zoneId];
  };

  const mapServerToFront = (data) =>
    data.map((z) => ({
      id: z.id,
      name: z.zoneName,
      allowedTime: z.allowedTime,
      sections: Array.isArray(z.sections)
        ? z.sections.map((s) => ({
            id: s.id,
            start: s.origin,
            end: s.destination,
            time: s.time,
            allowed: s.parkingAllowed,
          }))
        : [],
    }));

  const getAuthHeaders = () => {
    const token = localStorage.getItem("accessToken");
    return {
      "Content-Type": "application/json",
      Authorization: `Bearer ${token}`,
    };
  };

  /** 구역 목록 로드 */
  const loadZones = async () => {
    try {
      const res = await fetch(`${API_BASE}/zones`, {
        headers: getAuthHeaders(),
      });
      if (!res.ok) throw new Error("구역 목록 로드 실패");
      const data = await res.json();
      setZones(mapServerToFront(data));
    } catch (err) {
      console.error(err);
      alert(err.message || "구역 목록 로드 실패");
    }
  };

  useEffect(() => {
    loadZones();
  }, []);

  /** 구역 추가 */
  const handleAddZone = async () => {
    if (!newZoneName.trim() || !newAllowedStartTime || !newAllowedEndTime) {
      alert("구역명과 허용 시간대를 입력하세요.");
      return;
    }
    const allowedTime = `${newAllowedStartTime}~${newAllowedEndTime}`;
    const body = {
      zoneName: newZoneName.trim(),
      allowedTime,
      sections: [],
    };

    try {
      const res = await fetch(`${API_BASE}/zones`, {
        method: "POST",
        headers: getAuthHeaders(),
        body: JSON.stringify(body),
      });
      if (!res.ok) throw new Error("구역 등록 실패");
      await loadZones();
      setNewZoneName("");
      setNewAllowedStartTime("");
      setNewAllowedEndTime("");
    } catch (err) {
      console.error(err);
      alert(err.message || "구역 등록 실패");
    }
  };

  /** 구역 삭제 */
  const handleDeleteZone = async (zoneId) => {
    if (!window.confirm("정말 해당 구역을 삭제하시겠습니까?")) return;
    try {
      const res = await fetch(`${API_BASE}/zones/${zoneId}`, {
        method: "DELETE",
        headers: getAuthHeaders(),
      });
      if (!res.ok) throw new Error("구역 삭제 실패");
      await loadZones();
    } catch (err) {
      console.error(err);
      alert(err.message || "구역 삭제 실패");
    }
  };

  /** 구간 추가 (새 섹션만 전송) */
  const handleAddSection = async (zone) => {
    if (!newSection.start || !newSection.end || !newSection.startTime || !newSection.endTime) {
      alert("구간 정보를 모두 입력하세요.");
      return;
    }

    const newSectionPayload = {
      origin: newSection.start,
      destination: newSection.end,
      time: `${newSection.startTime}~${newSection.endTime}`,
      parkingAllowed: newSection.allowed,
    };

    const body = {
      zoneName: zone.name,
      allowedTime: zone.allowedTime,
      sections: [newSectionPayload],
    };

    try {
      const res = await fetch(`${API_BASE}/zones`, {
        method: "POST",
        headers: getAuthHeaders(),
        body: JSON.stringify(body),
      });
      if (!res.ok) {
        if (res.status === 401) {
          console.error("❌ 401 Unauthorized - 토큰 문제");
        }
        throw new Error("구간 추가 실패");
      }
      await loadZones();
      setNewSection({ start: "", end: "", startTime: "", endTime: "", allowed: true });
      setSelectedZoneId(null);
    } catch (err) {
      console.error(err);
      alert(err.message || "구간 추가 실패");
    }
  };

  /** 구간 수정 */

  const handleEditSection = (zoneId, section) => {
    const [startT, endT] = section.time.split("~");
    setEditingSectionId(section.id);
    setEditingSectionInput({
      zoneId,
      start: section.start,
      end: section.end,
      startTime: startT || "",
      endTime: endT || "",
      allowed: section.allowed ? "true" : "false",
    });
  };

  const handleSaveEdit = async () => {
    const { zoneId, start, end, startTime, endTime, allowed } = editingSectionInput;
    if (!start || !end || !startTime || !endTime) {
      alert("모든 구간 정보를 입력하세요.");
      return;
    }

    const body = {
      origin: start,
      destination: end,
      time: `${startTime}~${endTime}`,
      parkingAllowed: allowed === "true",
    };

    try {
      const res = await fetch(`${API_BASE}/zones/${zoneId}/sections/${editingSectionId}`, {
        method: "PATCH",
        headers: getAuthHeaders(),
        body: JSON.stringify(body),
      });
      if (!res.ok) throw new Error("구간 수정 실패");
      await loadZones();
      setEditingSectionId(null);
      setEditingSectionInput({});
    } catch (err) {
      console.error(err);
      alert(err.message);
    }
  };

  /** 구간 삭제 */
  const handleDeleteSections = async (zoneId) => {
    const idsToDelete = selectedSectionIds[zoneId] || [];

    if (!idsToDelete.length) return;
    if (!window.confirm("선택한 구간을 삭제하시겠습니까?")) return;

    try {
      for (const sectionId of idsToDelete) {
        const res = await fetch(`${API_BASE}/zones/${zoneId}/sections/${sectionId}`, {
          method: "DELETE",
          headers: getAuthHeaders(),
        });
        if (!res.ok) throw new Error(`구간 ${sectionId} 삭제 실패`);
      }
      await loadZones();
      setSelectedSectionIds((prev) => ({ ...prev, [zoneId]: [] }));
    } catch (err) {
      console.error(err);
      alert(err.message || "구간 삭제 실패");
    }
  };

  /** 체크박스 선택 상태 업데이트 */
  const handleSectionCheckbox = (zoneId, sectionId, checked) => {
    setSelectedSectionIds((prev) => {
      const current = prev[zoneId] || [];
      const next = checked
        ? [...current, sectionId]
        : current.filter((id) => id !== sectionId);
      return { ...prev, [zoneId]: next };
    });
  };

  // 도로명 주소 검색 팝업
  const openAddressPopup = (zoneId, type) => {
    setSelectedZoneId(zoneId); // 어느 구역에서 입력하는지 저장

    new window.daum.Postcode({
      oncomplete: function (data) {
        const address = data.roadAddress || data.jibunAddress;
        setNewSection((ns) => ({
          ...ns,
          [type]: address, // type은 'start' 또는 'end'
        }));

        // 입력 후 다음 칸으로 포커스 이동
        const refsForZone = inputRefs.current[zoneId];
        if (!refsForZone) return;
        setTimeout(() => {
          if (type === "start" && refsForZone.end.current) refsForZone.end.current.focus();
          else if (type === "end" && refsForZone.startTime.current) refsForZone.startTime.current.focus();
        }, 0);
      },
    }).open();
  };
  const mutedBtn = (color) => ({
    background: color,
    color: "#fff",
    border: "none",
    borderRadius: 6,
    padding: "6px 13px",
    fontWeight: 600,
    fontSize: 15,
    cursor: "pointer",
    userSelect: "none",
  });

  const thStyle = { padding: "8px 10px", fontWeight: 600, fontSize: 15, borderBottom: "1px solid #e0eaf6", background: "#f2f6fb" };
  const tdStyle = { padding: "8px 10px", fontSize: 15, borderBottom: "1px solid #e0eaf6", textAlign: "center" };

  return (
    <div style={{ background: "#fff", padding: 20, borderRadius: 10 }}>
      <h2>🕒 구역별 주정차 허용시간 및 구간정보 관리</h2>

      {/* 구역 추가 */}
      <section style={{ margin: "24px 0 32px 0", display: "flex", gap: 10, alignItems: "center" }}>
        <input placeholder="구역명" value={newZoneName} onChange={(e) => setNewZoneName(e.target.value)} style={{ padding: 7, border: "1px solid #364599ff", borderRadius: 6, background: "#f7fafd", width: 120 }} />
        <input type="time" value={newAllowedStartTime} onChange={(e) => setNewAllowedStartTime(e.target.value)} style={{ padding: 6, width: 110, border: "1px solid #bfd6f2", borderRadius: 6 }} />
        <span>~</span>
        <input type="time" value={newAllowedEndTime} onChange={(e) => setNewAllowedEndTime(e.target.value)} style={{ padding: 6, width: 110, border: "1px solid #bfd6f2", borderRadius: 6 }} />
        <button onClick={handleAddZone} style={mutedBtn("#364599ff")}>구역 추가</button>
      </section>

      {zones.map((zone) => {
        const refs = ensureZoneRefs(zone.id);
        return (
          <div key={zone.id} style={{ marginBottom: 36, border: "1px solid #e0eaf6", borderRadius: 8, padding: 14 }}>
            <div style={{ display: "flex", alignItems: "center", gap: 20, marginBottom: 12 }}>
              <span style={{ fontWeight: 700, fontSize: 18 }}>{zone.name}</span>
              <span style={{ color: "#555" }}>{zone.allowedTime}</span>
              <button onClick={() => handleDeleteZone(zone.id)} style={{ marginLeft: "auto", ...mutedBtn("#dd6565ff") }}>구역 삭제</button>
            </div>

            <table style={{ width: "100%", borderCollapse: "collapse" }}>
              <thead>
                <tr>
                  <th style={thStyle}></th>
                  <th style={thStyle}>출발지</th>
                  <th style={thStyle}>도착지</th>
                  <th style={thStyle}>허용 시간대</th>
                  <th style={thStyle}>주정차 허용</th>
                  <th style={thStyle}></th>
                </tr>
              </thead>
              <tbody>
                {zone.sections.length === 0 ? (
                  <tr>
                    <td colSpan={6} style={{ textAlign: "center", color: "#999" }}>등록된 구간이 없습니다.</td>
                  </tr>
                ) : (
                  zone.sections.map((section) => (
                    <tr key={section.id}>
                      <td style={tdStyle}>
                        <input
                          type="checkbox"
                          checked={(selectedSectionIds[zone.id] || []).includes(section.id)}
                          onChange={(e) => handleSectionCheckbox(zone.id, section.id, e.target.checked)}
                        />
                      </td>
                      {editingSectionId === section.id ? (
                      <>
                        <td style={tdStyle}>
                          <input
                            value={editingSectionInput.start}
                            onChange={(e) => setEditingSectionInput(prev => ({ ...prev, start: e.target.value }))}
                          />
                        </td>
                        <td style={tdStyle}>
                          <input
                            value={editingSectionInput.end}
                            onChange={(e) => setEditingSectionInput(prev => ({ ...prev, end: e.target.value }))}
                          />
                        </td>
                        <td style={tdStyle}>
                          <input
                            type="time"
                            value={editingSectionInput.startTime}
                            onChange={(e) => setEditingSectionInput(prev => ({ ...prev, startTime: e.target.value }))}
                          />
                          ~
                          <input
                            type="time"
                            value={editingSectionInput.endTime}
                            onChange={(e) => setEditingSectionInput(prev => ({ ...prev, endTime: e.target.value }))}
                          />
                        </td>
                        <td style={tdStyle}>
                          <select
                            value={editingSectionInput.allowed}
                            onChange={(e) => setEditingSectionInput(prev => ({ ...prev, allowed: e.target.value }))}
                          >
                            <option value="true">허용</option>
                            <option value="false">불가</option>
                          </select>
                        </td>
                        <td style={tdStyle}>
                          <button onClick={handleSaveEdit} style={mutedBtn("#364599ff")}>저장</button>
                          <button onClick={() => setEditingSectionId(null)} style={mutedBtn("#999")}>취소</button>
                        </td>
                      </>
                    ) : (
                      <>
                        <td style={tdStyle}>{section.start}</td>
                        <td style={tdStyle}>{section.end}</td>
                        <td style={tdStyle}>{section.time}</td>
                        <td style={tdStyle}>{section.allowed ? "허용" : "불가"}</td>
                        <td style={tdStyle}>
                          <button onClick={() => handleEditSection(zone.id, section)} style={mutedBtn("#364599ff")}>수정</button>
                        </td>
                      </>
                    )}
                  </tr>
                  ))
                )}
              </tbody>
            </table>

            {/* 구간 추가 입력 */}
            <div style={{ display: "flex", gap: 8, marginTop: 10 }}>
            {/* 출발지 */}
            <input
              ref={refs.start}
              placeholder="출발 도로명 주소"
              value={selectedZoneId === zone.id ? newSection.start : ""}
              onChange={(e) => {
                setSelectedZoneId(zone.id);
                setNewSection((ns) => ({ ...ns, start: e.target.value }));
              }}
            />
            <button
              type="button"
              onClick={() => openAddressPopup(zone.id, "start")}
              style={mutedBtn("#B3BCF2")}
            >
              주소검색
            </button>

            {/* 도착지 */}
            <input
              ref={refs.end}
              placeholder="도착 도로명 주소"
              value={selectedZoneId === zone.id ? newSection.end : ""}
              onChange={(e) => {
                setSelectedZoneId(zone.id);
                setNewSection((ns) => ({ ...ns, end: e.target.value }));
              }}
            />
            <button
              type="button"
              onClick={() => openAddressPopup(zone.id, "end")}
              style={mutedBtn("#B3BCF2")}
            >
              주소검색
            </button>

            {/* 시간 */}
            <input
              type="time"
              ref={refs.startTime}
              value={selectedZoneId === zone.id ? newSection.startTime : ""}
              onChange={(e) => {
                setSelectedZoneId(zone.id);
                setNewSection((ns) => ({ ...ns, startTime: e.target.value }));
              }}
            />
            <input
              type="time"
              ref={refs.endTime}
              value={selectedZoneId === zone.id ? newSection.endTime : ""}
              onChange={(e) => {
                setSelectedZoneId(zone.id);
                setNewSection((ns) => ({ ...ns, endTime: e.target.value }));
              }}
            />

            {/* 허용 여부 */}
            <select
              value={selectedZoneId === zone.id ? (newSection.allowed ? "true" : "false") : "true"}
              onChange={(e) => {
                setSelectedZoneId(zone.id);
                setNewSection((ns) => ({ ...ns, allowed: e.target.value === "true" }));
              }}
            >
              <option value="true">허용</option>
              <option value="false">불가</option>
            </select>

            {/* 추가 버튼 */}
            <button
              onClick={() => handleAddSection(zone)}
              style={mutedBtn("#364599ff")}
            >
              구간 추가
            </button>
          </div>

            {/* 선택 구간 삭제 버튼 */}
            <div style={{ textAlign: "right", marginTop: 8 }}>
              <button
                type="button"
                onClick={() => handleDeleteSections(zone.id)}
                disabled={!(selectedSectionIds[zone.id] || []).length}
                style={{
                  ...mutedBtn("#dd6565ff"),
                  opacity: !(selectedSectionIds[zone.id] || []).length ? 0.5 : 1,
                  cursor: !(selectedSectionIds[zone.id] || []).length ? "not-allowed" : "pointer"
                }}
              >
                선택구간 삭제
              </button>
            </div>
          </div>
        );
      })}
    </div>
  );
}

export default ZonesManagement;