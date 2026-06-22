import cv2
import time
import threading
import pandas as pd
import os
import socket
import json
from datetime import datetime
from ultralytics import YOLO
from yolo_detector import YOLODetector

# ==========================================
# CONFIGURATION
# ==========================================
CSV_FILE = "aegis_data.csv"
UDP_PORT = 4210

# ==========================================
# 1. THE MAP ENGINE & NETWORK VAULT
# ==========================================
class MapEngine:
    def __init__(self):
        self.lock = threading.Lock()
        
        # Vision State
        self.victims_found = 0
        self.latest_victim_status = "none"
        self.fire_detected = False
        
        # Hardware State (Updated by ESP32)
        self.esp32_address = None  # Auto-locks when first packet arrives
        self.telemetry = {
            "dist": 999,
            "temp": 0.0,
            "smoke": 0,
            "override": False,
            # --- NEW SLAM VARIABLES ---
            "x_pos": 0.0,
            "y_pos": 0.0,
            "heading": 0.0
        }
        

    def update_vision_data(self, fire_present, person_present, victim_status):
        with self.lock:
            self.fire_detected = fire_present
            if person_present:
                self.latest_victim_status = victim_status.lower()
                self.victims_found = 1 
            else:
                self.latest_victim_status = "none"
                self.victims_found = 0

    def update_telemetry(self, address, data):
        with self.lock:
            self.esp32_address = address
            self.telemetry.update(data)

    def get_current_state(self):
        with self.lock:
            return {
                "victims": self.victims_found,
                "status": self.latest_victim_status,
                "fire": self.fire_detected,
                "telemetry": self.telemetry.copy(),
                "address": self.esp32_address
            }


# ==========================================
# 2. UDP NETWORK LISTENER & EKF THREAD
# ==========================================
def udp_listener(map_engine, sock):
    import math
    import time
    import json
    import socket
    
    # --- NEW: WSL FORWARDER SETUP ---
    WSL_IP = "172.20.28.252"  # Windows Localhost (routes directly into WSL)
    WSL_PORT = 9090       # The port our C++ engine will listen to
    wsl_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    print(f"[NETWORK] WSL Physics Forwarder Active -> {WSL_IP}:{WSL_PORT}")
    # --------------------------------

    WHEEL_RADIUS = 0.0325  
    WHEEL_BASE = 0.254    
    TICKS_PER_REV = 181.5  
    METERS_PER_TICK = (2.0 * math.pi * WHEEL_RADIUS) / TICKS_PER_REV

    print("[NETWORK] Calibrating Gyroscope. Keep AEGIS still...")
    calibration_readings = []
    
    # Quick Calibration Loop
    sock.settimeout(1.0)
    while len(calibration_readings) < 50:
        try:
            data, addr = sock.recvfrom(1024)
            packet = json.loads(data.decode('utf-8'))
            calibration_readings.append(packet.get("gyro_z", 0.0))
            map_engine.update_telemetry(addr, {}) # Just to lock the IP
        except socket.timeout:
            continue
            
    gyro_offset_z = sum(calibration_readings) / len(calibration_readings)
    print(f"[NETWORK] Calibration Complete. Bias: {gyro_offset_z:.4f}")
    
    sock.setblocking(False) 
    
    x_pos, y_pos, theta = 0.0, 0.0, 0.0
    prev_enc_l, prev_enc_r = 0, 0
    prev_time = time.time()
    first_packet = True

    while True:
        try:
            data, addr = sock.recvfrom(1024)
            packet = json.loads(data.decode('utf-8'))
            current_time = time.time()
            
            curr_enc_l = packet.get("enc_l", 0)
            curr_enc_r = packet.get("enc_r", 0)
            raw_gyro_z = packet.get("gyro_z", 0.0)
            
            if first_packet:
                prev_enc_l = curr_enc_l
                prev_enc_r = curr_enc_r
                prev_time = current_time
                first_packet = False
                continue
                
            dt = current_time - prev_time
            prev_time = current_time
            
            # Distance Math
            delta_ticks_l = curr_enc_l - prev_enc_l
            delta_ticks_r = curr_enc_r - prev_enc_r
            prev_enc_l = curr_enc_l
            prev_enc_r = curr_enc_r
            
            d_center = ((delta_ticks_l + delta_ticks_r) / 2.0) * METERS_PER_TICK
            
            # Heading Math
            clean_gyro_z = raw_gyro_z - gyro_offset_z
            if abs(clean_gyro_z) < 0.03: clean_gyro_z = 0.0
            theta += (clean_gyro_z * dt)
            
            # Position Math
            x_pos += d_center * math.cos(theta)
            y_pos += d_center * math.sin(theta)
            theta = theta % (2.0 * math.pi)
            
            # Update the Vault
            packet["x_pos"] = x_pos
            packet["y_pos"] = y_pos
            packet["heading"] = math.degrees(theta)
            
            map_engine.update_telemetry(addr, packet)
            
            # --- NEW: FIRE THE PACKET INTO WSL ---
            # We bundle just the critical XYZ data to keep the C++ parser fast
            # wsl_payload = f"{x_pos},{y_pos},{theta}\n".encode('utf-8')
            # wsl_sock.sendto(wsl_payload, (WSL_IP, WSL_PORT))
            current_state = map_engine.get_current_state()
            hazard_code = 0
            if current_state["fire"]: hazard_code = 3
            elif current_state["victims"] > 0:
                hazard_code = 2 if current_state["status"] == "unconscious" else 1
            
            # Send: X, Y, Theta, Hazard_Code
            wsl_payload = f"{x_pos},{y_pos},{theta},{hazard_code}\n".encode('utf-8')
            wsl_sock.sendto(wsl_payload, (WSL_IP, WSL_PORT))
            # -------------------------------------
            
        except BlockingIOError:
            time.sleep(0.01)
        except Exception:
            pass

