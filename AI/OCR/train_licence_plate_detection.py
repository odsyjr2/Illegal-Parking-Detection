import argparse
from ultralytics import YOLO

def main():
    #  Load a model
    model = YOLO("yolo11n.pt")  # load a pretrained model (recommended for training)

    # results = model.train(
    #     data='coco.yaml',
    #     epochs=1,
    #     imgsz=640
    # )
    
    # Train the model
    results = model.train(
        data="C:/Users/chobh/Desktop/bigProject/Data/License Plate Recognition.v11i.yolov11/data.yaml", 
        epochs=100, 
        batch=16,
        imgsz=640,
        device=0,
        project="../Experiments/license_plate_detection_yolo11",
        name="25.08.05",
        seed=42,
        multi_scale=True,

        hsv_h=0.015, #defult
        hsv_s=0.7, #defult
        hsv_v=0.4,  #defult
        degrees=0.0, #defult
        translate=0.1, #defult
        scale=0.5, #default
        shear=0.0, #defult
        perspective=0.0, #default
        flipud=0.0, #defult
        fliplr=0.5, #defult
        bgr=0.0, #default
        mosaic=1.0, #defult
        mixup=0.1,
        cutmix=0.0, #default
        )




    # resume version
    # model = YOLO("./../Experiments/lane_violation_seg/25.08.05/weights/last.pt")

    # results = model.train(resume=True)
if __name__ == "__main__":
    main()
