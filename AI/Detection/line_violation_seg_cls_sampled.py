# -*- coding: utf-8 -*-
import os
import json
import cv2
import numpy as np
import argparse
from pathlib import Path
from tqdm import tqdm
import random
from collections import defaultdict

class LaneViolationDatasetGenerator:
    def __init__(self, source_path, output_path):
        self.source_path = Path(source_path)
        self.output_path = Path(output_path)
        
        # 4-class mask configuration
        self.mask_classes = {
            'background': 0,
            'vehicle': 1,
            'lane': 2,
            'overlap': 3
        }
        
        # YOLO seg trained classes
        self.vehicle_types = ['vehicle_car', 'vehicle_bus', 'vehicle_truck', 'vehicle_bike']
        self.lane_types = [
            'lane_shoulder_single_solid',
            'lane_shoulder_double_solid', 
            'lane_shoulder_single_dashed',
            'lane_shoulder_left_dashed_double',
            'lane_shoulder_right_dashed_double'
        ]
        
        # Violation categories
        self.violation_categories = ['normal', 'danger', 'violation']
        
        # Colors for visualization
        self.colors = {
            0: [0, 0, 0],      # background - black
            1: [0, 255, 0],    # vehicle - green
            2: [0, 0, 255],    # lane - red
            3: [255, 255, 0]   # overlap - cyan
        }
        
        self.setup_directories()
    
    def setup_directories(self):
        """Create output directory structure"""
        for category in self.violation_categories:
            (self.output_path / 'mask' / category).mkdir(parents=True, exist_ok=True)
            (self.output_path / 'mask_vis' / category).mkdir(parents=True, exist_ok=True)
            (self.output_path / 'image' / category).mkdir(parents=True, exist_ok=True)
    
    def parse_json_annotation(self, json_path):
        """Parse JSON annotation file"""
        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        annotations = []
        violation_type = None
        
        for item in data['data_set_info']['data']:
            obj_label = item['value'].get('object_Label', {})
            points = item['value'].get('points', [])
            extra = item['value'].get('extra', {})
            
            if not points:
                continue
                
            # Convert points to numpy array
            polygon = np.array([[p['x'], p['y']] for p in points], dtype=np.int32)
            
            # Use extra.value to distinguish between vehicle and lane
            object_type = extra.get('value', '')
            
            if object_type == 'vehicle':
                # Process vehicle annotations
                vehicle_type = obj_label.get('vehicle_type', '')
                if vehicle_type in self.vehicle_types:
                    vehicle_attr = obj_label.get('vehicle_attribute', '')
                    if vehicle_attr in self.violation_categories:
                        violation_type = vehicle_attr
                    
                    annotations.append({
                        'type': 'vehicle',
                        'polygon': polygon,
                        'class_name': vehicle_type,
                        'violation': vehicle_attr
                    })
            
            elif object_type == 'lane':
                # Process lane annotations
                lane_type = obj_label.get('lane_type', '')
                # Accept any shoulder lane type (more flexible matching)
                if 'shoulder' in lane_type.lower():
                    annotations.append({
                        'type': 'lane',
                        'polygon': polygon,
                        'class_name': lane_type
                    })
        
        return annotations, violation_type
    
    def create_mask(self, annotations, img_shape):
        """Create 4-class mask from annotations"""
        h, w = img_shape[:2]
        mask = np.zeros((h, w), dtype=np.uint8)
        
        vehicle_mask = np.zeros((h, w), dtype=np.uint8)
        lane_mask = np.zeros((h, w), dtype=np.uint8)
        
        # Draw vehicle polygons
        for ann in annotations:
            if ann['type'] == 'vehicle':
                cv2.fillPoly(vehicle_mask, [ann['polygon']], 1)
            elif ann['type'] == 'lane':
                cv2.fillPoly(lane_mask, [ann['polygon']], 1)
        
        # Assign mask values
        mask[vehicle_mask > 0] = self.mask_classes['vehicle']
        mask[lane_mask > 0] = self.mask_classes['lane']
        
        # Find overlap regions
        overlap_mask = (vehicle_mask > 0) & (lane_mask > 0)
        mask[overlap_mask] = self.mask_classes['overlap']
        
        return mask
    
    def create_visualization(self, mask):
        """Create color visualization of mask"""
        h, w = mask.shape
        vis = np.zeros((h, w, 3), dtype=np.uint8)
        
        for class_id, color in self.colors.items():
            vis[mask == class_id] = color
        
        return vis
    
    def collect_annotation_files(self, make_sample=False):
        """Collect annotation files from dataset"""
        annotation_files = defaultdict(list)
        
        print(f"Looking for data in: {self.source_path}")
        
        # Search in Training and Validation directories - Only SHOULDER directories
        for data_split in ['1.Training', '2.Validation']:
            label_dir = self.source_path / data_split / '라벨링데이터'
            print(f"Checking directory: {label_dir}")
            
            if not label_dir.exists():
                print(f"Directory not found: {label_dir}")
                continue
                
            # Search only in SHOULDER directories (A/SHOULDER, B/SHOULDER, C/SHOULDER)
            json_files_found = []
            camera_channels = ['A', 'B', 'C']
            
            for camera in camera_channels:
                shoulder_dir = label_dir / camera / 'SHOULDER'
                if shoulder_dir.exists():
                    shoulder_json_files = list(shoulder_dir.rglob('*.json'))
                    json_files_found.extend(shoulder_json_files)
                    print(f"Found {len(shoulder_json_files)} JSON files in {shoulder_dir}")
            
            print(f"Total SHOULDER JSON files found: {len(json_files_found)}")
            
            if not json_files_found:
                print(f"No SHOULDER JSON files found in {data_split}")
                continue
            
            processed_count = 0
            violation_counts = defaultdict(int)
            
            # Group files by video for 6-frame sampling
            video_files = defaultdict(list)
            for json_file in json_files_found:
                # Extract video identifier from filename
                # Pattern: [SHOULDER]00022A_183627_002.json
                # Directory: [00022]A_SHOULDER
                filename = json_file.stem
                if filename.startswith('[SHOULDER]'):
                    # Extract parts: 00022A_183627_002
                    parts = filename.replace('[SHOULDER]', '').split('_')
                    if len(parts) >= 3:
                        # video_id combines video number, camera, and time
                        # e.g., "00022A_183627" (same video sequence)
                        video_id = f"{parts[0]}_{parts[1]}"  # "00022A_183627"
                        try:
                            frame_number = int(parts[2])  # 002, 003, etc.
                            video_files[video_id].append((json_file, frame_number))
                        except ValueError:
                            continue
            
            # Sort files by frame number within each video and apply 6-frame sampling
            sampled_files = []
            for video_id, files in video_files.items():
                files.sort(key=lambda x: x[1])  # Sort by frame number
                # Sample every 6th frame (starting from frame 0)
                for i in range(0, len(files), 6):
                    sampled_files.append(files[i][0])  # Add json_file
                    
            print(f"After 6-frame sampling: {len(sampled_files)} files from {len(video_files)} videos")
            
            # Set up progress bar
            search_limit = 50 if make_sample else len(sampled_files)
            pbar = tqdm(sampled_files[:search_limit], desc=f"Processing {data_split} SHOULDER (6-frame sampled)")
            
            for json_file in pbar:
                try:
                    annotations, violation_type = self.parse_json_annotation(json_file)
                    
                    if violation_type:
                        violation_counts[violation_type] += 1
                        
                    if violation_type and violation_type in self.violation_categories:
                        # Check if corresponding image exists
                        img_path = self.get_corresponding_image_path(json_file)
                        if img_path and img_path.exists():
                            annotation_files[violation_type].append((json_file, img_path))
                            processed_count += 1
                            
                            # Update progress bar description
                            pbar.set_postfix({
                                'found': f"V:{len(annotation_files.get('violation', []))} "
                                        f"D:{len(annotation_files.get('danger', []))} "
                                        f"N:{len(annotation_files.get('normal', []))}"
                            })
                            
                            # Show progress for first few files of each type
                            if len(annotation_files[violation_type]) <= 3:
                                tqdm.write(f"Found {violation_type}: {json_file}")
                    
                    # Early termination if we have enough samples for all categories
                    if make_sample and all(len(annotation_files[cat]) >= 10 for cat in self.violation_categories if len(annotation_files[cat]) > 0):
                        break
                        
                except Exception as e:
                    continue
            
            pbar.close()
            
            print(f"Violation type distribution found: {dict(violation_counts)}")
            print(f"Files collected per category: {[(cat, len(files)) for cat, files in annotation_files.items()]}")
        
        # Apply sampling if requested
        if make_sample:
            for category in self.violation_categories:
                if len(annotation_files[category]) > 10:
                    annotation_files[category] = random.sample(annotation_files[category], 10)
        
        return annotation_files
    
    def get_corresponding_image_path(self, json_path):
        """Get corresponding image path from JSON path"""
        # Convert from 라벨링데이터 to 원천데이터 and .json to .jpg
        json_path = Path(json_path)
        relative_path = json_path.relative_to(self.source_path)
        
        # Replace 라벨링데이터 with 원천데이터 and .json with .jpg
        img_path_str = str(relative_path).replace('라벨링데이터', '원천데이터').replace('.json', '.jpg')
        img_path = self.source_path / img_path_str
        
        return img_path
    
    def process_dataset(self, make_sample=False):
        """Process the entire dataset"""
        print(f"Collecting annotation files... (sample mode: {make_sample})")
        annotation_files = self.collect_annotation_files(make_sample)
        
        total_files = sum(len(files) for files in annotation_files.values())
        print(f"Found {total_files} annotation files:")
        for category, files in annotation_files.items():
            print(f"  {category}: {len(files)} files")
        
        if total_files == 0:
            print("No annotation files found!")
            return
        
        # Process each category
        for category in self.violation_categories:
            if not annotation_files[category]:
                continue
                
            print(f"\nProcessing {category} category...")
            
            for i, (json_path, img_path) in enumerate(tqdm(annotation_files[category], desc=f"Processing {category}")):
                try:
                    # Load image with Korean path support
                    img_path_str = str(img_path)
                    
                    # Use numpy and cv2 for Korean path support
                    with open(img_path_str, 'rb') as f:
                        img_data = f.read()
                    img_array = np.frombuffer(img_data, np.uint8)
                    image = cv2.imdecode(img_array, cv2.IMREAD_COLOR)
                    
                    if image is None:
                        print(f"Failed to load image: {img_path}")
                        continue
                    
                    # Parse annotations
                    annotations, _ = self.parse_json_annotation(json_path)
                    if not annotations:
                        continue
                    
                    # Create mask
                    mask = self.create_mask(annotations, image.shape)
                    
                    # Create visualization
                    mask_vis = self.create_visualization(mask)
                    
                    # Generate filename using original image name
                    original_filename = img_path.stem  # Get filename without extension
                    filename = f"{original_filename}.png"
                    
                    # Save files
                    cv2.imwrite(str(self.output_path / 'mask' / category / filename), mask)
                    cv2.imwrite(str(self.output_path / 'mask_vis' / category / filename), mask_vis)
                    cv2.imwrite(str(self.output_path / 'image' / category / filename), image)
                    
                except Exception as e:
                    print(f"Error processing {json_path}: {e}")
                    continue
        
        print(f"\nDataset generation completed!")
        print(f"Output directory: {self.output_path}")

def main():
    parser = argparse.ArgumentParser(description='Generate ResNet training dataset from lane violation data')
    parser.add_argument('--source', 
                       default=r'D:\134.차로 위반 영상 데이터\01.데이터',
                       help='Source data directory')
    parser.add_argument('--output',
                       default=r'C:\Users\chobh\Desktop\bigProject\Data\lane_violation_seg_cls_dataset_sampled',
                       help='Output dataset directory')
    parser.add_argument('--make_sample', action='store_true',
                       help='Generate only 10 samples per class for testing')
    
    args = parser.parse_args()
    
    # Initialize generator
    generator = LaneViolationDatasetGenerator(args.source, args.output)
    
    # Process dataset
    generator.process_dataset(make_sample=args.make_sample)

if __name__ == "__main__":
    main()