# ==========================================
# 3. EVENT-DRIVEN CSV BROADCASTER
# ==========================================
def live_data_broadcaster(map_engine):
    import csv 
    print("[SYSTEM] Event-Driven CSV Broadcaster active.")
    last_logged_state = {"victims": -1, "status": "INIT", "fire": None}
    
    # 1. YOUR EXACT DISCOVERED HEADERS
    HEADERS = [
        "timestamp", "x_coord", "y_coord", "zone", 
        "victim_detected", "victim_count", "victim_status", 
        "temperature", "humidity", "smoke_density", 
        "fire_detected", "fire_spread"
    ]
    
    while True:
        state = map_engine.get_current_state()
        tel = state["telemetry"]
        
        has_changed = (
            state["victims"] != last_logged_state["victims"] or
            state["status"] != last_logged_state["status"] or
            state["fire"] != last_logged_state["fire"]
        )
        
        if has_changed and state["address"] is not None:
            fire_spread = "medium" if state["fire"] else "none"
            smoke_str = "high" if tel["smoke"] > 2000 else "low"
            
            # 2. THE DATA EXACTLY ALIGNED TO YOUR HEADERS
            current_data = [
                datetime.now().strftime("%Y-%m-%d %H:%M:%S"), # timestamp
                round(tel["x_pos"], 3),                       # x_coord
                round(tel["y_pos"], 3),                       # y_coord
                "Zone_A",                                     # zone
                state["victims"] > 0,                         # victim_detected
                state["victims"],                             # victim_count
                state["status"],                              # victim_status
                round(tel["temp"], 1),                        # temperature
                45.0,                                         # humidity (placeholder)
                smoke_str,                                    # smoke_density
                state["fire"],                                # fire_detected
                fire_spread                                   # fire_spread
            ]

            # 3. THE CSV WRITER
            file_exists = os.path.isfile(CSV_FILE)
            
            with open(CSV_FILE, mode='a', newline='') as file:
                writer = csv.writer(file)
                if not file_exists:
                    writer.writerow(HEADERS)
                    print("[SYSTEM] New CSV created. Headers initialized.")
                writer.writerow(current_data)
            
            print(f"\n[EVENT LOGGED] Victim: {state['victims']} | Fire: {state['fire']} | Temp: {tel['temp']}C")
            last_logged_state = state.copy()

        time.sleep(0.5)

