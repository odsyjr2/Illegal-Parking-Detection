import os
import argparse
import shutil
from pathlib import Path
from tqdm import tqdm

COCO_CLASSES = {
    2: 'car', 3: 'motorcycle', 5: 'bus', 7: 'truck',
    9: 'traffic light', 10: 'fire hydrant', 11: 'stop sign', 12: 'parking meter'
}

def parse_args():
    parser = argparse.ArgumentParser(description="Convert filtered COCO to new custom dataset")
    parser.add_argument('--input_labels', default='../../../Data/coco/labels')
    parser.add_argument('--input_images', default='../../../Data/coco/images')
    parser.add_argument('--output_root', default='../../../Data/coco_custom_vehicle_seg')
    parser.add_argument('--classes', nargs='+', type=int, default=[2, 3, 5, 7])
    return parser.parse_args()

def process_split(split, input_labels, input_images, output_root, target_classes, id_remap):
    input_label_dir = Path(input_labels) / split
    input_image_dir = Path(input_images) / split
    output_label_dir = Path(output_root) / 'labels' / split
    output_image_dir = Path(output_root) / 'images' / split
    list_txt_path = Path(output_root) / f"{split}.txt"

    output_label_dir.mkdir(parents=True, exist_ok=True)
    output_image_dir.mkdir(parents=True, exist_ok=True)

    kept = 0
    label_files = list(input_label_dir.glob("*.txt"))

    with open(list_txt_path, 'w') as list_file:
        for label_file in tqdm(label_files, desc=f"[{split}] filtering"):
            with open(label_file, 'r') as f:
                lines = f.readlines()

            new_lines = []
            for line in lines:
                parts = line.strip().split()
                if not parts:
                    continue
                cid = int(parts[0])
                if cid in target_classes:
                    new_id = id_remap[cid]
                    new_line = ' '.join([str(new_id)] + parts[1:])
                    new_lines.append(new_line)

            if new_lines:
                # write new label file
                new_label_path = output_label_dir / label_file.name
                with open(new_label_path, 'w') as f:
                    f.write('\n'.join(new_lines))

                # copy image file
                image_file = label_file.stem + ".jpg"
                src_img = input_image_dir / image_file
                dst_img = output_image_dir / image_file
                if src_img.exists():
                    shutil.copyfile(src_img, dst_img)
                else:
                    print(f"[경고] 이미지 누락: {src_img}")
                    continue

                # write relative path to list file
                list_file.write(f"./images/{split}/{image_file}\n")
                kept += 1

    print(f"[{split}] 포함된 이미지 수: {kept}개 → {list_txt_path}")

def main():
    args = parse_args()

    print("🎯 선택한 클래스 (COCO ID):", args.classes)
    print("📁 출력 폴더:", args.output_root)

    id_remap = {cid: i for i, cid in enumerate(args.classes)}  # COCO ID → 0부터 재매핑

    for split in ['train2017', 'val2017']:
        process_split(
            split=split,
            input_labels=args.input_labels,
            input_images=args.input_images,
            output_root=args.output_root,
            target_classes=args.classes,
            id_remap=id_remap
        )

    print("✅ 변환 완료!")

if __name__ == "__main__":
    main()