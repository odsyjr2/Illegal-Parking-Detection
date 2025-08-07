## 시스템 전체 절차 요약

[이미지 1장]
 ├─ 1. YOLO로 불법주정차 탐지
 ├─ 2. 불법주정차일 경우
 │    ├─ 번호판 탐지 → OCR 가능 여부 판단
 │    ├─ 리포트 상태 설정 ("신고됨" or "탐지됨")
 └─ 3. 이미지 메타데이터에서 정보 추출
      (위도, 경도, 탐지 시간)
 └─ 4. 리포트 정보 API 형태로 패킹 후 전송


## 패킹할 데이터 구조 예시
{
  "latitude": 37.4821,
  "longitude": 127.0192,
  "report_status": "신고됨",
  "detection_time": "2025-07-28T15:40:10",
  "license_plate": "12가3456",   # 신고됨일 경우 포함
  "image_id": "IMG_20250728_154010"   # (선택) 추후 저장된 리포트 추적용
}


EasyOCR github 설치 후 진행


fine tuning 모델 적용

git clone https://github.com/JaidedAI/EasyOCR.git C:/dev/easyocr
cd C:/dev/easyocr

# dev 버전으로 설치
pip install -e . --user 

https://github.com/JaidedAI/EasyOCR/blob/master/custom_model.md 참조하여
~/.EasyOCR/model, ~/.EasyOCR/user_network 설정