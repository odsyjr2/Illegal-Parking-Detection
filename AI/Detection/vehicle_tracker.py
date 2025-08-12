#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
YOLOv8 + BYTETracker + Stop-time filter
  · DirSeqProvider : 이미지 폴더를 FPS 기반 스트림으로 재생
  · --classes 0 1 2 : 원하는 클래스만 시각화
  · stationary(≥t_stop) → 빨간색, 이동 중 → 초록색
"""

import os, time, base64, argparse, re
from pathlib import Path
from urllib.parse import urlparse
from collections import defaultdict
import cv2, numpy as np, requests
from ultralytics import YOLO

# ────────── 유니코드 안전 입출력 ──────────
def safe_imread(p):
    img = cv2.imread(p)
    if img is not None:
        return img
    with open(p, "rb") as f:
        buf = np.frombuffer(f.read(), np.uint8)
    return cv2.imdecode(buf, cv2.IMREAD_COLOR)

def safe_videocapture(p):
    cap = cv2.VideoCapture(str(p))
    return cap if cap.isOpened() else cv2.VideoCapture(Path(p).as_uri())

# ────────── FrameProvider 계층 ──────────
class FrameProvider:
    """read() → (ret, BGR ndarray), release()"""
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
            return WebcamProvider(src)               # RTSP / MJPEG
        if scheme in ("http", "https"):
            return APISnapshotProvider(src, poll, tout, hdr or {})
        raise ValueError(f"[FrameProvider] 지원하지 않는 source: {src}")

class WebcamProvider(FrameProvider):
    def __init__(self, src):                        # webcam index / RTSP
        self.cap = cv2.VideoCapture(src)
        if not self.cap.isOpened():
            raise IOError(f"스트림을 열 수 없음: {src}")
    def read(self):    return self.cap.read()
    def release(self): self.cap.release()

class FileProvider(FrameProvider):
    def __init__(self, path):
        self.cap = safe_videocapture(path)
        if not self.cap.isOpened():
            raise IOError(f"비디오 파일을 열 수 없음: {path}")
    def read(self):    return self.cap.read()
    def release(self): self.cap.release()

class DirSeqProvider(FrameProvider):
    """폴더 내 *.jpg·png 등을 자연 정렬 → FPS 간격으로 재생"""
    SUP = {".jpg", ".jpeg", ".png", ".bmp"}

    def __init__(self, folder, fps):
        pat = re.compile(r'(\d+)')
        def natural_key(x):                          # 001.jpg < 10.jpg
            return [int(t) if t.isdigit() else t.lower()
                    for t in pat.split(Path(x).name)]
        self.files = sorted(
            [str(Path(folder)/f) for f in os.listdir(folder)
             if Path(f).suffix.lower() in self.SUP],
            key=natural_key
        )
        if not self.files:
            raise ValueError(f"[DirSeq] {folder} 에 이미지가 없습니다.")
        self.idx, self.delay, self.prev = 0, 1.0/fps, 0.0

    def read(self):
        if self.idx >= len(self.files):
            return False, None
        # FPS 유지
        wait = self.delay - (time.time() - self.prev)
        if wait > 0:  time.sleep(wait)
        self.prev = time.time()
        img = safe_imread(self.files[self.idx])
        self.idx += 1
        return img is not None, img
    def release(self): pass

class APISnapshotProvider(FrameProvider):
    def __init__(self, url, poll, timeout, headers):
        self.url, self.dt, self.tout, self.hdr = url, poll, timeout, headers
        self.last = 0.0
    def read(self):
        gap = self.dt - (time.time() - self.last)
        if gap > 0: time.sleep(gap)
        self.last = time.time()
        try:
            r = requests.get(self.url, timeout=self.tout, headers=self.hdr)
            r.raise_for_status()
            buf = (np.frombuffer(r.content, np.uint8) if
                   r.headers.get("content-type","").startswith("image")
                   else np.frombuffer(base64.b64decode(r.json()["image"]), np.uint8))
            frame = cv2.imdecode(buf, cv2.IMREAD_COLOR)
            return frame is not None, frame
        except Exception as e:
            print("[API]", e); return False, None
    def release(self): pass

# ────────── CLI 파서 ──────────
def build_parser():
    p = argparse.ArgumentParser("YOLOv8 차량 추적 · 정차 판정")
    p.add_argument("--source",  required=True, help="입력 소스 (폴더, 파일, RTSP 등)")
    p.add_argument("--weights", required=True, help="YOLO 가중치 *.pt")
    p.add_argument("--classes", nargs="+", default=[],
                   help="표시할 클래스 번호 (공백/쉼표 구분), 비우면 전체")
    p.add_argument("--img_size",  type=int,   default=640,  help="YOLO 입력 해상도")
    p.add_argument("--conf_thres",type=float, default=0.25, help="confidence 임계값")
    p.add_argument("--iou_thres", type=float, default=0.45, help="NMS IoU 임계값")
    p.add_argument("--device",    default="cuda",           help="cuda / cpu / 0,1…")
    p.add_argument("--t_stop",    type=float, default=10.0, help="정차 판정 시간(초)")
    p.add_argument("--move_tol",  type=float, default=5.0,  help="이동 허용 픽셀")
    p.add_argument("--show",      action="store_true",      help="창에 실시간 표시")
    p.add_argument("--fps",       type=int,   default=30,   help="폴더 재생 FPS")
    p.add_argument("--poll_interval",type=float,default=0.1,help="REST 폴링 간격")
    p.add_argument("--api_timeout",  type=float,default=5,  help="REST 타임아웃")
    p.add_argument("--api_header",   action="append",       help='"Key: Value" 반복')
    return p

def header_dict(lst):
    d={}; 
    if lst:
        for h in lst:
            if ":" in h:
                k,v=h.split(":",1); d[k.strip()]=v.strip()
    return d

# ────────── 메인 ──────────
def main():
    args = build_parser().parse_args()

    allowed = {int(x) for s in args.classes for x in s.split(",") if x.strip().isdigit()}
    provider = FrameProvider.from_source(
        args.source, args.poll_interval, args.api_timeout,
        header_dict(args.api_header), args.fps
    )

    model = YOLO(args.weights, task="detect").to(args.device)
    tracks = defaultdict(lambda: dict(last=None, last_t=0.0, stop=False))

    try:
        while True:
            ret, frame = provider.read()
            if not ret: break
            now = time.time()

            res = model.track(frame, imgsz=args.img_size,
                              conf=args.conf_thres, iou=args.iou_thres,
                              device=args.device, persist=True,
                              verbose=False)[0]

            for box, tid in zip(res.boxes, res.boxes.id or []):
                if tid is None: continue
                tid = int(tid)
                cls_id = int(box.cls)
                if allowed and cls_id not in allowed:
                    continue

                x1,y1,x2,y2 = map(float, box.xyxy)
                cx, cy = (x1+x2)/2, (y1+y2)/2
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

                color = (0,0,255) if tk["stop"] else (0,255,0)
                cv2.rectangle(frame, (int(x1),int(y1)), (int(x2),int(y2)), color, 2)
                cv2.putText(frame, f"ID {tid}", (int(x1),int(y1)-10),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)

            if args.show:
                cv2.imshow("Tracking", frame)
                if cv2.waitKey(1) & 0xFF == ord('q'):
                    break

    finally:
        provider.release()
        # GUI 없는 환경에서는 destroyAllWindows 가 실패할 수 있음
        try:
            if args.show:
                cv2.destroyAllWindows()
        except cv2.error:
            pass

if __name__ == "__main__":
    main()
