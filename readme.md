# AEGIS (Automated Emergency Ground Intelligence System)

AEGIS is an autonomous fire-fighting and tactical rescue robot designed to navigate disaster zones, classify hazards, and generate real-time 3D tactical maps for first responders. 

🏆 **Officially Shortlisted (Out of 30) — FAST-NUCES Robotics Exhibition**

---

## ⚙️ System Architecture

AEGIS bridges high-level AI with low-level hardware control through a highly distributed, multi-language stack:

* **🧠 The Visual Cortex (Python):** Utilizes YOLOv8 for live object detection and pose estimation. It instantly classifies victims (conscious vs. unconscious) and identifies active fires from a live network camera feed.
* **🗺️ The Spatial Engine (C++ & ORB-SLAM3):** A heavily modified visual SLAM engine running on WSL/Ubuntu. It utilizes native OpenGL to drop 3D holographic hazard markers directly into the generated spatial map at the exact coordinates a threat is detected.
* **🎙️ Tactical Voice System:** A voice agent that lets a commander ask AEGIS questions on the fly and get spoken updates back, built using Whisper for speech recognition, pyttsx3 and win32com for speech synthesis, and sound device for real-time audio capture, all stitched together with a lightweight Python pipeline.
* **🦾 The Hardware Spine (ESP32 / C++):** Manages locomotion and ultrasonic reflexes. It executes a custom "Tactical Evasion" framework that safely overrides forward momentum during hazard encounters while keeping evasive steering active.
* **📡 The Command Center:** A zero-lag UDP network bridge synchronizes the hardware telemetry with the vision system, pushing live data to an asynchronous CSV broadcaster and a 2D Matplotlib tactical radar.

---

## 🛠️ Prerequisites

### Python Environment (Windows)
* Python 3.8+
* Install dependencies: `pip install -r requirements.txt`
* YOLOv8 weights (`aegis_model.pt` and `yolov8n-pose.pt`) placed in the root directory.

### SLAM Environment (WSL / Ubuntu)
* Built and compiled **ORB-SLAM3** environment.
* C++ dependencies: OpenCV, Eigen3, Pangolin, DBoW2, g2o.

---

## 🚀 Quick Start Configuration

To boot the entire AEGIS ecosystem, launch the modules in this specific sequence:

**Windows Terminal 1**
Start the main aegis_core.py
**Windows Terminal 2**
Start the voice_interface.py
**Windows Terminal 3**
Start the com_server.py
