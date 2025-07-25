import os
import json
import shutil
from glob import glob
from tqdm import tqdm
from collections import defaultdict
import argparse

def parse_args():
    parser = argparse.ArgumentParser(description="빠른 불법주정차 YOLO용 커스텀 데이터셋 생성기")
    parser.add_argument("--src", default=r"C:\Users\chobh\Desktop\bigProject\Data\138.종합 민원 이미지 AI데이터\01.데이터", help="원본 데이터 루트")
    parser.add_argument("--dst", default=r"C:\Users\chobh\Desktop\bigProject\Data\oneclass_illegal_parking_dataset_intersect", help="타겟 디렉터리 루트")
    parser.add_argument("--mode", default="intersect", choices=["all", "intersect"], help="중복 이미지만 저장할지 여부 (intersect 모드)")
    return parser.parse_args()

def get_class_removed_filenames(directory, ext=".jpg"):
    return {fname[3:]: os.path.join(directory, fname) for fname in os.listdir(directory) if fname.endswith(ext)}

def convert_box_to_yolo(box, img_w, img_h):
    x_center = (box["x"] + box["w"] / 2) / img_w
    y_center = (box["y"] + box["h"] / 2) / img_h
    width = box["w"] / img_w
    height = box["h"] / img_h
    return [0, round(x_center, 6), round(y_center, 6), round(width, 6), round(height, 6)]

def split_name_mapping(split_name):
    return {
        "train": {
            "label_dir": os.path.join("1.Training", "라벨링데이터", "TL3", "불법주정차"),
            "image_dir": os.path.join("1.Training", "원천데이터", "TS3", "불법주정차")
        },
        "val": {
            "label_dir": os.path.join("2.Validation", "라벨링데이터", "VL3", "불법주정차"),
            "image_dir": os.path.join("2.Validation", "원천데이터", "VS3", "불법주정차")
        }
    }[split_name]

def preload_all_jsons(label_dir):
    all_json_map = defaultdict(list)
    all_json_paths = glob(os.path.join(label_dir, "*", "*.json"))
    for path in all_json_paths:
        fname = os.path.basename(path)
        key = "_".join(fname.split("_")[1:])  # remove 접두어
        key = os.path.splitext(key)[0]       # remove .json
        all_json_map[key].append(path)
    return all_json_map

def process_split(split_name, src_root, dst_root, mode):
    print(f"\n[{split_name.upper()}] 데이터 처리 시작")

    label_dir = os.path.join(src_root, split_name_mapping(split_name)["label_dir"])
    image_dir = os.path.join(src_root, split_name_mapping(split_name)["image_dir"])

    mode_map = {
        "day": ["불법주정차SUV(낮)", "불법주정차승용차(낮)"],
        "night": ["불법주정차SUV(밤)", "불법주정차승용차(밤)"]
    }

    all_json_map = preload_all_jsons(label_dir)

    for mode_time, categories in mode_map.items():
        print(f"\n▶ [{split_name.upper()} - {mode_time.upper()}] 처리 시작")

        all_images = {}
        for category in categories:
            img_dir = os.path.join(image_dir, category)
            image_files = get_class_removed_filenames(img_dir, ".jpg")
            for name, path in image_files.items():
                if name not in all_images:
                    all_images[name] = path

        if mode == "intersect":
            intersect_keys = [k for k, v in all_json_map.items() if len(v) >= 2]
            all_images = {k: v for k, v in all_images.items() if os.path.splitext(k)[0] in intersect_keys}

        image_out_dir = os.path.join(dst_root, "images", split_name, mode_time)
        label_out_dir = os.path.join(dst_root, "labels", split_name, mode_time)
        os.makedirs(image_out_dir, exist_ok=True)
        os.makedirs(label_out_dir, exist_ok=True)

        saved_images, saved_labels = 0, 0

        for img_name in tqdm(sorted(all_images.keys()), desc=f"{split_name}/{mode_time}", unit="file", leave=False):
            base_name = os.path.splitext(img_name)[0]
            json_paths = all_json_map.get(base_name, [])

            final_boxes = []
            img_w, img_h = 416, 416

            for json_path in json_paths:
                try:
                    with open(json_path, "r", encoding="utf-8") as f:
                        ann = json.load(f)

                    bbox_ann = ann.get("annotations", {}).get("Bbox Annotation", {})
                    if "Resolution" in bbox_ann:
                        res = bbox_ann["Resolution"].split("x")
                        img_w, img_h = int(res[0]), int(res[1])

                    for box in bbox_ann.get("Box", []):
                        yolo_box = convert_box_to_yolo(box, img_w, img_h)
                        final_boxes.append(yolo_box)
                except Exception as e:
                    print(f"[⚠️ 오류] {json_path} → {e}")

            img_src_path = all_images[img_name]
            img_dst_path = os.path.join(image_out_dir, img_name)
            if not os.path.exists(img_dst_path):
                shutil.copy2(img_src_path, img_dst_path)
                saved_images += 1

            if final_boxes:
                label_txt_path = os.path.join(label_out_dir, os.path.splitext(img_name)[0] + ".txt")
                with open(label_txt_path, "w") as f:
                    for box in final_boxes:
                        f.write(" ".join(map(str, box)) + "\n")
                saved_labels += 1

        print(f"  📊 SUV/승용차 원본 이미지 수 (중복 포함): {sum(len(os.listdir(os.path.join(image_dir, c))) for c in categories)}")
        print(f"  🔁 중복 제거된 최종 이미지 수: {len(all_images)}")
        print(f"  ✅ YOLO 라벨 생성: {saved_labels}개")
        print(f"  🖼️ 이미지 저장: {saved_images}개")

def main():
    args = parse_args()
    print("🚀 빠른 YOLO 데이터셋 생성 시작")

    process_split("train", args.src, args.dst, args.mode)
    process_split("val", args.src, args.dst, args.mode)

    print("\n🎉 전체 처리 완료!")
    print(f"📂 경로 요약:\n- 이미지: {args.dst}\\images\\(train|val)\\(day|night)\\\n- 라벨: {args.dst}\\labels\\(train|val)\\(day|night)\\")

if __name__ == "__main__":
    main()