import os
import json
import shutil
from tqdm import tqdm

def convert_json_to_txt(original_root, output_root):
    """
    original_root: 원본 데이터셋 경로 (예: C:/.../licence_plate_original/Training)
    output_root  : 변환된 데이터셋 저장 경로
    """

    # gt.txt 저장 경로
    gt_path = os.path.join(output_root, "gt.txt")
    test_dir = os.path.join(output_root, "test")

    # test 폴더 생성
    os.makedirs(test_dir, exist_ok=True)

    # annotations, images 경로
    ann_dir = os.path.join(original_root, "annotations")
    img_dir = os.path.join(original_root, "images")

    # gt.txt 작성
    with open(gt_path, "w", encoding="utf-8") as gt_file:
        for ann_file in tqdm(os.listdir(ann_dir), desc=f"Processing {original_root}"):
            if not ann_file.lower().endswith(".json"):
                continue

            ann_path = os.path.join(ann_dir, ann_file)
            with open(ann_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            img_name = data["imagePath"]
            label = data["value"]

            src_img_path = os.path.join(img_dir, img_name)
            if not os.path.exists(src_img_path):
                print(f"[WARN] 이미지 없음: {src_img_path}")
                continue

            # test 폴더 안에 복사할 파일명 (word_번호.png)
            file_ext = os.path.splitext(img_name)[1]
            new_img_name = f"word_{len(os.listdir(test_dir))+1}{file_ext}"
            dst_img_path = os.path.join(test_dir, new_img_name)

            # 이미지 복사 (한글 경로도 안전하게 처리)
            shutil.copy(src_img_path, dst_img_path)

            # gt.txt에 경로와 라벨 기록
            gt_file.write(f"test/{new_img_name}\t{label}\n")

    print(f"[INFO] 변환 완료: {gt_path}, 이미지 폴더: {test_dir}")

def main():
    # 원본 데이터셋 루트
    base_dir = r"C:/Users/chobh/Desktop/bigProject/Data/licence_plate_original"

    # Training 변환
    train_input = os.path.join(base_dir, "Training")
    train_output = os.path.join(base_dir, "training_for_lmdb")
    convert_json_to_txt(train_input, train_output)

    # Validation 변환
    val_input = os.path.join(base_dir, "Validation")
    val_output = os.path.join(base_dir, "validation_for_lmdb")
    convert_json_to_txt(val_input, val_output)

if __name__ == "__main__":
    main()
