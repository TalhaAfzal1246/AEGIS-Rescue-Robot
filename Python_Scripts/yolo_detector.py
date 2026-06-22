"""
AEGIS ROBOT — YOLO Object Detection
Detects: person (victim), fire, obstacle
Target: 93%+ accuracy
"""

import cv2
import numpy as np
import time
from ultralytics import YOLO

CLASS_NAMES = {0: 'person', 1: 'fire', 2: 'obstacle'}
CLASS_COLORS = {
    'person':   (0, 255, 0),
    'fire':     (0, 0, 255),
    'obstacle': (0, 165, 255),
}
MIN_CONFIDENCE = 0.35
BBOX_PADDING   = 10


class YOLODetector:

    def __init__(self, model_path: str = 'aegis_model.pt', debug_mode: bool = False):
        self.debug_mode = debug_mode
        self.model      = YOLO(model_path)
        self.history    = []
        print("[YOLODetector] AEGIS YOLO Detector loaded ✅")
        print(f"[YOLODetector] Model: {model_path}")
        print(f"[YOLODetector] Classes: {CLASS_NAMES}")

    def detect(self, frame: np.ndarray) -> dict:

        t_start = time.time()

        result = {
            'persons':         [],
            'fires':           [],
            'obstacles':       [],
            'all_detections':  [],
            'annotated_image': frame.copy() if self.debug_mode else None,
            'processing_ms':   0.0,
            'frame_shape':     frame.shape,
        }

        results = self.model(frame, conf=MIN_CONFIDENCE, verbose=False)

        for r in results:
            for box in r.boxes:
                cls_id     = int(box.cls[0])
                confidence = float(box.conf[0])
                x1, y1, x2, y2 = map(int, box.xyxy[0])
                class_name = CLASS_NAMES.get(cls_id, 'unknown')
                center_x   = (x1 + x2) / 2.0
                center_y   = (y1 + y2) / 2.0

                detection = {
                    'class':      class_name,
                    'confidence': round(confidence, 3),
                    'x1':         x1,
                    'y1':         y1,
                    'x2':         x2,
                    'y2':         y2,
                    'center_x':   center_x,
                    'center_y':   center_y,
                }

                result['all_detections'].append(detection)

                if class_name == 'person':
                    result['persons'].append(detection)
                elif class_name == 'fire':
                    result['fires'].append(detection)
                elif class_name == 'obstacle':
                    result['obstacles'].append(detection)

        if self.debug_mode:
            result['annotated_image'] = self._draw(frame.copy(), result)

        result['processing_ms'] = round((time.time() - t_start) * 1000, 2)
        return result

    def get_person_bboxes(self, frame: np.ndarray) -> list:
        """Returns list of bbox dicts for Hamid's pose estimator"""
        result = self.detect(frame)
        return result['persons']

    def _draw(self, frame, result):
        for det in result['all_detections']:
            color = CLASS_COLORS.get(det['class'], (255, 255, 255))
            cv2.rectangle(frame,
                          (det['x1'], det['y1']),
                          (det['x2'], det['y2']),
                          color, 2)
            label = f"{det['class']} {det['confidence']:.2f}"
            (tw, th), _ = cv2.getTextSize(
                label, cv2.FONT_HERSHEY_SIMPLEX, 0.6, 2
            )
            cv2.rectangle(frame,
                          (det['x1'], det['y1'] - th - 10),
                          (det['x1'] + tw + 5, det['y1']),
                          color, -1)
            cv2.putText(frame, label,
                        (det['x1'] + 3, det['y1'] - 5),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6,
                        (255, 255, 255), 2)

        summary = f"P:{len(result['persons'])} F:{len(result['fires'])} O:{len(result['obstacles'])}"
        cv2.putText(frame, summary, (10, 30),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.8,
                    (255, 255, 0), 2)
        return frame

    def release(self):
        print("[YOLODetector] Released.")
