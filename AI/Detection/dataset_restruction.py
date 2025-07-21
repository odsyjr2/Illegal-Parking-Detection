import os
import shutil
import glob
import json
import argparse
from tqdm import tqdm

def move_files(src_root, dst_root, data_type, split_name):
    # Training/Validation에 따라 라벨/원천데이터 폴더명 분기
    if split_name == "train":
        label_path = "라벨링데이터/TL3/불법주정차"
        img_path = "원천데이터/TS3/불법주정차"
    else:  # val
        label_path = "라벨링데이터/VL3/불법주정차"
        img_path = "원천데이터/VS3/불법주정차"
    label_base = os.path.join(src_root, data_type, label_path)
    img_base = os.path.join(src_root, data_type, img_path)

    # 목적지 디렉토리 생성
    os.makedirs(os.path.join(dst_root, split_name, "images"), exist_ok=True)
    os.makedirs(os.path.join(dst_root, split_name, "annotations"), exist_ok=True)

    # 각 하위 클래스 폴더 탐색
    for class_dir in os.listdir(label_base):
        label_dir = os.path.join(label_base, class_dir)
        img_dir = os.path.join(img_base, class_dir)
        if not os.path.isdir(label_dir):
            continue

        json_files = glob.glob(f"{label_dir}/*.json")
        for json_file in tqdm(json_files, desc=f"{split_name}:{class_dir}", unit="file"):
            # 라벨 json 파싱
            with open(json_file, 'r', encoding='utf-8') as f:
                ann = json.load(f)
            
            if "annotations" not in ann or "Bbox Annotation" not in ann["annotations"]:
                print(f"Skipping {json_file} due to missing annotation key.")
                continue

            img_file = ann["annotations"]["Bbox Annotation"]["atchFileName"]
            src_img_path = os.path.join(img_dir, img_file)
            
            # 목적지 경로 설정
            dst_img_path = os.path.join(dst_root, split_name, "images", img_file)
            dst_json_path = os.path.join(dst_root, split_name, "annotations", f"{os.path.splitext(img_file)[0]}.json")

            # 이미지 복사
            if os.path.exists(src_img_path):
                shutil.copy2(src_img_path, dst_img_path)
            else:
                print(f"Image not found: {src_img_path}")

            # annotation 복사
            shutil.copy2(json_file, dst_json_path)

def main():
    parser = argparse.ArgumentParser(description="데이터셋 디렉터리 구조 개선 스크립트")
    parser.add_argument("--src", default="C:\Users\chobh\Desktop\빅프로젝트\Data\138.종합 민원 이미지 AI데이터\01.데이터", help="원본 데이터셋 루트 디렉터리 경로")
    parser.add_argument("--dst", default="C:\Users\chobh\Desktop\빅프로젝트\custom_dataset", help="새로 만들 디렉터리(타겟) 경로")
    args = parser.parse_args()

    # Training → train(TL3/TS3), Validation → val(VL3/VS3)
    move_files(args.src, args.dst, "1.Training", "train")
    move_files(args.src, args.dst, "2.Validation", "val")
    
    print(f"\n정리가 완료되었습니다!\n- 이미지: {args.dst}/(train|val)/images/\n- annotation json: {args.dst}/(train|val)/annotations/")

if __name__ == "__main__":
    main()