import os
import json
import shutil
import argparse
from pathlib import Path
from tqdm import tqdm

# 클래스 인덱스 매핑
LANE_TYPE = {
    "lane_white": 0,
    "lane_blue": 1,
    "lane_yellow": 2,
    "lane_shoulder": 3
}
LANE_ATTR = {
    "single_solid": 4,
    "double_solid": 5,
    "single_dashed": 6,
    "left_dashed_double": 7,
    "right_dashed_double": 8
}

def get_class_id(label, attr):
    if label in LANE_TYPE:
        return LANE_TYPE[label]
    if attr in LANE_ATTR:
        return LANE_ATTR[attr]
    return None

def normalize_polygon(points, img_w=1920, img_h=1080):
    return [f"{x/img_w:.6f} {y/img_h:.6f}" for x, y in points]

def match_vehicle_condition(obj, target_attr, target_violation):
    """차량 객체가 조건을 만족하는지 확인"""
    if obj.get("value", {}).get("extra", {}).get("value") != "vehicle":
        return False
    attr = obj["value"].get("object_Label", {}).get("vehicle_attribute", "")
    violation = obj["value"].get("metainfo", {}).get("violation_type", "").lower()
    return (attr == target_attr and violation == target_violation)

def stream_clip_matches(json_dir, target_attr, target_violation):
    """클립에 조건에 맞는 차량 객체가 하나라도 있는지 확인"""
    for json_file in Path(json_dir).glob("*.json"):
        try:
            with open(json_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
        except:
            continue
        for obj in data.get("data_set_info", {}).get("data", []):
            if match_vehicle_condition(obj, target_attr, target_violation):
                return True
    return False

def convert_lane_objects(json_file, dst_label_path, src_img_path, dst_img_path):
    with open(json_file, 'r', encoding='utf-8') as f:
        data = json.load(f)

    lines = []
    for obj in data["data_set_info"]["data"]:
        if obj.get("value", {}).get("extra", {}).get("value") != "lane":
            continue
        label = obj["value"]["object_Label"].get("lane_type", "")
        attr = obj["value"]["object_Label"].get("lane_attribute", "")
        class_id = get_class_id(label, attr)
        if class_id is None:
            continue
        points = [(p["x"], p["y"]) for p in obj["value"]["points"]]
        norm = normalize_polygon(points)
        lines.append(f"{class_id} " + " ".join(norm))

    if lines:
        with open(dst_label_path, 'w', encoding='utf-8') as f:
            f.write("\n".join(lines))
        if src_img_path.exists():
            shutil.copy(src_img_path, dst_img_path)
            return True
    return False

def process_streams(src_root, dst_root, attr, violation):
    json_root = Path(src_root) / "라벨링데이터"
    img_root = Path(src_root) / "원천데이터"
    dst_img_dir = Path(dst_root) / "images/train"
    dst_lbl_dir = Path(dst_root) / "labels/train"
    dst_img_dir.mkdir(parents=True, exist_ok=True)
    dst_lbl_dir.mkdir(parents=True, exist_ok=True)

    stream_dirs = [p for p in json_root.rglob("*") if p.is_dir() and "[" in p.name]
    print(f"🔍 영상 스트림 폴더 수: {len(stream_dirs)}")

    saved = 0
    for stream in tqdm(stream_dirs, desc="클립 단위 처리"):
        if not stream_clip_matches(stream, attr, violation):
            continue

        rel_path = stream.relative_to(json_root)
        img_stream_dir = img_root / rel_path

        for json_file in stream.glob("*.json"):
            try:
                with open(json_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
            except:
                continue

            img_name = Path(data["data_set_info"]["sourceValue"]).name
            label_name = img_name.replace(".jpg", ".txt")
            dst_lbl_path = dst_lbl_dir / label_name
            dst_img_path = dst_img_dir / img_name
            src_img_path = img_stream_dir / img_name

            success = convert_lane_objects(json_file, dst_lbl_path, src_img_path, dst_img_path)
            if success:
                saved += 1

    print(f"\n✅ 조건에 맞는 이미지/라벨 쌍 총 {saved}개 생성 완료.")

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--src", required=True, help="원본 루트 폴더")
    parser.add_argument("--dst", required=True, help="저장할 디렉토리")
    parser.add_argument("--attribute", required=True, choices=["normal", "danger", "violation"], help="차량 속성 선택")
    parser.add_argument("--violation", required=True, choices=["white", "blue", "yellow", "shoulder"], help="차선 색상 선택")
    args = parser.parse_args()

    process_streams(args.src, args.dst, args.attribute, args.violation)

if __name__ == "__main__":
    main()
