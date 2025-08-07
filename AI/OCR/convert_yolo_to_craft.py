import os, glob, cv2
from tqdm import tqdm

def convert_split(split, dst_split):
    yolo_labels_dir = f'C:/Users/chobh/Desktop/bigProject/Data/License Plate Recognition.v11i.yolov11/{split}/labels'
    images_dir = f'C:/Users/chobh/Desktop/bigProject/Data/License Plate Recognition.v11i.yolov11/{split}/images'
    output_img_dir = f'C:/Users/chobh/Desktop/bigProject/Data/Licence_Plate_Recoginitiion_CRAFT/ch4_{dst_split}_images'
    output_gt_dir = f'C:/Users/chobh/Desktop/bigProject/Data/Licence_Plate_Recoginitiion_CRAFT/ch4_{dst_split}_localization_transcription_gt'

    os.makedirs(output_img_dir, exist_ok=True)
    os.makedirs(output_gt_dir, exist_ok=True)

    for label_path in tqdm(glob.glob(os.path.join(yolo_labels_dir, '*.txt'))):
        image_path = os.path.join(images_dir, os.path.basename(label_path).replace('.txt', '.jpg'))
        img = cv2.imread(image_path)
        if img is None:
            continue
        h, w = img.shape[:2]

        with open(label_path, 'r') as f:
            lines = f.readlines()

        gt_lines = []
        for line in lines:
            cls, xc, yc, bw, bh = map(float, line.strip().split())

            # 좌표 변환 후 int 변환
            x1 = int((xc - bw/2) * w)
            y1 = int((yc - bh/2) * h)
            x2 = int((xc + bw/2) * w)
            y2 = y1
            x3 = x2
            y3 = int((yc + bh/2) * h)
            x4 = x1
            y4 = y3

            gt_lines.append(f"{x1},{y1},{x2},{y2},{x3},{y3},{x4},{y4},###,plate\n")

        cv2.imwrite(os.path.join(output_img_dir, os.path.basename(image_path)), img)
        with open(os.path.join(output_gt_dir, f'gt_{os.path.basename(label_path)}'), 'w') as out_f:
            out_f.writelines(gt_lines)

for split, dst_split in {'train':'training', 'valid':'test'}.items():
    convert_split(split, dst_split)
