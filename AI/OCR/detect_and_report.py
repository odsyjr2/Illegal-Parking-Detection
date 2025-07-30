import argparse
import cv2
import json
import requests
from datetime import datetime
from ultralytics import YOLO
from easyocr import Reader
from PIL import Image
from PIL.ExifTags import TAGS, GPSTAGS

# ------------------ Metadata 추출 ------------------ #
def extract_metadata(image_path):
    image = Image.open(image_path)
    exif_data = image._getexif()
    gps_info = {}
    result = {}

    if not exif_data:
        return None

    for tag, value in exif_data.items():
        decoded = TAGS.get(tag, tag)
        if decoded == "DateTimeOriginal":
            result["detection_time"] = datetime.strptime(value, "%Y:%m:%d %H:%M:%S").isoformat()
        if decoded == "GPSInfo":
            for t in value:
                sub_decoded = GPSTAGS.get(t, t)
                gps_info[sub_decoded] = value[t]

    def to_degrees(value):
        d, m, s = value
        return d[0]/d[1] + m[0]/m[1]/60 + s[0]/s[1]/3600

    if gps_info:
        lat = to_degrees(gps_info['GPSLatitude'])
        lon = to_degrees(gps_info['GPSLongitude'])
        if gps_info.get('GPSLatitudeRef') == 'S': lat *= -1
        if gps_info.get('GPSLongitudeRef') == 'W': lon *= -1
        result["latitude"] = lat
        result["longitude"] = lon

    return result

# ------------------ 탐지 프로세스 ------------------ #
def process_image(image_path, illegal_model, plate_model, ocr_model, api_url):
    image = cv2.imread(image_path)
    metadata = extract_metadata(image_path)
    if not metadata:
        print("[ERROR] 이미지에 메타데이터가 없습니다.")
        return

    result = illegal_model(image)[0]
    report_sent = False

    for box in result.boxes:
        cls_id = int(box.cls.item())
        conf = box.conf.item()
        if conf < 0.5 or cls_id != 0:
            continue

        x1, y1, x2, y2 = map(int, box.xyxy[0])
        car_crop = image[y1:y2, x1:x2]
        plate_result = plate_model(car_crop)[0]

        report = {
            "latitude": metadata["latitude"],
            "longitude": metadata["longitude"],
            "detection_time": metadata["detection_time"],
            "report_status": "탐지됨",
            "image_id": image_path.split('/')[-1].split('.')[0]
        }

        for pbox in plate_result.boxes:
            px1, py1, px2, py2 = map(int, pbox.xyxy[0])
            plate_crop = car_crop[py1:py2, px1:px2]
            ocr_output = ocr_model.readtext(plate_crop)
            if ocr_output:
                report["license_plate"] = ocr_output[0][1]
                report["report_status"] = "신고됨"
                break

        # API 전송
        headers = {'Content-Type': 'application/json'}
        response = requests.post(api_url, headers=headers, data=json.dumps(report))

        print("🔎 전송된 리포트:")
        print(json.dumps(report, ensure_ascii=False, indent=2))
        print(f"📡 응답 상태 코드: {response.status_code}")
        report_sent = True
        break  # 첫 차량만 처리

    if not report_sent:
        print("[INFO] 불법주정차 차량이 탐지되지 않았습니다.")

# ------------------ 메인 실행부 ------------------ #
def main():
    parser = argparse.ArgumentParser(description="불법주정차 탐지 및 OCR 리포트 전송기")
    parser.add_argument('--image_path', type=str, required=True, help='이미지 경로')
    parser.add_argument('--illegal_model', type=str, required=True, help='불법주정차 YOLO 모델 경로')
    parser.add_argument('--plate_model', type=str, required=True, help='번호판 YOLO 모델 경로')
    parser.add_argument('--api_url', type=str, required=True, help='리포트를 전송할 API 주소')
    args = parser.parse_args()

    illegal_model = YOLO(args.illegal_model)
    plate_model = YOLO(args.plate_model)
    ocr_model = Reader(['ko'], gpu=True)

    process_image(args.image_path, illegal_model, plate_model, ocr_model, args.api_url)

if __name__ == '__main__':
    main()
