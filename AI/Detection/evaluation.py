import argparse
from ultralytics import YOLO
from pathlib import Path

def parse_args():
    parser = argparse.ArgumentParser(description="Evaluate YOLOv8 model on custom dataset")
    parser.add_argument('--weights', type=str, default='runs/detect/train/weights/best.pt', help='Path to trained model weights')
    parser.add_argument('--data', type=str, default='C:/Users/chobh/Desktop/bigProject/Data/coco_custom_vehicle_seg/data.yaml', help='Path to dataset YAML file')
    parser.add_argument('--imgsz', type=int, default=640, help='Image size for inference')
    parser.add_argument('--device', type=str, default='0', help='CUDA device (e.g., 0 or cpu)')
    return parser.parse_args()

def main():
    args = parse_args()

    # 모델 로드
    print(f"🔍 모델 로딩 중: {args.weights}")
    model = YOLO(args.weights)

    # 평가 수행
    print(f"📊 평가 시작 - 데이터셋: {args.data}")
    metrics = model.val(
        data=args.data,
        imgsz=args.imgsz,
        device=args.device,
        split='val'
    )

    # 평가 결과 출력
    print("\n📈 평가 결과 요약:")
    for k, v in metrics.results_dict.items():
        print(f"{k:20s}: {v:.4f}")

    # 상세 저장 (선택사항)
    result_path = Path(args.weights).parent / "eval_metrics.txt"
    with open(result_path, 'w') as f:
        for k, v in metrics.results_dict.items():
            f.write(f"{k}: {v:.4f}\n")
    print(f"\n✅ 결과 저장 완료: {result_path}")

if __name__ == "__main__":
    main()
