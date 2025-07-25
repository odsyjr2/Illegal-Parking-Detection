import os
import json
import glob

# 통합할 원본 클래스 이름들(추가적으로 다른 class가 있다면 여기서 필터링 가능)
ALLOWED_CATEGORIES = [
    "불법주정차SUV(낮)",
    "불법주정차SUV(밤)",
    "불법주정차승용차(낮)",
    "불법주정차승용차(밤)"
]
CATEGORY_MAP = {c: 0 for c in ALLOWED_CATEGORIES}  # 모두 vehicle로 통합

def convert_bbox_to_yolo(bbox, img_w, img_h):
    """
    JSON bbox(x, y, w, h) → YOLO format (x_center, y_center, w, h), normalized
    """
    x, y, w, h = bbox['x'], bbox['y'], bbox['w'], bbox['h']
    x_center = (x + w/2) / img_w
    y_center = (y + h/2) / img_h
    w_norm = w / img_w
    h_norm = h / img_h
    return [x_center, y_center, w_norm, h_norm]

def parse_resolution(res_str):
    # "1920x1080" → (1920, 1080)
    try:
        w, h = map(int, res_str.split('x'))
        return w, h
    except:
        return None, None

def json_to_yolo(json_path, idx=None, total=None):
    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    meta = data.get('meta', {})
    ann = data.get('annotations', {}).get('Bbox Annotation', {})
    boxes = ann.get('Box', [])
    resolution = meta.get('Resolution', '')
    img_w, img_h = parse_resolution(resolution)
    if img_w is None or img_h is None:
        print(f"[WARN] 이미지 해상도 정보 없음: {json_path}")
        return

    yolo_lines = []
    for bbox in boxes:
        category_name = bbox.get('category_name', '')
        if category_name not in CATEGORY_MAP:
            print(f"[WARN] 알 수 없는 클래스: {category_name} ({json_path}) -> vehicle로 처리")
        class_id = 0  # 무조건 vehicle로 통합
        yolo_box = convert_bbox_to_yolo(bbox, img_w, img_h)
        line = f"{class_id} {' '.join([f'{x:.6f}' for x in yolo_box])}"
        yolo_lines.append(line)
        print(f"  └─ [{category_name}] → [vehicle] (bbox 변환 완료)")

    # 저장 경로: json과 동일 폴더, 파일명은 이미지와 동일하게(jpg→txt)
    img_name = ann.get('atchOrgFileName', '').replace('.jpg', '.txt')
    if not img_name:
        img_name = os.path.splitext(os.path.basename(json_path))[0] + '.txt'
    txt_save_path = os.path.join(os.path.dirname(json_path), img_name)
    with open(txt_save_path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(yolo_lines))
    if idx is not None and total is not None:
        print(f"[{idx+1}/{total}] Saved: {txt_save_path}")
    else:
        print(f"[INFO] Saved: {txt_save_path}")

def convert_folder(root_dir):
    # 모든 하위 폴더의 .json 파일을 찾음
    json_files = glob.glob(os.path.join(root_dir, '**', '*.json'), recursive=True)
    total = len(json_files)
    print(f"[INFO] 총 json 파일: {total}개 변환 시작")
    for idx, json_path in enumerate(json_files):
        try:
            print(f"\n[{idx+1}/{total}] 변환 중: {json_path}")
            json_to_yolo(json_path, idx, total)
        except Exception as e:
            print(f"[ERROR] {json_path}: {e}")

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--root', type=str, required=True,
                        help='라벨링 데이터(json) 최상위 폴더 경로 (예: 01.데이터/1.Training/라벨링데이터/TL3/불법주정차/)')
    args = parser.parse_args()

    convert_folder(args.root)
