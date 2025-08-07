import './CheckModal.css'
import { useState, useEffect } from 'react'

const TERMS = [
  {
    id: 'terms1',
    title: '개인정보 수집 및 이용 동의 (필수)',
    content: `회사는 회원가입 및 서비스 제공을 위해 아래와 같은 개인정보를 수집하고 이용합니다.\n
[수집 항목]
- 이름
- 이메일 주소\n
[수집 목적]
- 회원 식별 및 가입 처리
- 로그인 및 기본 서비스 제공\n
[보유 및 이용 기간]
- 회원 탈퇴 시 지체 없이 파기
- 단, 서비스 악용, 분쟁 대응을 위해 탈퇴 후 30일간 보관 후 완전 삭제\n
※ 위 수집 및 이용에 동의하지 않을 권리가 있으며, 동의 거부 시 회원가입이 제한될 수 있습니다.`,
    required: true,
  },
  {
    id: 'terms2',
    title: '개인정보 제3자 제공 동의 (필수)',
    content: `회사는 신고 처리 및 법령 준수를 위해 아래와 같은 경우 개인정보를 제3자에게 제공합니다.\n
[제공 대상]
- 관련 행정기관, 사법기관 등\n
[제공 항목]
- 신고 사진, 위치 정보, 신고 내용, 신고자 이메일\n
[제공 목적]
- 신고 내용의 조사 및 법적 대응\n
[보유 및 제공 기간]
- 제공 시점으로부터 3년 보관 후 파기`,
    required: true,
  },
  {
    id: 'terms3',
    title: '마케팅 정보 수신 동의 (선택)',
    content: `회사는 서비스 소식, 업데이트, 이벤트 안내 등의 마케팅 정보를 이메일로 발송할 수 있습니다.\n
[수신 항목]
- 이메일 주소\n
[수신 목적]
- 서비스 및 이벤트 안내, 업데이트 알림\n
[수신 거부]
- 메일 하단의 수신 거부 기능을 통해 언제든지 철회 가능\n
※ 본 항목은 선택 사항이며, 동의하지 않아도 서비스 이용에 제한은 없습니다.`,
    required: false,
  },
]


function CheckModal({ onClose, onAgree }) {
  const [checked, setChecked] = useState({})
  const [allChecked, setAllChecked] = useState(false)

  useEffect(() => {
    const all = TERMS.every(t => checked[t.id])
    setAllChecked(all)
  }, [checked])

  const handleCheck = (id, value) => {
    setChecked(prev => ({
      ...prev,
      [id]: value,
    }))
  }

  const handleAllCheck = () => {
    const newValue = !allChecked
    const newChecked = {}
    TERMS.forEach(term => {
      newChecked[term.id] = newValue
    })
    setChecked(newChecked)
  }

  const isAllRequiredChecked = TERMS
    .filter(t => t.required)
    .every(t => checked[t.id])

  return (
    <div className="modal-backdrop">
      <div className="modal-box">
        <h3>약관 동의</h3>

        <label className="all-check">
          <input
            type="checkbox"
            checked={allChecked}
            onChange={handleAllCheck}
          />
          전체 동의
        </label>
        <div className="terms-content">
            <div className="scrollable">
            { `- 전체동의 시 필수 사항 및 선택사항에 대해 일관 동의하게 되며, 개별적으로도 동의를 선택하실 수 있습니다
               - 필수 항목은 서비스 제공을 위해 필요한 항목이므로, 동의를 거부하시는 경우 서비스 이용에 제한이 있을수 있습니다.`}
            </div>
        </div>

        <div className="terms-list">
          {TERMS.map(term => (
            <div key={term.id} className="terms-item">
              <label>
                <input
                  type="checkbox"
                  checked={!!checked[term.id]}
                  onChange={(e) => handleCheck(term.id, e.target.checked)}
                />
                {term.title} {term.required && <span style={{ color: 'red' }}>*</span>}
              </label>
              <div className="terms-content">
                <div className="scrollable">
                  {term.content}
                </div>
              </div>
            </div>
          ))}
        </div>

        <div className="modal-buttons">
          <button onClick={onClose}>취소</button>
          <button
            onClick={() => {
              if (isAllRequiredChecked) {
                onAgree()
              } else {
                alert('필수 약관에 모두 동의해야 합니다.')
              }
            }}
          >
            확인
          </button>
        </div>
      </div>
    </div>
  )
}

export default CheckModal
