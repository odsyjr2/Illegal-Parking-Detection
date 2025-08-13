import './CheckModal.css'
import { useState, useEffect } from 'react'

const TERMS = [
  {
    id: 'terms_age',
    title: '만 14세 이상 확인 (필수)',
    content: `본인은 만 14세 이상임을 확인합니다.\n
              만 14세 미만인 경우 회원 가입이 불가능하며, 법정대리인의 동의가 필요합니다.`,
    required: true,
  },

  {
    id: 'terms1',
    title: '개인정보 수집 및 이용 동의 (필수)',
    content: `[수집 항목]
              - 이름, 이메일 주소
              [수집 목적]
              - 회원 식별, 가입 처리, 로그인 및 서비스 제공
              [보유 기간]
              - 탈퇴 시 지체 없이 파기
              - 단, 서비스 악용·분쟁 대응을 위해 탈퇴 후 30일 보관 후 삭제
              ※ 동의 거부 시 회원가입이 제한됩니다.`,
    required: true,
  },
  {
    id: 'terms2',
    title: '개인정보 제3자 제공 동의 (필수)',
    content: `[제공 대상]
              - 관련 행정기관, 사법기관 등
              [제공 항목]
              - 신고 사진, 위치 정보, 신고 내용, 신고자 이메일
              [제공 목적]
              - 신고 조사 및 법적 대응
              [보유·제공 기간]
              - 제공 시점부터 3년 보관 후 파기`,
    required: true,
  },
  {
    id: 'terms3',
    title: '마케팅 정보 수신 동의 (선택)',
    content: `[수신 항목]
              - 이메일 주소
              [목적]
              - 서비스·이벤트 안내, 업데이트 알림
              [거부]
              - 메일 하단에서 수신 거부 가능
              ※ 미동의 시 서비스 이용 제한 없음`,
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
            {`- 전체동의 시 필수·선택 항목에 모두 동의하며, 개별 동의도 가능합니다.
- 필수 항목은 서비스 제공에 필요하므로, 거부 시 이용이 제한됩니다.`}
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
                <div className="scrollable">{term.content}</div>
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
