import os
import json
import cv2
import numpy as np
from easyocr import Reader
from tqdm import tqdm
import Levenshtein

# # 데이터 경로
# IMG_DIR = "C:/Users/chobh/Desktop/bigProject/Data/자동차 차종-연식-번호판 인식용 영상/Validation/[원천]자동차번호판OCR데이터"
# LABEL_DIR = "C:/Users/chobh/Desktop/bigProject/Data/자동차 차종-연식-번호판 인식용 영상/Validation/[라벨]자동차번호판OCR_valid"
IMG_DIR = "C:/Users/chobh/Desktop/bigProject/Data/licence_plate_original/Validation/images" # 경로 수정
LABEL_DIR = "C:/Users/chobh/Desktop/bigProject/Data/licence_plate_original/Validation/annotations"

# EasyOCR Reader (한글+영문+숫자)
reader = Reader(['ko', 'en'], gpu=True, recog_network='custom_example')  # GPU 사용 권장

# 평가 지표
total_samples = 0
exact_match_count = 0
char_accuracy_sum = 0.0

# 결과 저장 (샘플)
results_samples = []

def imread_korean(path):
    """한글 경로 이미지 읽기 (cv2.imread 대체)"""
    stream = np.fromfile(path, dtype=np.uint8)
    img = cv2.imdecode(stream, cv2.IMREAD_COLOR)
    return img

for label_file in tqdm(os.listdir(LABEL_DIR)):
    if not label_file.endswith('.json'):
        continue
    
    json_path = os.path.join(LABEL_DIR, label_file)
    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    gt_text = data['value'].strip()  # 정답 번호판
    img_path = os.path.join(IMG_DIR, data['imagePath'])

    if not os.path.exists(img_path):
        continue
    
    img = imread_korean(img_path)
    if img is None:
        continue

    # EasyOCR 인식
    ocr_result = reader.readtext(img, detail=0)  # detail=0 → 텍스트 리스트만 반환
    
    if len(ocr_result) == 0:
        pred_text = ""
    else:
        pred_text = ocr_result[0].strip()

    # 정확도 계산
    total_samples += 1
    if pred_text == gt_text:
        exact_match_count += 1

    if len(gt_text) > 0:
        char_acc = 1 - (Levenshtein.distance(pred_text, gt_text) / len(gt_text))
    else:
        char_acc = 0
    char_accuracy_sum += char_acc

    # 샘플 저장
    if len(results_samples) < 20:  # 처음 20개만 저장
        results_samples.append((img_path, gt_text, pred_text, char_acc))

# 최종 성능 계산
if __name__=="__main__":
    exact_match_acc = exact_match_count / total_samples * 100
    avg_char_acc = char_accuracy_sum / total_samples * 100

    print(f"총 샘플 수: {total_samples}")
    print(f"정확 매칭 정확도: {exact_match_acc:.2f}%")
    print(f"문자 단위 평균 정확도: {avg_char_acc:.2f}%")

    print("\n===== 예측 샘플 (일부) =====")
    for img_path, gt, pred, acc in results_samples:
        print(f"[GT] {gt}  |  [Pred] {pred}  |  CharAcc: {acc:.2f}")
