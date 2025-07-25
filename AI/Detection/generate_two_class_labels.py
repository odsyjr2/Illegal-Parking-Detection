## normal parking class pseudo labeling

import os
import cv2
import numpy as np
from tqdm import tqdm
from ultralytics import YOLO

# 설정
IMAGE_ROOT = 'C:/Users/chobh/Desktop/bigProject/Data/oneclass_illegal_parking_dataset_intersect/images/'
LABEL_ROOT = 'C:/Users/chobh/Desktop/bigProject/Data/oneclass_illegal_parking_dataset_intersect/labels/'
OUTPUT_ROOT = 'C:/Users/chobh/Desktop/bigProject/Data/oneclass_illegal_parking_dataset_intersect/two_class_pseudo_label'
MODEL_PATH = 'C:/Users/chobh/Desktop/bigProject/Illegal-Parking-Detection/AI/Experiments/coco_custom_vehicle_seg/25.07.23/weights/best.pt'

CONF_THRESHOLD = 0.5
IOU_THRESHOLD = 0.5

NORMAL_CLASS_ID = 0
ILLEGAL_CLASS_ID = 1
CAR_CLASS_ID_IN_MODEL = 0  # 차량 class_id만 사용 (coco 데이터셋 학습 모델)

# 모델 로드
model = YOLO(MODEL_PATH)

# IoU 계산 함수
def compute_iou(box1, box2):
    xA = max(box1[0], box2[0])
    yA = max(box1[1], box2[1])
    xB = min(box1[2], box2[2])
    yB = min(box1[3], box2[3])
    interArea = max(0, xB - xA) * max(0, yB - yA)
    box1Area = (box1[2]-box1[0]) * (box1[3]-box1[1])
    box2Area = (box2[2]-box2[0]) * (box2[3]-box2[1])
    return interArea / float(box1Area + box2Area - interArea + 1e-6)

# 하위 폴더 순회
splits = ['train', 'val']
times = ['day', 'night']

for split in splits:
    for time in times:
        image_dir = os.path.join(IMAGE_ROOT, split, time)
        label_dir = os.path.join(LABEL_ROOT, split, time)
        output_dir = os.path.join(OUTPUT_ROOT, split, time)
        os.makedirs(output_dir, exist_ok=True)

        print(f"\n📁 Processing {split}/{time} ...")
        image_files = [f for f in os.listdir(image_dir) if f.lower().endswith(('.jpg', '.png'))]

        for img_file in tqdm(image_files, desc=f"[{split}/{time}]"):
            img_path = os.path.join(image_dir, img_file)
            label_path = os.path.join(label_dir, os.path.splitext(img_file)[0] + ".txt")
            output_label_path = os.path.join(output_dir, os.path.splitext(img_file)[0] + ".txt")

            # 이미지 로딩
            img = cv2.imread(img_path)
            if img is None:
                print(f"⚠️ 이미지 불러오기 실패: {img_path}")
                continue
            h, w = img.shape[:2]

            # 기존 불법주정차 라벨 (class_id = 0) → 1로 변환
            illegal_boxes = []
            gt_lines = []
            if os.path.exists(label_path):
                with open(label_path, 'r') as f:
                    for line in f.readlines():
                        cls, cx, cy, bw, bh = map(float, line.strip().split())
                        x1 = (cx - bw / 2) * w
                        y1 = (cy - bh / 2) * h
                        x2 = (cx + bw / 2) * w
                        y2 = (cy + bh / 2) * h
                        illegal_boxes.append([x1, y1, x2, y2])
                        gt_lines.append(f"{ILLEGAL_CLASS_ID} {cx:.6f} {cy:.6f} {bw:.6f} {bh:.6f}\n")

            # 차량 탐지 (YOLO 추론)
            results = model.predict(img_path, conf=CONF_THRESHOLD, iou=0.5, verbose=False)

            if results[0].boxes is not None and results[0].boxes.xyxy is not None:
                pred_boxes = results[0].boxes.xyxy.cpu().numpy()
                pred_classes = results[0].boxes.cls.cpu().numpy().astype(int)
            else:
                pred_boxes = []
                pred_classes = []

            # 차량 class_id = 0 인 것만 필터링
            filtered_boxes = [box for box, cls in zip(pred_boxes, pred_classes) if cls == CAR_CLASS_ID_IN_MODEL]

            # 결과 저장
            normal_count = 0
            with open(output_label_path, 'w') as fw:
                # 기존 GT: class_id = 1로 저장
                for line in gt_lines:
                    fw.write(line)

                # 정상 차량: class_id = 0
                for box in filtered_boxes:
                    x1, y1, x2, y2 = box
                    overlap = any(compute_iou(box, gt_box) >= IOU_THRESHOLD for gt_box in illegal_boxes)
                    if overlap:
                        continue

                    bw = (x2 - x1) / w
                    bh = (y2 - y1) / h
                    cx = (x1 + x2) / 2 / w
                    cy = (y1 + y2) / 2 / h
                    fw.write(f"{NORMAL_CLASS_ID} {cx:.6f} {cy:.6f} {bw:.6f} {bh:.6f}\n")
                    normal_count += 1

            print(f"✅ {img_file}: 불법={len(gt_lines)} 정상={normal_count}")
