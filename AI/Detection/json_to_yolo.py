import json
import os
from glob import glob
from tqdm import tqdm

def convert_to_yolo(json_file_path, output_dir):
    """
    JSON 파일을 읽어 YOLO 포맷의 txt 파일로 변환합니다.
    """
    try:
        with open(json_file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        # 이미지 크기 정보 추출
        resolution = data.get("meta", {}).get("Resolution", "0x0").split('x')
        if len(resolution) != 2:
            # print(f"Skipping {json_file_path}: Invalid resolution format.")
            return
            
        img_width, img_height = int(resolution[0]), int(resolution[1])
        if img_width == 0 or img_height == 0:
            # print(f"Skipping {json_file_path}: Image width or height is zero.")
            return

        # 어노테이션 정보 추출
        annotations = data.get("annotations", {}).get("Bbox Annotation", {})
        boxes = annotations.get("Box", [])
        
        if not boxes:
            # Bounding Box가 없는 경우, 빈 txt 파일 생성
            base_filename = os.path.basename(json_file_path)
            txt_filename = os.path.splitext(base_filename)[0] + ".txt"
            open(os.path.join(output_dir, txt_filename), 'w').close()
            return

        yolo_data = []
        for box in boxes:
            # YOLO 포맷으로 변환
            # 현재는 단일 클래스(0)로 처리
            class_id = 0  
            x, y, w, h = box['x'], box['y'], box['w'], box['h']
            
            x_center = (x + w / 2) / img_width
            y_center = (y + h / 2) / img_height
            width_norm = w / img_width
            height_norm = h / img_height
            
            yolo_data.append(f"{class_id} {x_center:.6f} {y_center:.6f} {width_norm:.6f} {height_norm:.6f}")

        # YOLO 포맷으로 파일 저장
        base_filename = os.path.basename(json_file_path)
        txt_filename = os.path.splitext(base_filename)[0] + ".txt"
        
        with open(os.path.join(output_dir, txt_filename), 'w') as f:
            f.write("\n".join(yolo_data))

    except Exception as e:
        print(f"Error processing {json_file_path}: {e}")

def process_dataset(dataset_path):
    """
    'train'과 'val' 폴더에 대해 변환 작업을 수행합니다.
    """
    for split in ["train", "val"]:
        json_dir = os.path.join(dataset_path, split, "annotations")
        output_dir = os.path.join(dataset_path, split, "labels")

        if not os.path.exists(json_dir):
            print(f"Directory not found: {json_dir}")
            continue

        os.makedirs(output_dir, exist_ok=True)
        
        json_files = glob(os.path.join(json_dir, "*.json"))
        print(f"Found {len(json_files)} json files in {json_dir}")

        for json_file in tqdm(json_files, desc=f"Converting {split} JSONs to YOLO format"):
            convert_to_yolo(json_file, output_dir)
        
        print(f"Finished processing for {split} set. Labels are in {output_dir}")


if __name__ == '__main__':
    # custom_dataset 경로 설정
    root_path = "C:/Users/User/Project_Big"
    dataset_base_path = os.path.join(root_path, "custom_dataset")
    process_dataset(dataset_base_path)
