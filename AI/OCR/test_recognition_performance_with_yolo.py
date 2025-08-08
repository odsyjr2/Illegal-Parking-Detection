# filename: evaluate_yolo_easyocr_pipeline_report.py

import os
import json
import cv2
import numpy as np
from tqdm import tqdm
import Levenshtein
from ultralytics import YOLO
from easyocr import Reader
# from EasyOCR.easyocr import *


# =====================
# 설정
# =====================
# IMG_DIR = "C:/Users/chobh/Desktop/bigProject/Data/자동차 차종-연식-번호판 인식용 영상/Validation/[원천]자동차번호판OCR데이터"
# LABEL_DIR = "C:/Users/chobh/Desktop/bigProject/Data/자동차 차종-연식-번호판 인식용 영상/Validation/[라벨]자동차번호판OCR_valid"
IMG_DIR = "C:/Users/chobh/Desktop/bigProject/Data/licence_plate_original/Validation/images" # 경로 수정
LABEL_DIR = "C:/Users/chobh/Desktop/bigProject/Data/licence_plate_original/Validation/annotations"
YOLO_MODEL_PATH = "C:/Users/chobh/Desktop/bigProject/Illegal-Parking-Detection/AI/Experiments/license_plate_detection_yolo11/25.08.05/weights/best.pt"  # YOLO 번호판 탐지 모델
YOLO_CONF = 0.5                         # YOLO confidence threshold
YOLO_IMGSZ = 640                        # YOLO 입력 이미지 크기

# =====================
# 유틸 함수
# =====================
def imread_korean(path):
    """한글 경로 이미지 로드"""
    stream = np.fromfile(path, dtype=np.uint8)
    img = cv2.imdecode(stream, cv2.IMREAD_COLOR)
    return img

# =====================
# 메인 함수
# =====================
def main():
    # 모델 로드
    print("[INFO] YOLO 모델 로드 중...")
    yolo_model = YOLO(YOLO_MODEL_PATH)

    print("[INFO] EasyOCR 모델 로드 중...")
    reader = Reader(['ko'], gpu=True, recog_network='custom_example')

    # 지표
    total_samples = 0
    exact_match_count = 0
    char_accuracy_sum = 0.0
    detection_fail_count = 0
    ocr_fail_count = 0

    results_samples = []

    # 평가 루프
    for label_file in tqdm(os.listdir(LABEL_DIR), desc="Evaluating"):
        if not label_file.endswith('.json'):
            continue
        
        # 라벨 읽기
        json_path = os.path.join(LABEL_DIR, label_file)
        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        gt_text = data['value'].strip()
        img_path = os.path.join(IMG_DIR, data['imagePath'])
        if not os.path.exists(img_path):
            continue
        
        img = imread_korean(img_path)
        if img is None:
            continue

        # 1️⃣ YOLO 탐지
        det_results = yolo_model.predict(img, imgsz=YOLO_IMGSZ, conf=YOLO_CONF, verbose=False)
        boxes = det_results[0].boxes.xyxy.cpu().numpy()

        if len(boxes) == 0:
            # 번호판 탐지 실패
            detection_fail_count += 1
            pred_text = ""
        else:
            # 가장 큰 박스 선택
            areas = [(x2 - x1) * (y2 - y1) for x1, y1, x2, y2 in boxes]
            largest_idx = int(np.argmax(areas))
            x1, y1, x2, y2 = map(int, boxes[largest_idx])
            plate_crop = img[y1:y2, x1:x2]

            # 2️⃣ EasyOCR 인식
            ocr_result = reader.recognize(plate_crop, detail=0)
            pred_text = ocr_result[0].strip() if len(ocr_result) > 0 else ""

            if pred_text != gt_text:
                ocr_fail_count += 1

        # 3️⃣ 성능 집계
        total_samples += 1
        if pred_text == gt_text:
            exact_match_count += 1

        if len(gt_text) > 0:
            char_acc = 1 - (Levenshtein.distance(pred_text, gt_text) / len(gt_text))
        else:
            char_acc = 0
        char_accuracy_sum += char_acc

        if len(results_samples) < 20:
            results_samples.append((img_path, gt_text, pred_text, char_acc))

    # 결과 출력
    exact_match_acc = exact_match_count / total_samples * 100
    avg_char_acc = char_accuracy_sum / total_samples * 100
    detection_fail_rate = detection_fail_count / total_samples * 100
    ocr_fail_rate = ocr_fail_count / (total_samples - detection_fail_count) * 100 if total_samples - detection_fail_count > 0 else 0

    print("\n===== 평가 결과 =====")
    print(f"총 샘플 수: {total_samples}")
    print(f"정확 매칭 정확도: {exact_match_acc:.2f}%")
    print(f"문자 단위 평균 정확도: {avg_char_acc:.2f}%")
    print(f"탐지 실패율 (Detection Fail Rate): {detection_fail_rate:.2f}%")
    print(f"인식 실패율 (OCR Fail Rate, 탐지 성공 시): {ocr_fail_rate:.2f}%")

    print("\n===== 예측 샘플 (일부) =====")
    for img_path, gt, pred, acc in results_samples:
        print(f"[GT] {gt}  |  [Pred] {pred}  |  CharAcc: {acc:.2f}")

# =====================
# 실행
# =====================
if __name__ == "__main__":
    main()
