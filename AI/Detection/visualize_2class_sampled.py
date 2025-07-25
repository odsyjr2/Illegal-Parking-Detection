import os
import cv2
import matplotlib.pyplot as plt

# 클래스 정의
CLASS_NAMES = {0: 'normal', 1: 'illegal_parking'}
CLASS_COLORS = {0: (0, 255, 0), 1: (255, 0, 0)}  # BGR

def draw_boxes(image, label_path):
    if not os.path.exists(label_path):
        print(f"⚠️ 라벨 없음: {label_path}")
        return image.copy()

    h, w = image.shape[:2]
    vis_image = image.copy()

    with open(label_path, 'r') as f:
        for line in f.readlines():
            cls, cx, cy, bw, bh = map(float, line.strip().split())
            x1 = int((cx - bw / 2) * w)
            y1 = int((cy - bh / 2) * h)
            x2 = int((cx + bw / 2) * w)
            y2 = int((cy + bh / 2) * h)

            color = CLASS_COLORS.get(int(cls), (0, 255, 255))
            name = CLASS_NAMES.get(int(cls), 'unknown')
            cv2.rectangle(vis_image, (x1, y1), (x2, y2), color, 2)
            cv2.putText(vis_image, name, (x1, y1 - 5),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)
    return vis_image

def visualize_all_val_images(base_image_dir, base_label_dir, save_dir=None):
    for time in ['day', 'night']:
        image_dir = os.path.join(base_image_dir, time)
        label_dir = os.path.join(base_label_dir, time)

        print(f"\n🌓 전체 시각화: {time.upper()}")
        image_files = [f for f in os.listdir(image_dir) if f.lower().endswith(('.jpg', '.png'))]

        # 저장 디렉토리 준비
        if save_dir:
            time_save_dir = os.path.join(save_dir, time)
            os.makedirs(time_save_dir, exist_ok=True)

        for file in image_files:
            img_path = os.path.join(image_dir, file)
            label_path = os.path.join(label_dir, os.path.splitext(file)[0] + ".txt")

            image = cv2.imread(img_path)
            if image is None:
                print(f"⚠️ 이미지 불러오기 실패: {img_path}")
                continue

            image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
            image_with_boxes = draw_boxes(image, label_path)
            image_with_boxes_rgb = cv2.cvtColor(image_with_boxes, cv2.COLOR_BGR2RGB)

            # 시각화 생성
            fig, axs = plt.subplots(1, 2, figsize=(14, 6))
            fig.suptitle(f"{time.upper()} - {file}", fontsize=14)

            axs[0].imshow(image_rgb)
            axs[0].set_title("Original")
            axs[0].axis('off')

            axs[1].imshow(image_with_boxes_rgb)
            axs[1].set_title("With Labels")
            axs[1].axis('off')

            plt.tight_layout()

            if save_dir:
                save_path = os.path.join(save_dir, time, os.path.splitext(file)[0] + ".png")
                fig.savefig(save_path)
                plt.close(fig)
                print(f"💾 저장 완료: {save_path}")
            else:
                plt.show()

# 경로 설정
BASE_IMAGE_DIR = 'C:/Users/chobh/Desktop/bigProject/Data/oneclass_illegal_parking_dataset_intersect/images/val'
BASE_LABEL_DIR = 'C:/Users/chobh/Desktop/bigProject/Data/oneclass_illegal_parking_dataset_intersect/two_class_pseudo_label/val'
SAVE_DIR = 'C:/Users/chobh/Desktop/bigProject/Data/oneclass_illegal_parking_dataset_intersect/visualize_two_class_val'  # None이면 저장하지 않음

# 실행
visualize_all_val_images(BASE_IMAGE_DIR, BASE_LABEL_DIR, save_dir=SAVE_DIR)
