import argparse
from ultralytics import YOLO

def main():
    #  Load a model
    model = YOLO("yolo11n-seg.pt")  # load a pretrained model (recommended for training)
    
    # results = model.train(
    #     data='coco.yaml',
    #     epochs=1,
    #     imgsz=640
    # )
    
    # Train the model
    results = model.train(
        data="coco_custom.yaml", 
        epochs=100, 
        batch=16,
        imgsz=640,
        device=0,
        project="../Experiments/coco_custom_vehicle_seg",
        name="25.07.28_gray_aug",
        seed=42,
        multi_scale=True,

        hsv_h=0.5, 
        hsv_s=1.0, 
        hsv_v=0.6, 
        degrees=0.0, #defult
        translate=0.1, #defult
        scale=0.5,
        shear=0.0, #defult
        perspective=0.0005,
        flipud=0.0, #defult
        fliplr=0.5, #defult
        bgr=0.3,
        mosaic=0.5, #defult
        # mixup=0.1,
        # cutmix=0.1,
        )




    # # resume version
    # model = YOLO("../Experiments/illegal_parking_union_det/25.07.24/weights/last.pt")

    # results = model.train(resume=True)
if __name__ == "__main__":
    main()
