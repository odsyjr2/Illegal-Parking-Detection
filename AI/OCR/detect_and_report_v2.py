# detect_and_report_v2.py
import argparse
import cv2
import torch
import requests
from datetime import datetime
from ultralytics import YOLO
from pathlib import Path

# OCR 모델 로드 함수 (예시)
from deep_text_recognition_benchmark.demo import OCRModel  # 실제 OCR 코드에 맞게 경로 수정 필요

def load_models(yolo_weights, ocr_weights, device):
    print("[INFO] Loading YOLO model...")
    yolo_model = YOLO(yolo_weights)
    yolo_model.to(device)

    print("[INFO] Loading OCR model...")
    ocr_model = OCRModel(ocr_weights, device=device)  # OCR 구현체에 맞게 변경
    return yolo_model, ocr_model

def detect_and_recognize(yolo_model, ocr_model, frame, device, conf_thres=0.5):
    results = yolo_model(frame, conf=conf_thres, verbose=False)
    detections = []

    for r in results:
        for box in r.boxes:
            cls_id = int(box.cls.cpu().item())
            conf = float(box.conf.cpu().item())
            label = r.names[cls_id]

            x1, y1, x2, y2 = map(int, box.xyxy[0].cpu().numpy())

            detection_info = {
                "bbox": (x1, y1, x2, y2),
                "label": label,
                "conf": conf
            }

            # OCR 수행: 위반 차량만
            if label.lower() == "violation":
                crop_img = frame[y1:y2, x1:x2]
                plate_text = ocr_model.recognize(crop_img)
                detection_info["plate_number"] = plate_text
            else:
                detection_info["plate_number"] = None

            detections.append(detection_info)
    return detections

def pack_report_data(detections, latitude, longitude):
    reports = []
    now_time = datetime.utcnow().isoformat()

    for det in detections:
        status = "신고됨" if det["label"].lower() == "violation" else "탐지됨"
        reports.append({
            "latitude": latitude,
            "longitude": longitude,
            "status": status,
            "plate_number": det["plate_number"],
            "detected_time": now_time
        })
    return reports

def send_reports(api_url, reports):
    for rep in reports:
        try:
            r = requests.post(api_url, json=rep)
            if r.status_code == 200:
                print(f"[INFO] Report sent successfully: {rep}")
            else:
                print(f"[WARN] Failed to send report: {r.status_code} {r.text}")
        except Exception as e:
            print(f"[ERROR] API send error: {e}")

def main():
    parser = argparse.ArgumentParser(description="Illegal Parking Detection & Reporting v2")
    parser.add_argument("--source", type=str, required=True, help="Video/image path or RTSP URL")
    parser.add_argument("--yolo_weights", type=str, default="yolo_illegal_parking.pt", help="YOLO model weights")
    parser.add_argument("--ocr_weights", type=str, default="korean_g2.pth", help="OCR model weights")
    parser.add_argument("--latitude", type=float, required=True, help="CCTV latitude")
    parser.add_argument("--longitude", type=float, required=True, help="CCTV longitude")
    parser.add_argument("--api_url", type=str, default="http://localhost:8000/api/report", help="API endpoint URL")
    parser.add_argument("--device", type=str, default="cuda" if torch.cuda.is_available() else "cpu", help="Device to run on")
    parser.add_argument("--conf_thres", type=float, default=0.5, help="YOLO confidence threshold")
    args = parser.parse_args()

    # 모델 로드
    yolo_model, ocr_model = load_models(args.yolo_weights, args.ocr_weights, args.device)

    # 영상/이미지 입력 처리
    cap = cv2.VideoCapture(args.source)
    if not cap.isOpened():
        print(f"[ERROR] Cannot open source: {args.source}")
        return

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        detections = detect_and_recognize(yolo_model, ocr_model, frame, args.device, args.conf_thres)
        reports = pack_report_data(detections, args.latitude, args.longitude)

        if reports:
            send_reports(args.api_url, reports)

        # 시각화 (Optional)
        for det in detections:
            x1, y1, x2, y2 = det["bbox"]
            color = (0, 0, 255) if det["label"].lower() == "violation" else (0, 255, 0)
            cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
            text = f"{det['label']} {det['conf']:.2f}"
            if det["plate_number"]:
                text += f" | {det['plate_number']}"
            cv2.putText(frame, text, (x1, y1 - 5), cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)

        cv2.imshow("Detection & Report", frame)
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    cap.release()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    main()
