  
import cv2
from flask import Flask, Response

app = Flask(__name__)

# 1. CHANGE THIS TO YOUR PHONE's EXACT IP RIGHT NOW
PHONE_URL = "http://192.168.209.245:8080/video"
cap = cv2.VideoCapture(PHONE_URL)

def generate_frames():
    while True:
        success, frame = cap.read()
        if not success:
            continue
        # Compress and serve the clean frame
        ret, buffer = cv2.imencode('.jpg', frame)
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + buffer.tobytes() + b'\r\n')

@app.route('/video')
def video_feed():
    return Response(generate_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')

if __name__ == "__main__":
    print(f"[BRIDGE] Fetching video from: {PHONE_URL}")
    print(f"[BRIDGE] Serving to WSL at: http://192.168.137.1:5000/video")
    # Hosts it on all Windows network adapters
    app.run(host='0.0.0.0', port=5000)




# import cv2
# from flask import Flask, Response

# app = Flask(__name__)
# cap = cv2.VideoCapture(0) # Grabs your HP HD Camera perfectly in Windows

# def generate():
#     while True:
#         success, frame = cap.read()
#         if not success:
#             break
#         # Compress and stream
#         ret, buffer = cv2.imencode('.jpg', frame)
#         yield (b'--frame\r\n'
#                b'Content-Type: image/jpeg\r\n\r\n' + buffer.tobytes() + b'\r\n')

# @app.route('/video')
# def video():
#     return Response(generate(), mimetype='multipart/x-mixed-replace; boundary=frame')

# if __name__ == '__main__':
#     print("Broadcasting camera to WSL...")
#     app.run(host='0.0.0.0', port=5000)

 