# ==========================================
# 4. THE VISION & CONTROL COMMANDER (MAIN LOOP)
# ==========================================

class LiveCamera:
    def __init__(self, url):
        self.cap = cv2.VideoCapture(url)
        self.ret, self.frame = self.cap.read()
        self.running = True
        
        # This background thread constantly empties the OpenCV buffer
        self.thread = threading.Thread(target=self.update, daemon=True)
        self.thread.start()

    def update(self):
        while self.running:
            ret, frame = self.cap.read()
            if ret:
                self.frame = frame # Overwrite with the absolute newest frame

    def read(self):
        # When YOLO asks for a frame, hand it the freshest one
        return self.ret, self.frame

    def release(self):
        self.running = False
        self.cap.release()




def main_vision_loop():
    print("\n[SYSTEM] Booting AEGIS AI Core...")
    
    aegis_map = MapEngine()

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind(('0.0.0.0', UDP_PORT))
    # sock.bind(('192.168.133.81', UDP_PORT))
    # sock.bind(('192.168.209.81', UDP_PORT))


    sock.setblocking(False) 

    threading.Thread(target=udp_listener, args=(aegis_map, sock), daemon=True).start()
    threading.Thread(target=live_data_broadcaster, args=(aegis_map,), daemon=True).start()

    print("[SYSTEM] Loading Models...")
    obj_detector = YOLODetector(model_path='aegis_model.pt', debug_mode=True)
    pose_model = YOLO('yolov8n-pose.pt')

    consecutive_fallen = 0
    consecutive_standing = 0
    REQUIRED_FRAMES = 3  
    official_victim_state = "SCANNING..."

    # video_url = "http://192.168.209.245:8080/video"
    video_url = "Enter URL of Camera You are Using"
    

    cap = LiveCamera(video_url)


    print("\n========================================")
    print(" AEGIS COMMAND CENTER ACTIVE")
    print(" Drive: W A S D  |  Stop: Spacebar  |  Quit: Q")
    print("========================================")

    cv2.namedWindow("AEGIS - Tactical Vision", cv2.WINDOW_NORMAL)

    frame_counter = 0


    last_key_time = time.time()
    current_drive_state = 'S'
    last_sent_state = ''

    while True:
        ret, frame = cap.read()
        if not ret: 
            print("[ERROR] Camera frame dropped. Is the camera being used by another app?")
            break

        frame_counter += 1
        if frame_counter % 2 == 0:
            # We skip the heavy math on this frame to save CPU power!
            # But we still listen for W A S D driving commands so it doesn't lag.
            key = cv2.waitKey(1) & 0xFF
            
            continue
        
        t0 = time.time()

        # STEP 1: VISION
        obj_result = obj_detector.detect(frame)
        display_frame = obj_result.get('annotated_image', frame.copy())
        
        is_fire = len(obj_result['fires']) > 0
        is_person = len(obj_result['persons']) > 0

        # STEP 2: POSE ESTIMATION & OVERRIDE LOGIC
        if is_person:
            cv2.putText(display_frame, "SYSTEM HALT: VICTIM DETECTED", (10, 30), 
                        cv2.FONT_HERSHEY_DUPLEX, 0.8, (0, 0, 255), 2)
            
            pose_results = pose_model(frame, verbose=False)
            display_frame = pose_results[0].plot(img=display_frame)
            keypoints_data = pose_results[0].keypoints

            if keypoints_data is not None and len(keypoints_data.xy) > 0:
                for person in keypoints_data.xy:
                    if len(person) >= 17:
                        nose_y, left_ankle_y, right_ankle_y = person[0][1].item(), person[15][1].item(), person[16][1].item()
                        if nose_y > 0 and (left_ankle_y > 0 or right_ankle_y > 0):
                            vertical_diff = abs(max(left_ankle_y, right_ankle_y) - nose_y)
                            if vertical_diff < 150:
                                consecutive_fallen += 1; consecutive_standing = 0
                            else:
                                consecutive_standing += 1; consecutive_fallen = 0

                            if consecutive_fallen >= REQUIRED_FRAMES: official_victim_state = "UNCONSCIOUS"
                            elif consecutive_standing >= REQUIRED_FRAMES: official_victim_state = "CONSCIOUS"

            color = (0, 0, 255) if official_victim_state == "UNCONSCIOUS" else (0, 255, 0)
            cv2.putText(display_frame, f"STATUS: {official_victim_state}", (10, 110), cv2.FONT_HERSHEY_DUPLEX, 0.8, color, 2)
        else:
            consecutive_fallen = 0; consecutive_standing = 0; official_victim_state = "NONE"

        if is_fire:
            cv2.putText(display_frame, "HAZARD: FIRE DETECTED", (10, 150), cv2.FONT_HERSHEY_DUPLEX, 0.8, (0, 165, 255), 2)

        # STEP 3: UPDATE VAULT
        aegis_map.update_vision_data(is_fire, is_person, official_victim_state)
        current_state = aegis_map.get_current_state()

        tel = current_state["telemetry"]
        if current_state["address"]:
            cv2.putText(display_frame, f"LINK: ACTIVE | Temp: {tel['temp']}C | Dist: {tel['dist']}cm", 
                        (10, 450), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 255), 2)
            if tel["override"]:
                cv2.putText(display_frame, "ULTRASONIC BRAKE ENGAGED", (300, 30), 
                            cv2.FONT_HERSHEY_DUPLEX, 0.7, (0, 165, 255), 2)

        # STEP 4: SEND MOTOR COMMANDS
        key = cv2.waitKey(1) & 0xFF
        cmd_to_send = None

        hazard_in_front = is_person or is_fire or tel.get("override", False)

        # 1. Catch the key press and reset the deadman timer
        if key == ord('w'):
            current_drive_state = 'S' if hazard_in_front else 'F'
            last_key_time = time.time()
        elif key == ord('s'):
            current_drive_state = 'B'
            last_key_time = time.time()
        elif key == ord('a'):
            current_drive_state = 'L'
            last_key_time = time.time()
        elif key == ord('d'):
            current_drive_state = 'R'
            last_key_time = time.time()
        elif key == ord(' '):
            current_drive_state = 'S'

        # 2. The Deadman Switch
        # If no valid drive key was pressed in the last 0.15 seconds, auto-stop.
        if time.time() - last_key_time > 0.15:
            current_drive_state = 'S'

        # 3. UDP Spam Filter (The Secret to Zero Lag)
        # ONLY send a network packet if the command actually changed. 
        if current_drive_state != last_sent_state:
            if current_state["address"]:
                try:
                    sock.sendto(current_drive_state.encode(), current_state["address"])
                    
                    if current_drive_state == 'S':
                        print("[NETWORK] Brakes Applied.")
                    else:
                        print(f"[NETWORK] Sent command: {current_drive_state}")
                        
                    # Save this state so we don't spam it again
                    last_sent_state = current_drive_state
                except BlockingIOError:
                    pass

        if key == ord('q'): break

        cv2.imshow("AEGIS - Tactical Vision", display_frame)

    cap.release()
    cv2.destroyAllWindows()
    obj_detector.release()


if __name__ == "__main__":
    main_vision_loop()