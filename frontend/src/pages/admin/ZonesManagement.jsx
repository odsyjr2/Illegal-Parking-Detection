import React, { useState, useEffect } from 'react';

const KAKAO_API_KEY = '9fabbd28c079827af4ab0436f07293ec';

// 도로명주소 검색 컴포넌트
function AddressSearch({ onSelect, placeholder = "도로명주소 검색", style = {}, inputStyle = {} }) {
  const [query, setQuery] = useState('');
  const [results, setResults] = useState([]);
  
  useEffect(() => {
    if (query.length < 2) {
      setResults([]);
      return;
    }
    const controller = new AbortController();
    fetch(
      `https://dapi.kakao.com/v2/local/search/address.json?query=${encodeURIComponent(query)}`,
      {
        headers: { Authorization: `KakaoAK ${KAKAO_API_KEY}` },
        signal: controller.signal,
      }
    )
      .then(res => res.json())
      .then(data => {
        if (data.documents) setResults(data.documents);
      })
      .catch(err => {
        if (err.name !== 'AbortError') console.error(err);
      });

    return () => controller.abort();
  }, [query]);

  return (
    <div style={{ position: 'relative', ...style }}>
      <input
        placeholder={placeholder}
        value={query}
        onChange={e => setQuery(e.target.value)}
        style={{ padding: 7, width: 250, borderRadius: 6, border: '1px solid #ccc', ...inputStyle }}
      />
      {results.length > 0 && (
        <ul
          style={{
            position: 'absolute',
            top: '100%',
            left: 0,
            right: 0,
            maxHeight: 150,
            overflowY: 'auto',
            background: 'white',
            border: '1px solid #ddd',
            margin: 0,
            padding: 0,
            listStyle: 'none',
            zIndex: 10,
          }}
        >
          {results.map(item => (
            <li
              key={item.id}
              style={{ padding: 8, cursor: 'pointer' }}
              onClick={() => {
                onSelect(item.address.address_name);
                setQuery('');
                setResults([]);
              }}
            >
              {item.address.address_name}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

function ZonesManagement() {
  // [1] 상태 정의
  const [zones, setZones] = useState([
    {
      id: 1,
      name: '관악구',
      allowedTime: '08:00~20:00',
      sections: [
        { id: 100, start: '봉천동', end: '신림동', time: '09:00~12:00', allowed: true },
        { id: 101, start: '청룡동', end: '대학동', time: '15:00~18:00', allowed: false },
      ],
    },
    {
      id: 2,
      name: '강남구',
      allowedTime: '09:00 ~ 18:00',
      sections: [{ id: 200, start: '역삼동', end: '삼성동', time: '10:00~23:00', allowed: true }],
    },
  ]);
  const [newZoneName, setNewZoneName] = useState('');
  const [newAllowedTime, setNewAllowedTime] = useState('');

  const [newSection, setNewSection] = useState({ start: '', end: '', time: '', allowed: true });
  const [selectedZoneId, setSelectedZoneId] = useState(null);
  const [selectedSectionIds, setSelectedSectionIds] = useState({});
  const [editingSectionId, setEditingSectionId] = useState(null);
  const [editingSectionInput, setEditingSectionInput] = useState({});

  // 구역 추가
  const handleAddZone = () => {
    if (!newZoneName.trim() || !newAllowedTime.trim()) {
      alert('구역명과 허용 시간대를 입력하세요.');
      return;
    }
    const allowedTime = `${newAllowedStartTime}~${newAllowedEndTime}`
    setZones([
      ...zones,
      {
        id: Date.now(),
        name: newZoneName.trim(),
        allowedTime,
        sections: [],
      },
    ]);
    setNewZoneName('');
    setNewAllowedTime('');
  };

  // 구간 체크박스 선택 관리
  const handleSectionCheckbox = (zoneId, sectionId, checked) => {
    setSelectedSectionIds(prev => {
      const current = prev[zoneId] || [];
      const next = checked ? Array.from(new Set([...current, sectionId])) : current.filter(id => id !== sectionId);
      return { ...prev, [zoneId]: next };
    });
  };

  // 선택 구간 삭제
  const handleDeleteSections = zoneId => {
    const idsToDelete = selectedSectionIds[zoneId] || [];
    if (idsToDelete.length === 0) return;
    if (!window.confirm('선택한 구간을 삭제하시겠습니까?')) return;
    setZones(
      zones.map(zone =>
        zone.id === zoneId ? { ...zone, sections: zone.sections.filter(s => !idsToDelete.includes(s.id)) } : zone
      )
    );
    setSelectedSectionIds(prev => ({ ...prev, [zoneId]: [] }));
  };

  // 구간 수정 시작
  const handleEditSection = (zoneId, section) => {
    setEditingSectionId(section.id);
    setEditingSectionInput({
      start: section.start,
      end: section.end,
      startTime: startT || '',
      endTime: endT || '',
      allowed: section.allowed,
      zoneId,
    });
  };

  // 수정 입력 변경 감지
  const handleEditInputChange = (field, value) => {
    setEditingSectionInput(prev => ({ ...prev, [field]: value }));
  };

  // 수정 저장
  const handleSaveEdit = () => {
    const { zoneId, start, end, time, allowed } = editingSectionInput;
    setZones(
      zones.map(zone =>
        zone.id === zoneId
          ? {
              ...zone,
              sections: zone.sections.map(s =>
                s.id === editingSectionId ? { ...s, start, end, time, allowed: allowed === 'false' ? false : !!allowed } : s
              ),
            }
          : zone
      )
    );
    setEditingSectionId(null);
    setEditingSectionInput({});
  };

  // 수정 취소
  const handleCancelEdit = () => {
    setEditingSectionId(null);
    setEditingSectionInput({});
  };

  // 구간 추가
  const handleAddSection = zoneId => {
    if (!newSection.start || !newSection.end || !newSection.time) {
      alert('구간 정보를 모두 입력하세요.');
      return;
    }
    setZones(
      zones.map(z =>
        z.id === zoneId
          ? {
              ...z,
              sections: [
                ...z.sections,
                {
                  ...newSection,
                  id: Date.now(),
                  allowed: newSection.allowed === 'false' ? false : !!newSection.allowed,
                },
              ],
            }
          : z
      )
    );
    setNewSection({ start: '', end: '', time: '', allowed: true });
    setSelectedZoneId(null);
  };

  return (
    <div style={{ background: '#fff', padding: 20, borderRadius: 10 }}>
      <h2>🕒 구역별 주정차 허용시간 및 구간정보 관리</h2>

      {/* 구역 추가 폼 + 도로명주소 검색 붙임 */}
      <section style={{ margin: '24px 0 32px 0', display: 'flex', gap: 10, alignItems: 'center', flexWrap: 'wrap' }}>
        <input
          placeholder="구역명"
          value={newZoneName}
          onChange={e => setNewZoneName(e.target.value)}
          style={{ padding: 7, border: '1px solid #364599ff', borderRadius: 6, background: '#f7fafd', width: 160 }}
        />

        {/* 허용시간 시작 */}
        <input
          type="time"
          value={newAllowedStartTime}
          onChange={e => setNewAllowedStartTime(e.target.value)}
          style={{
            padding: 6,
            width: 110,
            border: '1px solid #bfd6f2',
            borderRadius: 6,
            background: '#f7fafd',
          }}
        />
        <span style={{ alignSelf: 'center' }}>~</span>
        {/* 허용시간 종료 */}
        <input
          placeholder="허용시간 (예: 08:00 ~ 20:00)"
          value={newAllowedTime}
          onChange={e => setNewAllowedTime(e.target.value)}
          style={{ padding: 7, border: '1px solid #364599ff', borderRadius: 6, background: '#f7fafd', width: 180 }}
        />
        <button onClick={handleAddZone} style={mutedBtn('#364599ff')}>
          구역 추가
        </button>

        {/* 도로명주소 검색 - 구역명 대신 필요할 경우 사용하세요 */}
        <AddressSearch
          placeholder=" 검색"
          onSelect={address => setNewZoneName(address)}
          style={{ flexGrow: 1, maxWidth: 400, marginLeft: 350 }}
          inputStyle={{ width: '80%' }}
        />
      </section>

      {/* 기존 구역 목록 및 구간 테이블 */}
      <section>
        {zones.length === 0 ? (
          <p style={{ color: '#777' }}>등록된 구역이 없습니다.</p>
        ) : (
          zones.map(zone => (
            <div
              key={zone.id}
              style={{ marginBottom: 36, border: '1px solid #e0eaf6', borderRadius: 8, padding: 14 }}
            >
              <div style={{ display: 'flex', alignItems: 'center', gap: 20, marginBottom: 12, flexWrap: 'wrap' }}>
                <span style={{ fontWeight: 700, fontSize: 18 }}>{zone.name}</span>
                <span style={{ color: '#555' }}>{zone.allowedTime}</span>
                <button
                  onClick={() => {
                    if (window.confirm('정말 해당 구역을 삭제하시겠습니까?')) {
                      setZones(zones.filter(z => z.id !== zone.id));
                    }
                  }}
                  style={{ marginLeft: 'auto', ...mutedBtn('#dd6565ff'), flexShrink: 0 }}
                >
                  구역 삭제
                </button>
              </div>

              {/* 구간 테이블 */}
              <table style={{ width: '100%', borderCollapse: 'collapse' }}>
                <thead>
                  <tr style={{ background: '#f2f6fb', borderBottom: '1px solid #e0eaf6' }}>
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
                      <td colSpan={6} style={{ color: '#999', padding: 12, textAlign: 'center' }}>
                        등록된 구간이 없습니다.
                      </td>
                    </tr>
                  ) : (
                    zone.sections.map(section =>
                      editingSectionId === section.id ? (
                        <tr key={section.id} style={{ borderBottom: '1px solid #e0eaf6', background: '#f6faff' }}>
                          <td style={tdStyle}>
                            <input type="checkbox" disabled />
                          </td>
                          <td style={tdStyle}>
                            <AddressSearch
                              placeholder="출발지 주소 검색"
                              onSelect={address => handleEditInputChange('start', address)}
                              inputStyle={{ width: 150, padding: 4 }}
                            />
                          </td>
                          <td style={tdStyle}>
                            <AddressSearch
                              placeholder="도착지 주소 검색"
                              onSelect={address => handleEditInputChange('end', address)}
                              inputStyle={{ width: 150, padding: 4 }}
                            />
                          </td>
                          <td style={tdStyle}>
                            <input
                              value={editingSectionInput.time}
                              onChange={e => handleEditInputChange('time', e.target.value)}
                              style={{ width: 100 }}
                            />
                          </td>
                          <td style={tdStyle}>
                            <select
                              value={editingSectionInput.allowed ? 'true' : 'false'}
                              onChange={e => handleEditInputChange('allowed', e.target.value)}
                              style={{ width: 90 }}
                            >
                              <option value="true">허용</option>
                              <option value="false">불가</option>
                            </select>
                          </td>
                          <td style={tdStyle}>
                            <button onClick={handleSaveEdit} style={mutedBtn('#364599ff')}>
                              저장
                            </button>
                            <button onClick={handleCancelEdit} style={mutedBtn('#bdbdbd')}>
                              취소
                            </button>
                          </td>
                        </tr>
                      ) : (
                        <tr key={section.id} style={{ borderBottom: '1px solid #e0eaf6' }}>
                          <td style={tdStyle}>
                            <input
                              type="checkbox"
                              checked={(selectedSectionIds[zone.id] || []).includes(section.id)}
                              onChange={e => handleSectionCheckbox(zone.id, section.id, e.target.checked)}
                            />
                          </td>
                          <td style={tdStyle}>{section.start}</td>
                          <td style={tdStyle}>{section.end}</td>
                          <td style={tdStyle}>{section.time}</td>
                          <td style={tdStyle}>
                            {section.allowed ? '허용' : <span style={{ color: '#e06767' }}>불가</span>}
                          </td>
                          <td style={tdStyle}>
                            <button onClick={() => handleEditSection(zone.id, section)} style={mutedBtn('#364599ff')}>
                              수정
                            </button>
                          </td>
                        </tr>
                      )
                    )
                  )}
                </tbody>
              </table>

              <div
                style={{
                  display: 'flex',
                  justifyContent: 'space-between',
                  alignItems: 'center',
                  marginTop: 10,
                  flexWrap: 'wrap',
                  gap: 8,
                }}
              >
                <div>
                  <button
                    type="button"
                    onClick={() => handleDeleteSections(zone.id)}
                    disabled={!(selectedSectionIds[zone.id] || []).length}
                    style={{
                      ...mutedBtn('#dd6565ff'),
                      opacity: !(selectedSectionIds[zone.id] || []).length ? 0.5 : 1,
                      cursor: !(selectedSectionIds[zone.id] || []).length ? 'not-allowed' : 'pointer',
                    }}
                  >
                    선택구간 삭제
                  </button>
                </div>

                {/* 구간 추가 폼 */}
                <div style={{ display: 'flex', gap: 20, flexWrap: 'wrap', alignItems: 'center' }}>
                  {/* 출발지 검색 */}
                  <AddressSearch
                    placeholder="출발지 주소 검색"
                    onSelect={address => {
                      setSelectedZoneId(zone.id);
                      setNewSection(ns => ({ ...ns, start: address }));
                    }}
                    style={{ maxWidth: 150 }}
                    inputStyle={{ padding: 6, width: 150, border: '1px solid #bfd6f2', borderRadius: 6, background: '#f7fafd' }}
                  />
                  {/* 도착지 검색 */}
                  <AddressSearch
                    placeholder="도착지 주소 검색"
                    onSelect={address => {
                      setSelectedZoneId(zone.id);
                      setNewSection(ns => ({ ...ns, end: address }));
                    }}
                    style={{ maxWidth: 150 }}
                    inputStyle={{ padding: 6, width: 150, border: '1px solid #bfd6f2', borderRadius: 6, background: '#f7fafd' }}
                  />
                  <button
                    type="button"
                    onClick={() => openAddressPopup(zone.id, 'end')}
                    style={{ ...mutedBtn('#B3BCF2'), padding: '6px 11px' }}
                  >
                    주소검색
                  </button>

                  {/* 허용시간 시작 */}
                  <input
                    type="time"
                    ref={refs.startTime}
                    value={selectedZoneId === zone.id ? newSection.startTime : ''}
                    onChange={e => {
                      setSelectedZoneId(zone.id)
                      setNewSection(ns => ({ ...ns, startTime: e.target.value }))
                    }}
                    style={{
                      padding: 6,
                      width: 110,
                      border: '1px solid #bfd6f2',
                      borderRadius: 6,
                      background: '#f7fafd',
                    }}
                  />
                  <span style={{ alignSelf: 'center' }}>~</span>
                  {/* 허용시간 종료 */}
                  <input
                    type="time"
                    ref={refs.endTime}
                    value={selectedZoneId === zone.id ? newSection.endTime : ''}
                    onChange={e => {
                      setSelectedZoneId(zone.id);
                      setNewSection(ns => ({ ...ns, time: e.target.value }));
                    }}
                    style={{ padding: 6, width: 150, border: '1px solid #bfd6f2', borderRadius: 6, background: '#f7fafd' }}
                  />

                  <select
                    value={selectedZoneId === zone.id ? (newSection.allowed ? 'true' : 'false') : 'true'}
                    onChange={e => {
                      setSelectedZoneId(zone.id);
                      setNewSection(ns => ({ ...ns, allowed: e.target.value === 'true' }));
                    }}
                    style={{ padding: 6, width: 100, border: '1px solid #bfd6f2', borderRadius: 6, background: '#f7fafd' }}
                  >
                    <option value="true">허용</option>
                    <option value="false">불가</option>
                  </select>
                  <button onClick={() => handleAddSection(zone.id)} style={mutedBtn('#364599ff')}>
                    구간 추가
                  </button>
                </div>
              </div>
            )
          })
        )}
      </section>
    </div>
  );
}

// 스타일 함수 및 객체
const mutedBtn = color => ({
  background: color,
  color: '#fff',
  border: 'none',
  borderRadius: 6,
  padding: '6px 13px',
  fontWeight: 600,
  fontSize: 15,
  cursor: 'pointer',
  userSelect: 'none',
  boxShadow: 'none',
  transition: 'background 0.18s',
});

const thStyle = {
  padding: '8px 10px',
  fontWeight: 600,
  fontSize: 15,
  borderBottom: '1px solid #e0eaf6',
  background: '#f2f6fb',
};
const tdStyle = {
  padding: '8px 10px',
  fontSize: 15,
  borderBottom: '1px solid #e0eaf6',
  textAlign: 'center',
};

export default ZonesManagement;
