"""
AEGIS — YOLO Integration Bridge
Shows exactly how to send/receive data between modules
"""

import json


def simulate_pipeline():

    print("=" * 50)
    print("  AEGIS YOLO Integration Bridge")
    print("=" * 50)

    yolo_output = [
        {
            "class":      "person",
            "confidence": 0.94,
            "x1":         120,
            "y1":         50,
            "x2":         380,
            "y2":         430,
            "center_x":   250.0,
            "center_y":   240.0
        },
        {
            "class":      "fire",
            "confidence": 0.89,
            "x1":         400,
            "y1":         100,
            "x2":         600,
            "y2":         350,
            "center_x":   500.0,
            "center_y":   225.0
        },
        {
            "class":      "obstacle",
            "confidence": 0.76,
            "x1":         50,
            "y1":         300,
            "x2":         200,
            "y2":         480,
            "center_x":   125.0,
            "center_y":   390.0
        }
    ]

    print("\n[YOLO sends to /yolo/detections]")
    print(json.dumps(yolo_output, indent=2))

    print("\n[YOLO sends persons only to Hamid's /yolo/persons]")
    persons = [d for d in yolo_output if d['class'] == 'person']
    print(json.dumps(persons, indent=2))

    print("\n[SLAM reads these fields from YOLO]")
    for det in yolo_output:
        print(f"  class: {det['class']} | center: ({det['center_x']}, {det['center_y']}) | conf: {det['confidence']}")

    print("\nAll good! Integration ready ✅")


if __name__ == "__main__":
    simulate_pipeline()
