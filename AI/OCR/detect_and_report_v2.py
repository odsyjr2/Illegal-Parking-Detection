import cv2
from ultralytics import YOLO
import easyocr
import requests
import datetime
import argparse
import os
import json
import numpy as np
import threading
import time
import yaml


def load_config(config_path='config.yaml'):
    """Load configuration from a YAML file."""
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f)
    except FileNotFoundError:
        print(f"Error: Configuration file not found at {config_path}")
        return None
    except Exception as e:
        print(f"Error loading or parsing config file: {e}")
        return None

def load_models(config):
    """Load and return all AI models based on the provided configuration."""
    print("Loading models...")
    try:
        tracking_model = YOLO(config['models']['tracking_path'])
        parking_model = YOLO(config['models']['parking_path'])
        ocr_reader = easyocr.Reader(
            [config['models']['ocr']['language']],
            model_storage_directory=config['models']['ocr']['storage_directory'],
            gpu=True
        )
        models = {"tracking": tracking_model, "parking": parking_model, "ocr": ocr_reader}
        print("Models loaded successfully.")
        return models
    except Exception as e:
        print(f"Error loading models: {e}")
        return None

class CCTVStreamProcessor(threading.Thread):
    """A class to process a single CCTV stream in a separate thread."""

    def __init__(self, stream_info, context):
        """Initializes the CCTV Stream Processor thread.

        Args:
            stream_info (dict): A dictionary containing all information for a single CCTV stream,
                                such as id, source, location, and coordinates.
                                This acts as the unique 'job description' for this thread.
            context (dict): A dictionary containing shared resources and configurations to be used
                            across all threads. This includes:
                            - 'models': The loaded AI models (YOLO, EasyOCR).
                            - 'config': The global configuration loaded from config.yaml.
                            - 'eval_mode': A boolean flag for performance evaluation mode.
        """
        super().__init__()
        self.stream_info = stream_info
        self.context = context
        self.models = context['models']
        self.config = context['config']
        self.eval_mode = context['eval_mode']
        self.parking_tracker = {}
        self.window_name = f"CCTV: {self.stream_info['id']}"
        self.params = self.config['parameters']['parking_detection']

    def run(self):
        """Main loop to process video frames."""
        source = self.stream_info['source']
        if isinstance(source, str) and source.isdigit():
            source = int(source)

        print(f"[{self.stream_info['id']}] Starting processing for {source}")
        cap = cv2.VideoCapture(source)
        if not cap.isOpened():
            print(f"[{self.stream_info['id']}] Error: Could not open video source.")
            return

        fps = cap.get(cv2.CAP_PROP_FPS)
        if fps == 0: fps = 30

        while cap.isOpened():
            ret, frame = cap.read()
            if not ret: break

            processed_frame = self.process_frame(frame, fps)
            cv2.imshow(self.window_name, processed_frame)
            if cv2.waitKey(1) & 0xFF == ord('q'): break

        cap.release()
        cv2.destroyWindow(self.window_name)
        print(f"[{self.stream_info['id']}] Finished processing.")

    def process_frame(self, frame, fps):
        """Process a single frame for vehicle tracking and parking detection."""
        track_results = self.models['tracking'].track(frame, persist=True, classes=[2, 3, 5, 7])

        if track_results[0].boxes.id is not None:
            boxes, track_ids = track_results[0].boxes.xyxy.cpu(), track_results[0].boxes.id.cpu()
            current_tracked_ids = set(track_ids.numpy().astype(int))

            for box, track_id in zip(boxes, track_ids):
                self.update_parking_tracker(track_id.item(), box.numpy().astype(int))
                self.visualize_and_report(frame, track_id.item(), box.numpy().astype(int), fps)
            
            self.cleanup_disappeared_trackers(current_tracked_ids)
        
        return frame

    def update_parking_tracker(self, track_id, box):
        x1, y1, x2, y2 = box
        center_x, center_y = (x1 + x2) // 2, (y1 + y2) // 2
        if track_id not in self.parking_tracker:
            self.parking_tracker[track_id] = {'position': (center_x, center_y), 'frame_count': 1, 'reported': False}
        else:
            tracker = self.parking_tracker[track_id]
            distance = np.sqrt((center_x - tracker['position'][0])**2 + (center_y - tracker['position'][1])**2)
            if distance < self.params['movement_threshold_pixels']:
                tracker['frame_count'] += 1
            else:
                tracker['position'] = (center_x, center_y)
                tracker['frame_count'] = 1
                tracker['reported'] = False

    def visualize_and_report(self, frame, track_id, box, fps):
        tracker = self.parking_tracker[track_id]
        parking_duration = tracker['frame_count'] / fps
        x1, y1, x2, y2 = box
        color, label = (0, 255, 0), f"ID: {track_id}"

        if parking_duration > self.params['time_threshold_seconds']:
            color = (0, 255, 255)
            label += f" Parked: {parking_duration:.1f}s"
            vehicle_roi = frame[y1:y2, x1:x2]
            if vehicle_roi.size == 0: return

            parking_results = self.models['parking'](vehicle_roi, verbose=False)
            if any(len(r.boxes) > 0 for r in parking_results):
                color = (0, 0, 255)
                label += " [ILLEGAL]"
                if not tracker['reported']:
                    self.handle_illegal_detection(frame, box, track_id)
                    tracker['reported'] = True

        cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
        cv2.putText(frame, label, (x1, y1 - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)

    def cleanup_disappeared_trackers(self, current_tracked_ids):
        disappeared_ids = set(self.parking_tracker.keys()) - current_tracked_ids
        for track_id in disappeared_ids:
            del self.parking_tracker[track_id]

    def handle_illegal_detection(self, frame, box, track_id):
        cctv_id = self.stream_info['id']
        print(f"[{cctv_id}] Handling illegal detection for vehicle {track_id}. Preparing report...")
        x1, y1, x2, y2 = box
        vehicle_roi = frame[y1:y2, x1:x2]

        ocr_results = self.models['ocr'].readtext(vehicle_roi)
        license_plate = "Unknown"
        if ocr_results:
            best_result = max(ocr_results, key=lambda r: r[2])
            license_plate = best_result[1]
            print(f"[{cctv_id}] OCR Result: {license_plate} (Confidence: {best_result[2]:.2f})")

        timestamp = datetime.datetime.now()
        image_filename = f"{timestamp.strftime('%Y%m%d_%H%M%S')}_{cctv_id}_{license_plate}.jpg"
        image_path = os.path.join(self.config['file_paths']['image_save_dir'], image_filename)
        cv2.imwrite(image_path, frame)

        detection_data = {
            "cctvId": cctv_id,
            "licensePlate": license_plate,
            "detectedAt": timestamp.isoformat(),
            "imageUrl": image_path,
            "location": self.stream_info.get('location', 'N/A'),
            "latitude": self.stream_info.get('coordinates', {}).get('latitude', 0.0),
            "longitude": self.stream_info.get('coordinates', {}).get('longitude', 0.0),
            "vehicleType": "CAR"
        }
        send_detection_to_backend(cctv_id, detection_data, self.config['api']['backend_url'])

def send_detection_to_backend(cctv_id, detection_data, api_url):
    headers = {'Content-Type': 'application/json'}
    for key, value in detection_data.items():
        if isinstance(value, np.generic): detection_data[key] = value.item()
    try:
        response = requests.post(api_url, data=json.dumps(detection_data, indent=2), headers=headers)
        response.raise_for_status()
        print(f"[{cctv_id}] Successfully sent data. Response: {response.json()}")
    except requests.exceptions.RequestException as e:
        print(f"[{cctv_id}] Error sending data: {e}")

def main():
    parser = argparse.ArgumentParser(description="Illegal Parking Detection System (Multi-Stream)")
    parser.add_argument("--config", type=str, default="config.yaml", help="Path to the configuration YAML file.")
    parser.add_argument("--video_dir", type=str, help="Path to video directory for testing (overrides config). ")
    args = parser.parse_args()

    config = load_config(args.config)
    if not config: return

    models = load_models(config)
    if not models: return

    os.makedirs(config['file_paths']['image_save_dir'], exist_ok=True)

    # Create a context dictionary to hold shared resources
    context = {
        "models": models,
        "config": config,
        "eval_mode": args.eval
    }

    streams_to_process = []
    if args.video_dir:
        print(f"--video_dir provided. Processing videos from: {args.video_dir}")
        if not os.path.isdir(args.video_dir):
            print(f"Error: Directory not found at {args.video_dir}")
            return
        for i, filename in enumerate(os.listdir(args.video_dir)):
            if filename.endswith(('.mp4', '.avi', '.mov')):
                streams_to_process.append({
                    "id": f"test_vid_{i+1:03d}",
                    "source": os.path.join(args.video_dir, filename),
                    "location": "Test Video"
                })
    else:
        print("Processing streams from config.yaml")
        streams_to_process = config.get('cctv_streams', [])

    if not streams_to_process:
        print("No video streams to process. Check config.yaml or --video_dir.")
        return

    threads = []
    for stream_info in streams_to_process:
        processor = CCTVStreamProcessor(stream_info, context)
        threads.append(processor)
        processor.start()
        time.sleep(0.5)

    for thread in threads:
        thread.join()

    print("All video streams processed. Exiting.")
    cv2.destroyAllWindows()

if __name__ == '__main__':
    main()