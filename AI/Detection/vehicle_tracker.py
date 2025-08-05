import re
from collections import defaultdict
from pathlib import Path
import os
import time
import base64
import argparse
import numpy as np
import cv2
import requests
from urllib.parse import urlparse
from ultralytics import YOLO


def safe_imread(p):
    img = cv2.imread(p)
    if img is not None:
        return img
    with open(p, "rb") as f:
        buf = np.frombuffer(f.read(), np.uint8)
    return cv2.imdecode(buf, cv2.IMREAD_COLOR)


class FrameProvider:
    @staticmethod
    def from_source(src, poll=0.1, tout=5, hdr=None, fps=30):
        if isinstance(src, int) or (isinstance(src, str) and src.isdigit()):
            return WebcamProvider(int(src))
        if os.path.isfile(src):
            return FileProvider(src)
        if os.path.isdir(src):
            return DirSeqProvider(src, fps)
        scheme = urlparse(str(src)).scheme.lower()
        if scheme == "rtsp" or src.endswith((".mjpg", ".mjpeg", ".stream")):
            return WebcamProvider(src)
        if scheme in ("http", "https"):
            return APISnapshotProvider(src, poll, tout, hdr or {})
        raise ValueError(f"[FrameProvider] Unsupported source: {src}")


class WebcamProvider(FrameProvider):
    def __init__(self, src):
        self.cap = cv2.VideoCapture(src)
        if not self.cap.isOpened():
            raise IOError(f"Cannot open stream: {src}")

    def read(self):
        return self.cap.read()

    def release(self):
        self.cap.release()


class FileProvider(FrameProvider):
    def __init__(self, path):
        self.cap = cv2.VideoCapture(str(path))
        if not self.cap.isOpened():
            raise IOError(f"Cannot open video file: {path}")

    def read(self):
        return self.cap.read()

    def release(self):
        self.cap.release()


class DirSeqProvider(FrameProvider):
    SUP = {".jpg", ".jpeg", ".png", ".bmp"}

    def __init__(self, folder, fps):
        pat = re.compile(r'(\d+)')

        def natural_key(x):
            return [int(t) if t.isdigit() else t.lower()
                    for t in pat.split(Path(x).name)]

        self.files = sorted(
            [str(Path(folder) / f) for f in os.listdir(folder)
             if Path(f).suffix.lower() in self.SUP],
            key=natural_key
        )
        if not self.files:
            raise ValueError(f"[DirSeq] No images in {folder}")
        self.idx, self.delay, self.prev = 0, 1.0 / fps, 0.0

    def read(self):
        if self.idx >= len(self.files):
            return False, None
        wait = self.delay - (time.time() - self.prev)
        if wait > 0:
            time.sleep(wait)
        self.prev = time.time()
        img = safe_imread(self.files[self.idx])
        self.idx += 1
        return img is not None, img

    def release(self):
        pass


class APISnapshotProvider(FrameProvider):
    def __init__(self, url, poll, timeout, headers):
        self.url, self.dt, self.tout, self.hdr = url, poll, timeout, headers
        self.last = 0.0

    def read(self):
        gap = self.dt - (time.time() - self.last)
        if gap > 0:
            time.sleep(gap)
        self.last = time.time()
        try:
            r = requests.get(self.url, timeout=self.tout, headers=self.hdr)
            r.raise_for_status()
            buf = (np.frombuffer(r.content, np.uint8) if
                   r.headers.get("content-type", "").startswith("image")
                   else np.frombuffer(base64.b64decode(r.json()["image"]), np.uint8))
            frame = cv2.imdecode(buf, cv2.IMREAD_COLOR)
            return frame is not None, frame
        except Exception as e:
            print("[API]", e)
            return False, None

    def release(self):
        pass


def build_parser():
    p = argparse.ArgumentParser("YOLOv8 Vehicle Tracker with Stop-Time Detection")
    # p.add_argument("--source", required=True)
    # p.add_argument("--weights", required=True)
    p.add_argument("--source", default=r"C:\Users\chobh\Desktop\bigProject\Data\교통CCTV인공지능학습용데이터\1.Training\원천데이터\주간영상_01\낙천대APT앞(광주)_20210422102826")
    p.add_argument("--weights", default="C:/Users/chobh/Desktop/bigProject/Illegal-Parking-Detection/AI/Experiments/coco_custom_vehicle_seg/25.07.31_yolo11seg_gray_aug_from_pretrain_784_b8/weights/best.pt")
    p.add_argument("--classes", nargs="+", default=[])
    p.add_argument("--img_size", type=int, default=640)
    p.add_argument("--conf_thres", type=float, default=0.25)
    p.add_argument("--iou_thres", type=float, default=0.45)
    p.add_argument("--device", default="cuda")
    p.add_argument("--t_stop", type=float, default=10.0)
    p.add_argument("--move_tol", type=float, default=5.0)
    p.add_argument("--show", action="store_true")
    p.add_argument("--fps", type=int, default=30)
    p.add_argument("--poll_interval", type=float, default=0.1)
    p.add_argument("--api_timeout", type=float, default=5)
    p.add_argument("--api_header", action="append")
    return p


def header_dict(lst):
    d = {}
    if lst:
        for h in lst:
            if ":" in h:
                k, v = h.split(":", 1)
                d[k.strip()] = v.strip()
    return d


def main():
    args = build_parser().parse_args()
    allowed = {int(x) for s in args.classes for x in s.split(",") if x.strip().isdigit()}
    provider = FrameProvider.from_source(args.source, args.poll_interval,
                                         args.api_timeout, header_dict(args.api_header), args.fps)

    model = YOLO(args.weights, task="detect").to(args.device)
    tracks = defaultdict(lambda: dict(last=None, last_t=0.0, stop=False))

    try:
        while True:
            ret, frame = provider.read()
            if not ret:
                break
            now = time.time()
            res = model.track(frame, imgsz=args.img_size,
                              conf=args.conf_thres, iou=args.iou_thres,
                              device=args.device, persist=True, verbose=False)[0]

            if res.boxes.id is not None:
                ids = res.boxes.id.cpu().numpy().astype(int)
                for i, box in enumerate(res.boxes):
                    tid = ids[i]
                    cls_id = int(box.cls)
                    if allowed and cls_id not in allowed:
                        continue
                    # x1, y1, x2, y2 = map(float, box.xyxy)
                    x1, y1, x2, y2 = box.xyxy[0].tolist()
                    cx, cy = (x1 + x2) / 2, (y1 + y2) / 2
                    cur = np.array([cx, cy])

                    tk = tracks[tid]
                    if tk["last"] is None:
                        tk["last"], tk["last_t"] = cur, now
                    else:
                        if np.linalg.norm(cur - tk["last"]) < args.move_tol:
                            if not tk["stop"] and (now - tk["last_t"]) >= args.t_stop:
                                tk["stop"] = True
                                print(f"[정차] ID {tid}  ≥ {args.t_stop}s")
                        else:
                            tk["last_t"], tk["stop"] = now, False
                        tk["last"] = cur

                    color = (0, 0, 255) if tk["stop"] else (0, 255, 0)
                    cv2.rectangle(frame, (int(x1), int(y1)), (int(x2), int(y2)), color, 2)
                    cv2.putText(frame, f"ID {tid}", (int(x1), int(y1) - 10),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)

            if args.show:
                cv2.imshow("Tracking", frame)
                if cv2.waitKey(1) & 0xFF == ord('q'):
                    break

    finally:
        provider.release()
        try:
            if args.show:
                cv2.destroyAllWindows()
        except cv2.error:
            pass

if __name__ == "__main__":
    main()
