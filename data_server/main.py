from datetime import datetime
import threading
import queue
import cv2
import numpy as np
from flask import Flask, jsonify, request, render_template
from ultralytics import YOLO
import network_helper

app = Flask(__name__)

image_queue = queue.Queue(maxsize=2)

def display_images(detect_objects: bool):
    model = YOLO("YOLO26s.pt") if detect_objects else None
    try:
        while True:
            try:
                data = image_queue.get(timeout=0.1)
                image_array = np.frombuffer(data, dtype=np.uint8)
                image = cv2.imdecode(image_array, cv2.IMREAD_COLOR)

                if image is not None:
                    if detect_objects:
                        results = model.predict(image, verbose=False)
                        image = results[0].plot()
                    cv2.imshow("Live View", image)

            except queue.Empty:
                pass
            cv2.waitKey(1)
    except KeyboardInterrupt:
        print("程式已由使用者中斷")
    finally:
        cv2.destroyAllWindows()

@app.route("/hello", methods=["GET"])
def hello():
    return jsonify({"message": "hello"})

@app.route("/get-network-info", methods=["GET"])
def get_network_info():
    try:
        purpose = request.args.get("purpose")
        if not purpose:
            return jsonify({"error": "必須指定 purpose 查詢參數"}), 400

        network_info = network_helper.get_network_info(purpose)
        return jsonify(network_info)
    except ValueError as e:
        return jsonify({"error": str(e)}), 400

# template: 127.0.0.1:5000/set-network-info?server_ip=192.168.0.56&server_port=5000
@app.route("/set-network-info", methods=["GET", "POST"])
def set_network_info():
    if request.method == "GET":
        return render_template("set_network_info.html", network_info=app.network_info)
    else:
        app.network_info["ssid"] = request.form.get("ssid")
        app.network_info["password"] = request.form.get("password")
        app.network_info["ip"] = request.form.get("ip")
        app.network_info["port"] = request.form.get("port")
        # app.network_info["api_url"] = f"http://{app.network_info['ip']}:{app.network_info['port']}"

        return jsonify({"message": "Network info updated", "network_info": app.network_info})

@app.route("/esp32/image-upload", methods=["POST"])
def image_upload():
    device_id = request.headers.get("X-Device-ID")
    byte_data = request.get_data()
    print(f"Received image upload from device {device_id}, size: {len(byte_data)} bytes")

    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    filename = f"./data_server/images/image_{device_id}_{timestamp}.jpg"

    with open(filename, "wb") as f:
        f.write(byte_data)

    return jsonify({
        "message": "Image uploaded successfully", 
        "filename": filename
    })

@app.route("/esp32/image-inference", methods=["POST"])
def image_inference():
    device_id = request.headers.get("X-Device-ID")
    byte_data = request.get_data()
    print(f"Received image upload from device {device_id}, size: {len(byte_data)} bytes")

    try:
        image_queue.put(byte_data, timeout=1)
        return jsonify({"message": "Image added to queue"})
    except queue.Full:
        return jsonify({"error": "Image queue is full"}), 400

@app.route("/esp32/plate-debug", methods=["GET"])
def plate_debug():
    device_id = request.headers.get("X-Device-ID")
    byte_data = request.get_data()
    print(f"Received image upload from device {device_id}, size: {len(byte_data)} bytes")

    try:
        image_queue.put(byte_data, timeout=1)
        return jsonify({"message": "Image added to queue"})
    except queue.Full:
        return jsonify({"error": "Image queue is full"}), 400

if __name__ == "__main__":
    flask_thread = threading.Thread(
        target=lambda: app.run(
            host="0.0.0.0",
            port=5000,
            debug=True,
            use_reloader=False
        ),
        daemon=True
    )
    flask_thread.start()

    display_images(detect_objects=True)