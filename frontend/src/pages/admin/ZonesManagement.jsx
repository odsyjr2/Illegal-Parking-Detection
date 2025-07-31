import React, { useState, useRef } from 'react'

// 중요! 프로젝트 public/index.html head에 아래 스크립트 필수입니다
// <script src="https://t1.daumcdn.net/mapjsapi/bundle/postcode/prod/postcode.v2.js"></script>

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
      allowedTime: '09:00~18:00',
      sections: [
        { id: 200, start: '역삼동', end: '삼성동', time: '10:00~23:00', allowed: true },
      ],
    },
  ])

  // 구역 추가 폼: 구역명, 허용시간 시작/종료 분리 상태
  const [newZoneName, setNewZoneName] = useState('')
  const [newAllowedStartTime, setNewAllowedStartTime] = useState('')
  const [newAllowedEndTime, setNewAllowedEndTime] = useState('')

  // 구간 추가 폼 상태
  const [newSection, setNewSection] = useState({
    start: '',
    end: '',
    startTime: '',
    endTime: '',
    allowed: true,
  })

  const [selectedZoneId, setSelectedZoneId] = useState(null)
  const [selectedSectionIds, setSelectedSectionIds] = useState({})
  const [editingSectionId, setEditingSectionId] = useState(null)
  const [editingSectionInput, setEditingSectionInput] = useState({})
  const [zoneForPopup, setZoneForPopup] = useState(null)

  // zone.id 별 input ref 관리
  const inputRefs = useRef({})

  const ensureZoneRefs = (zoneId) => {
    if (!inputRefs.current[zoneId]) {
      inputRefs.current[zoneId] = {
        start: React.createRef(),
        end: React.createRef(),
        startTime: React.createRef(),
        endTime: React.createRef(),
      }
    }
    return inputRefs.current[zoneId]
  }

  // 구역 추가 함수 (허용시간 startTime, endTime 조합 저장)
  const handleAddZone = () => {
    if (!newZoneName.trim() || !newAllowedStartTime || !newAllowedEndTime) {
      alert('구역명과 허용 시간대를 입력하세요.')
      return
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
    ])
    setNewZoneName('')
    setNewAllowedStartTime('')
    setNewAllowedEndTime('')
  }

  // 이하 주요 함수는 기존과 동일 (구간 체크, 삭제, 편집 등) ...

  const handleSectionCheckbox = (zoneId, sectionId, checked) => {
    setSelectedSectionIds(prev => {
      const current = prev[zoneId] || []
      const next = checked ? Array.from(new Set([...current, sectionId])) : current.filter(id => id !== sectionId)
      return { ...prev, [zoneId]: next }
    })
  }

  const handleDeleteSections = (zoneId) => {
    const idsToDelete = selectedSectionIds[zoneId] || []
    if (idsToDelete.length === 0) return
    if (!window.confirm('선택한 구간을 삭제하시겠습니까?')) return
    setZones(zones.map(zone =>
      zone.id === zoneId ? { ...zone, sections: zone.sections.filter(s => !idsToDelete.includes(s.id)) } : zone
    ))
    setSelectedSectionIds(prev => ({ ...prev, [zoneId]: [] }))
  }

  const handleEditSection = (zoneId, section) => {
    setEditingSectionId(section.id)
    const [startT, endT] = section.time.split('~')
    setEditingSectionInput({
      start: section.start,
      end: section.end,
      startTime: startT || '',
      endTime: endT || '',
      allowed: section.allowed,
      zoneId,
    })
  }

  const handleEditInputChange = (field, value) => {
    setEditingSectionInput(prev => ({ ...prev, [field]: value }))
  }

  const handleSaveEdit = () => {
    const { zoneId, start, end, startTime, endTime, allowed } = editingSectionInput
    if (!start || !end || !startTime || !endTime) {
      alert('모든 구간 정보를 입력하세요.')
      return
    }
    const time = `${startTime}~${endTime}`
    setZones(zones.map(zone =>
      zone.id === zoneId
        ? {
          ...zone,
          sections: zone.sections.map(s =>
            s.id === editingSectionId
              ? { ...s, start, end, time, allowed: allowed === 'false' ? false : !!allowed }
              : s
          )
        }
        : zone
    ))
    setEditingSectionId(null)
    setEditingSectionInput({})
  }

  const handleCancelEdit = () => {
    setEditingSectionId(null)
    setEditingSectionInput({})
  }

  const handleAddSection = (zoneId) => {
    if (!newSection.start || !newSection.end || !newSection.startTime || !newSection.endTime) {
      alert('구간 정보를 모두 입력하세요.')
      return
    }
    const time = `${newSection.startTime}~${newSection.endTime}`

    setZones(zones.map(z =>
      z.id === zoneId
        ? {
          ...z,
          sections: [...z.sections, {
            start: newSection.start,
            end: newSection.end,
            time,
            allowed: newSection.allowed === 'false' ? false : !!newSection.allowed,
            id: Date.now(),
          }]
        }
        : z
    ))

    setNewSection({
      start: '',
      end: '',
      startTime: '',
      endTime: '',
      allowed: true,
    })
    setSelectedZoneId(null)

    focusNextInput(zoneId, 'addSection')
  }

  const openAddressPopup = (zoneId, type /* 'start'|'end' */) => {
    setZoneForPopup(zoneId)
    new window.daum.Postcode({
      oncomplete: function (data) {
        const address = data.roadAddress || data.jibunAddress

        setNewSection(ns => ({
          ...ns,
          [type]: address
        }))

        const refs = inputRefs.current[zoneId]
        if (!refs) return

        setTimeout(() => {
          if (type === 'start' && refs.end.current) refs.end.current.focus()
          else if (type === 'end' && refs.startTime.current) refs.startTime.current.focus()
        }, 0)
      }
    }).open()
  }

  const openAddressPopupForEdit = (field /* 'start'|'end' */) => {
    new window.daum.Postcode({
      oncomplete: function (data) {
        const address = data.roadAddress || data.jibunAddress
        setEditingSectionInput(prev => ({
          ...prev,
          [field]: address
        }))
      }
    }).open()
  }

  const focusNextInput = (currentZoneId, actionType) => {
    const currentIndex = zones.findIndex(z => z.id === currentZoneId)
    if (currentIndex === -1) return
    const nextZone = zones[currentIndex + 1]
    const refs = inputRefs.current

    if (actionType === 'addSection') {
      if (nextZone) {
        setSelectedZoneId(nextZone.id)
        setNewSection({
          start: '',
          end: '',
          startTime: '',
          endTime: '',
          allowed: true,
        })

        setTimeout(() => {
          const nextRefs = refs[nextZone.id]
          if (nextRefs && nextRefs.start.current) {
            nextRefs.start.current.focus()
          }
        }, 0)
      } else {
        setSelectedZoneId(null)
      }
    }
  }



  // === JSX ===
  return (
    <div style={{ background: '#fff', padding: 20, borderRadius: 10 }}>
      <h2>🕒 구역별 주정차 허용시간 및 구간정보 관리</h2>

      {/* 구역 추가 폼 */}
      <section style={{ margin: '24px 0 32px 0', display: 'flex', gap: 10, alignItems: 'center' }}>
        <input
          placeholder="구역명"
          value={newZoneName}
          onChange={e => setNewZoneName(e.target.value)}
          style={{
            padding: 7,
            border: '1px solid #364599ff',
            borderRadius: 6,
            background: '#f7fafd',
            width: 120
          }}
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
          type="time"
          value={newAllowedEndTime}
          onChange={e => setNewAllowedEndTime(e.target.value)}
          style={{
            padding: 6,
            width: 110,
            border: '1px solid #bfd6f2',
            borderRadius: 6,
            background: '#f7fafd',
          }}
        />

        <button onClick={handleAddZone} style={mutedBtn('#364599ff')}>
          구역 추가
        </button>
      </section>

      {/* 각 구역별 구간 목록 */}
      <section>
        {zones.length === 0 ? (
          <p style={{ color: '#777' }}>등록된 구역이 없습니다.</p>
        ) : (
          zones.map(zone => {
            const refs = ensureZoneRefs(zone.id)

            return (
              <div key={zone.id} style={{ marginBottom: 36, border: '1px solid #e0eaf6', borderRadius: 8, padding: 14 }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 20, marginBottom: 12 }}>
                  <span style={{ fontWeight: 700, fontSize: 18 }}>{zone.name}</span>
                  <span style={{ color: '#555' }}>{zone.allowedTime}</span>
                  <button
                    onClick={() => {
                      if (window.confirm('정말 해당 구역을 삭제하시겠습니까?')) {
                        setZones(zones.filter(z => z.id !== zone.id))
                        delete inputRefs.current[zone.id]
                      }
                    }}
                    style={{ marginLeft: 'auto', ...mutedBtn('#dd6565ff') }}
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
                        <td colSpan={6} style={{ color: '#999', padding: 12, textAlign: 'center' }}>등록된 구간이 없습니다.</td>
                      </tr>
                    ) : (
                      zone.sections.map(section =>
                        editingSectionId === section.id ? (
                          <tr key={section.id} style={{ borderBottom: '1px solid #e0eaf6', background: '#f6faff' }}>
                            <td style={tdStyle}><input type="checkbox" disabled /></td>
                            <td style={tdStyle}>
                              <div style={{ display: 'flex', gap: '6px', alignItems: 'center' }}>
                                <input
                                  value={editingSectionInput.start}
                                  onChange={e => handleEditInputChange('start', e.target.value)}
                                  style={{ width: 150 }}
                                />
                                <button
                                  type="button"
                                  onClick={() => {
                                    setZoneForPopup(editingSectionInput.zoneId)
                                    openAddressPopupForEdit('start')
                                  }}
                                  style={{ ...mutedBtn('#B3BCF2'), padding: '4px 8px', fontSize: 13 }}
                                >
                                  주소검색
                                </button>
                              </div>
                            </td>
                            <td style={tdStyle}>
                              <div style={{ display: 'flex', gap: '6px', alignItems: 'center' }}>
                                <input
                                  value={editingSectionInput.end}
                                  onChange={e => handleEditInputChange('end', e.target.value)}
                                  style={{ width: 150 }}
                                />
                                <button
                                  type="button"
                                  onClick={() => {
                                    setZoneForPopup(editingSectionInput.zoneId)
                                    openAddressPopupForEdit('end')
                                  }}
                                  style={{ ...mutedBtn('#B3BCF2'), padding: '4px 8px', fontSize: 13 }}
                                >
                                  주소검색
                                </button>
                              </div>
                            </td>
                            <td style={tdStyle}>
                              <input
                                type="time"
                                value={editingSectionInput.startTime || ''}
                                onChange={e => handleEditInputChange('startTime', e.target.value)}
                                style={{ width: 110 }}
                              />
                              <span style={{ margin: '0 4px' }}>~</span>
                              <input
                                type="time"
                                value={editingSectionInput.endTime || ''}
                                onChange={e => handleEditInputChange('endTime', e.target.value)}
                                style={{ width: 110 }}
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
                              <button onClick={handleSaveEdit} style={mutedBtn('#364599ff')}>저장</button>
                              <button onClick={handleCancelEdit} style={mutedBtn('#bdbdbd')}>취소</button>
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
                              <button onClick={() => handleEditSection(zone.id, section)} style={mutedBtn('#364599ff')}>수정</button>
                            </td>
                          </tr>
                        )
                      )
                    )}
                  </tbody>
                </table>

                {/* 구간 추가 폼 */}
                <div style={{ display: 'flex', gap: 8, alignItems: 'center', marginTop: 10 }}>
                  <input
                    ref={refs.start}
                    placeholder="출발 도로명 주소"
                    value={selectedZoneId === zone.id ? newSection.start : ''}
                    onChange={e => {
                      setSelectedZoneId(zone.id)
                      setZoneForPopup(zone.id)
                      setNewSection(ns => ({ ...ns, start: e.target.value }))
                    }}
                    style={{
                      padding: 6,
                      width: 220,
                      border: '1px solid #bfd6f2',
                      borderRadius: 6,
                      background: '#f7fafd',
                    }}
                  />
                  <button
                    type="button"
                    onClick={() => openAddressPopup(zone.id, 'start')}
                    style={{ ...mutedBtn('#B3BCF2'), padding: '6px 11px' }}
                  >
                    주소검색
                  </button>

                  <input
                    ref={refs.end}
                    placeholder="도착 도로명 주소"
                    value={selectedZoneId === zone.id ? newSection.end : ''}
                    onChange={e => {
                      setSelectedZoneId(zone.id)
                      setZoneForPopup(zone.id)
                      setNewSection(ns => ({ ...ns, end: e.target.value }))
                    }}
                    style={{
                      padding: 6,
                      width: 220,
                      border: '1px solid #bfd6f2',
                      borderRadius: 6,
                      background: '#f7fafd',
                    }}
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
                      setSelectedZoneId(zone.id)
                      setNewSection(ns => ({ ...ns, endTime: e.target.value }))
                    }}
                    style={{
                      padding: 6,
                      width: 110,
                      border: '1px solid #bfd6f2',
                      borderRadius: 6,
                      background: '#f7fafd',
                    }}
                  />

                  <select
                    value={selectedZoneId === zone.id ? (newSection.allowed ? 'true' : 'false') : 'true'}
                    onChange={e => {
                      setSelectedZoneId(zone.id)
                      setNewSection(ns => ({ ...ns, allowed: e.target.value === 'true' }))
                    }}
                    style={{
                      padding: 6,
                      width: 90,
                      border: '1px solid #bfd6f2',
                      borderRadius: 6,
                      background: '#f7fafd',
                    }}
                  >
                    <option value="true">허용</option>
                    <option value="false">불가</option>
                  </select>
                  <button onClick={() => handleAddSection(zone.id)} style={mutedBtn('#364599ff')}>
                    구간 추가
                  </button>
                </div>

                {/* 선택구간 삭제 버튼 */}
                <div style={{ marginTop: 8, display: 'flex', justifyContent: 'flex-end' }}>
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
              </div>
            )
          })
        )}
      </section>
    </div>
  )
}

const mutedBtn = (color) => ({
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
})

const thStyle = {
  padding: '8px 10px',
  fontWeight: 600,
  fontSize: 15,
  borderBottom: '1px solid #e0eaf6',
  background: '#f2f6fb',
}
const tdStyle = {
  padding: '8px 10px',
  fontSize: 15,
  borderBottom: '1px solid #e0eaf6',
  textAlign: 'center',
}

export default ZonesManagement