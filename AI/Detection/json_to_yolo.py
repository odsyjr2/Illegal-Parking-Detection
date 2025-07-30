import json
import os
from glob import glob
from tqdm import tqdm

# 통합 대상 클래스들
TARGET_CLASSES = {
    "불법주정차SUV(낮)",
    "불법주정차SUV(밤)",
    "불법주정차승용차(낮)",
    "불법주정차승용차(밤)"
}

def convert_to_yolo(json_file_path, output_dir):
    """
    JSON 파일을 읽어 YOLO 포맷의 txt 파일로 변환합니다.
    """
    try:
        with open(json_file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        # 이미지 해상도 확인
        resolution = ["416", "416"]
        # resolution = data.get("meta", {}).get("Resolution", "0x0").split('x')
        # if len(resolution) != 2:
        #     return
        img_width, img_height = int(resolution[0]), int(resolution[1])
        if img_width == 0 or img_height == 0:
            return
        

        # 어노테이션 정보 추출
        annotations = data.get("annotations", {}).get("Bbox Annotation", {})
        boxes = annotations.get("Box", [])
        
        yolo_data = []

        for box in boxes:
            category = box.get("category_name", "")
            if category not in TARGET_CLASSES:
                continue  # 불필요한 클래스는 제외

            class_id = 0  # illegal_parking으로 통합
            x, y, w, h = box['x'], box['y'], box['w'], box['h']
            x_center = (x + w / 2) / img_width
            y_center = (y + h / 2) / img_height
            width_norm = w / img_width
            height_norm = h / img_height

            yolo_data.append(f"{class_id} {x_center:.6f} {y_center:.6f} {width_norm:.6f} {height_norm:.6f}")

        # 파일명 변환 및 저장
        base_filename = os.path.basename(json_file_path)
        txt_filename = os.path.splitext(base_filename)[0] + ".txt"
        txt_path = os.path.join(output_dir, txt_filename)

        with open(txt_path, 'w') as f:
            f.write("\n".join(yolo_data) if yolo_data else "")  # 박스 없으면 빈 파일

    except Exception as e:
        print(f"Error processing {json_file_path}: {e}")

def process_dataset(dataset_base_path):
    """
    annotations/train, annotations/val → labels/train, labels/val로 YOLO 포맷 변환
    """
    for split in ["train", "val"]:
        json_dir = os.path.join(dataset_base_path, "annotations", split)
        output_dir = os.path.join(dataset_base_path, "labels", split)

        if not os.path.exists(json_dir):
            print(f"[!] Not found: {json_dir}")
            continue

        os.makedirs(output_dir, exist_ok=True)
        json_files = glob(os.path.join(json_dir, "*.json"))
        print(f"[{split}] {len(json_files)}개의 JSON 파일을 변환합니다.")

        for json_file in tqdm(json_files, desc=f"[{split}] converting"):
            convert_to_yolo(json_file, output_dir)

        print(f"[✓] {split} 변환 완료 → {output_dir}")

if __name__ == '__main__':
    # 커스텀 데이터셋 루트 경로 설정
    dataset_base_path = "C:/Users/chobh/Desktop/bigProject/Data/oneclass_illegal_parking_dataset"
    process_dataset(dataset_base_path)
