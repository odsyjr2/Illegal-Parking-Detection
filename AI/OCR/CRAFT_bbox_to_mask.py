import os
import cv2
import numpy as np
import argparse


def convert_split(root_dir, split, out_dir):
    img_dir = os.path.join(root_dir, split, 'images')
    lbl_dir = os.path.join(root_dir, split, 'labels')
    mask_dir = os.path.join(out_dir, split, 'masks')
    os.makedirs(mask_dir, exist_ok=True)

    for fname in os.listdir(lbl_dir):
        if not fname.endswith('.txt'):
            continue
        label_path = os.path.join(lbl_dir, fname)
        img_name = fname.replace('.txt', '.jpg')
        img_path = os.path.join(img_dir, img_name)
        if not os.path.exists(img_path):
            # try png
            img_name = fname.replace('.txt', '.png')
            img_path = os.path.join(img_dir, img_name)
            if not os.path.exists(img_path):
                print(f"Image not found for label {label_path}, skipping.")
                continue

        # read image to get dimensions
        img = cv2.imread(img_path)
        if img is None:
            print(f"Failed to load image {img_path}, skipping.")
            continue
        h, w = img.shape[:2]

        # create blank mask
        mask = np.zeros((h, w), dtype=np.uint8)

        # parse YOLO bbox and draw rectangle
        with open(label_path, 'r') as f:
            for line in f:
                parts = line.strip().split()
                if len(parts) != 5:
                    continue
                _, x_c, y_c, bw, bh = map(float, parts)
                x1 = int((x_c - bw/2) * w)
                y1 = int((y_c - bh/2) * h)
                x2 = int((x_c + bw/2) * w)
                y2 = int((y_c + bh/2) * h)
                # clamp
                x1, y1 = max(0, x1), max(0, y1)
                x2, y2 = min(w-1, x2), min(h-1, y2)
                cv2.rectangle(mask, (x1, y1), (x2, y2), 255, thickness=-1)

        # save mask as png
        mask_path = os.path.join(mask_dir, fname.replace('.txt', '.png'))
        cv2.imwrite(mask_path, mask)
        print(f"Saved mask: {mask_path}")


def main():
    parser = argparse.ArgumentParser(
        description='Convert YOLO bbox labels to binary masks for CRAFT training'
    )
    parser.add_argument(
        '--root', type=str, required=True,
        help='Path to License Plate Recognition.v11i.yolov11 directory'
    )
    parser.add_argument(
        '--out', type=str, required=True,
        help='Output directory for masks under splits'
    )
    args = parser.parse_args()

    for split in ['train', 'valid', 'test']:
        print(f"Processing split: {split}")
        convert_split(args.root, split, args.out)

    print("Conversion completed.")


if __name__ == '__main__':
    main()
