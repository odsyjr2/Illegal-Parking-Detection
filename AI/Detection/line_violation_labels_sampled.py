import os
import json
import shutil
import argparse
from glob import glob
from tqdm import tqdm
from pathlib import Path
from multiprocessing import Pool, cpu_count
import cv2
import numpy as np

# 차량 클래스
VEHICLE_CLASS_MAP = {
    "vehicle_car": 0,
    "vehicle_bus": 1,
    "vehicle_truck": 2,
    "vehicle_bike": 3
}

# 차선 클래스 조합 (shoulder만)
LANE_COLORS = ["shoulder"]
LANE_STYLES = [
    "single_solid", "double_solid", "single_dashed",
    "left_dashed_double", "right_dashed_double"
]
LANE_CLASS_MAP = {
    f"lane_{color}_{style}": 4 + j
    for j, style in enumerate(LANE_STYLES)
    for color in LANE_COLORS
}

ALL_CLASSES = list(VEHICLE_CLASS_MAP.keys()) + list(LANE_CLASS_MAP.keys())

# =========================
# 유니코드 경로 대응 imread
# =========================
def imread_unicode(path):
    """한글/특수문자 경로 호환 이미지 로드"""
    path = str(path)
    if not os.path.exists(path):
        return None
    data = np.fromfile(path, dtype=np.uint8)
    if data.size == 0:
        return None
    return cv2.imdecode(data, cv2.IMREAD_COLOR)

# =========================
# 정규화 + 0~1 범위 보정
# =========================
def normalize_point(x, y, w, h):
    nx = min(max(round(x / w, 6), 0), 1)
    ny = min(max(round(y / h, 6), 0), 1)
    return nx, ny

def format_yoloseg_line(class_id, points, w, h):
    coords = []
    for p in points:
        x, y = normalize_point(p["x"], p["y"], w, h)
        coords.extend([x, y])
    return f"{class_id} " + " ".join(map(str, coords))

# =========================
# JSON 라벨 파싱
# =========================
def extract_objects_from_json(json_path):
    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    items = []
    objects = data.get("data_set_info", {}).get("data", [])
    for obj in objects:
        val = obj.get("value", {})
        extra = val.get("extra", {})
        if not val.get("points") or len(val["points"]) < 3:
            continue

        if extra.get("value") == "vehicle":
            label = val.get("object_Label", {}).get("vehicle_type")
            class_id = VEHICLE_CLASS_MAP.get(label)

        elif extra.get("value") == "lane":
            c = val.get("object_Label", {}).get("lane_type")
            s = val.get("object_Label", {}).get("lane_attribute")
            if not c.endswith("shoulder"):
                continue
            class_id = LANE_CLASS_MAP.get(f"{c}_{s}")
        else:
            continue

        if class_id is not None:
            items.append((class_id, val["points"]))
    return items

# =========================
# JSON → 이미지 경로
# =========================
def get_image_path_from_json(json_path):
    parts = Path(json_path).parts
    if "라벨링데이터" not in parts:
        return None
    idx = parts.index("라벨링데이터")
    rel_path = Path(*parts[idx+1:]).with_suffix(".jpg")
    img_path = Path(json_path).parents[idx] / "원천데이터" / rel_path
    return img_path

# =========================
# 개별 JSON 처리
# =========================
def process_one(args):
    json_path, img_dst_dir, lbl_dst_dir = args
    image_path = get_image_path_from_json(json_path)
    if not image_path.exists():
        return False

    # 유니코드 경로 호환 imread
    img = imread_unicode(image_path)
    if img is None:
        return False
    h, w = img.shape[:2]

    # 이미지 복사 (유니코드 호환)
    data = np.fromfile(str(image_path), dtype=np.uint8)
    cv2.imencode('.jpg', img)[1].tofile(str(img_dst_dir / image_path.name))

    # 라벨 생성
    label_items = extract_objects_from_json(json_path)
    if not label_items:
        return False

    label_file = lbl_dst_dir / (image_path.stem + ".txt")
    with open(label_file, 'w', encoding='utf-8') as f:
        for class_id, points in label_items:
            f.write(format_yoloseg_line(class_id, points, w, h) + "\n")
    return True

# =========================
# split(train/val) 처리
# =========================
def process_split(split, src_root, dst_root, frame_interval):
    folder_map = {"train": "1.Training", "val": "2.Validation"}
    src_dir = Path(src_root) / folder_map[split] / "라벨링데이터"
    img_dst = Path(dst_root) / "images" / split
    lbl_dst = Path(dst_root) / "labels" / split
    img_dst.mkdir(parents=True, exist_ok=True)
    lbl_dst.mkdir(parents=True, exist_ok=True)

    json_files = sorted(glob(str(src_dir / "**" / "*.json"), recursive=True))
    sampled_jsons = [jf for i, jf in enumerate(json_files) if i % frame_interval == 0]

    print(f"[{split.upper()}] 총 JSON 파일: {len(json_files)}, 샘플링 후: {len(sampled_jsons)}")
    args_list = [(Path(j), img_dst, lbl_dst) for j in sampled_jsons]

    with Pool(processes=cpu_count()) as pool:
        results = list(tqdm(pool.imap_unordered(process_one, args_list), total=len(args_list)))

    print(f"[{split.upper()}] 완료된 라벨 수: {sum(results)}")

# =========================
# main
# =========================
def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--src", default="D:/134.차로 위반 영상 데이터/01.데이터")
    parser.add_argument("--dst", default="C:/Users/chobh/Desktop/bigProject/Data/lane_violation_yoloseg_dataset_sampled/")
    parser.add_argument("--frame_interval", type=int, default=6,
                        help="프레임 샘플링 간격 (예: 5 → 5개 프레임 중 1개만 사용)")
    args = parser.parse_args()

    for split in ["train", "val"]:
        process_split(split, args.src, args.dst, args.frame_interval)

    print("\n✅ 샘플링 기반 변환 완료.")

if __name__ == "__main__":
    main()
