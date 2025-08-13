# line_violation_labels.py
# YOLO-seg 학습용: 차량 + 갓길 차선 어노테이션 전용 변환기 (shoulder only)

import os
import json
import shutil
import argparse
from glob import glob
from tqdm import tqdm
from pathlib import Path
from multiprocessing import Pool, cpu_count

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

# YOLO-seg 포맷

def normalize_point(x, y, w=1920, h=1080):
    return round(x / w, 6), round(y / h, 6)

def format_yoloseg_line(class_id, points):
    coords = []
    for p in points:
        x, y = normalize_point(p["x"], p["y"])
        coords.extend([x, y])
    return f"{class_id} " + " ".join(map(str, coords))

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
            c = val.get("object_Label", {}).get("lane_type")  # lane_shoulder
            s = val.get("object_Label", {}).get("lane_attribute")  # single_solid
            if not c.endswith("shoulder"):
                continue  # shoulder만 필터링
            class_id = LANE_CLASS_MAP.get(f"{c}_{s}")
        else:
            continue

        if class_id is not None:
            items.append((class_id, val["points"]))

    return items

def get_image_path_from_json(json_path):
    parts = Path(json_path).parts
    if "라벨링데이터" not in parts:
        return None
    idx = parts.index("라벨링데이터")
    rel_path = Path(*parts[idx+1:]).with_suffix(".jpg")
    img_path = Path(json_path).parents[idx] / "원천데이터" / rel_path
    return img_path

def process_one(args):
    json_path, img_dst_dir, lbl_dst_dir = args

    image_path = get_image_path_from_json(json_path)
    if not image_path.exists():
        return False

    shutil.copy(image_path, img_dst_dir / image_path.name)

    label_items = extract_objects_from_json(json_path)
    if not label_items:
        return False

    label_file = lbl_dst_dir / (image_path.stem + ".txt")
    with open(label_file, 'w') as f:
        for class_id, points in label_items:
            f.write(format_yoloseg_line(class_id, points) + "\n")

    return True

def process_split(split, src_root, dst_root):
    folder_map = {"train": "1.Training", "val": "2.Validation"}
    src_dir = Path(src_root) / folder_map[split] / "라벨링데이터"
    img_dst = Path(dst_root) / "images" / split
    lbl_dst = Path(dst_root) / "labels" / split
    img_dst.mkdir(parents=True, exist_ok=True)
    lbl_dst.mkdir(parents=True, exist_ok=True)

    json_files = sorted(glob(str(src_dir / "**" / "*.json"), recursive=True))
    args_list = [(Path(j), img_dst, lbl_dst) for j in json_files]

    print(f"[{split.upper()}] 총 JSON 파일: {len(json_files)}")
    with Pool(processes=cpu_count()) as pool:
        results = list(tqdm(pool.imap_unordered(process_one, args_list), total=len(args_list)))

    print(f"[{split.upper()}] 완료된 라벨 수: {sum(results)}")

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--src", default="D:/134.차로 위반 영상 데이터/01.데이터")
    parser.add_argument("--dst", default="D:/lane_violation_yoloseg_dataset")
    args = parser.parse_args()

    for split in ["train", "val"]:
        process_split(split, args.src, args.dst)

    print("\n✅ 전체 변환 완료.")

if __name__ == "__main__":
    main()
