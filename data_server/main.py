print("import 系統模組...")
from datetime import datetime
import os
import threading
import queue
import time
import traceback

print("import Flask 模組...")
from flask import Flask, jsonify, request, render_template, abort, send_file

print("import 電腦視覺模組...")
import cv2
import numpy as np
from dotenv import load_dotenv
from ultralytics import YOLO

print("import LINE Messaging API 模組...")
from linebot.v3.exceptions import InvalidSignatureError
from line.linehelper import LineMessageHelper

print("import 自訂模組...")
import network_helper
from roadtrace.tracer import PathTracer
from toiletbox.toilet_status import ToiletStateMachine
print("import 完成")

load_dotenv()
debug_count = 0

app = Flask(__name__)

print("正在載入 LINE 使用的 YOLO 模型 ...")
car_model = YOLO("./ai/best_models/車牌m(115_11_3)150次.pt")
poo_model = YOLO("./ai/best_models/(2026_11_9)便便s150次.pt")
print("載入完畢")

image_queue = queue.Queue(maxsize=2)
road_tracer = PathTracer("./ai/best_models/車牌m(115_11_3)150次.pt")
line_helper = LineMessageHelper(car_model, poo_model)
state_machine = ToiletStateMachine()

audio_files = [
    "button-press",
    "capture",
    "uploading",
    "try-again",
    "poo-normal",
    "poo-wet",
    "poo-blood-dry",
    "poo-blood-wet",
    "poo-green",
    "poo-white",
    "flush",
    "urgent-call",
]

poo_type_map = {
    -1: "unknown",
    0: "poo-blood-dry",
    1: "poo-wet",
    2: "poo-green",
    3: "poo-blood-wet",
    4: "poo-white",
    5: "poo-normal",
}

csi_state = {
    "someone": False,
    "motion": False,
    "state": "",
    "timestamp": "",
    "fast_empty": False,
    "long_static": False,
    "last_static": datetime.now()
}

def display_images(detect_objects: bool):
    print("正在載入 queue 使用的 YOLO...")
    model = YOLO("./ai/best_models/(2026_11_9)便便s150次.pt") if detect_objects else None
    print("載入完畢")

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
        return jsonify({"error": "Image queue is full"}), 503

@app.route("/esp32/sound-snapshot", methods=["POST"])
def sound_snapshot():
    device_id = request.headers.get("X-Device-ID")
    sound_level = float(request.headers.get("X-Sound-Level"))
    byte_data = request.get_data()
    print(f"偵測到聲音快照，裝置ID: {device_id}, 聲音分貝: {sound_level}, 資料大小: {len(byte_data)} bytes")

    try:
        road_tracer.trace_plate(device_id, sound_level, byte_data)

        police_area = "G" # 真正應用要搜尋最近警車，但先假設警車都在 G 區
        road_tracer.set_best_path(police_area, device_id)
        best_path = road_tracer.get_best_path(police_area) # debug use
        print(f"(儲存最佳路徑) 警車區域: {police_area}    最佳路徑: {best_path}")
        return "ok", 200
    except Exception as e:
        print("Error:", e)
        return "error", 500

@app.route("/esp32/best-path", methods=["GET"])
def get_best_path():
    police_area = request.args.get("police", "G")
    best_path = road_tracer.get_best_path(police_area)
    print(f"請求 {police_area} 區域警車支援，最佳路徑: {best_path}")
    return best_path, 200


@app.post("/webhook")
def webhook():
    body = request.get_data(as_text=True)
    signature = request.headers.get("X-Line-Signature", "")

    try:
        line_helper.handler.handle(body, signature)
    except InvalidSignatureError:
        abort(400)
    except Exception:
        traceback.print_exc()
        return "Internal Server Error", 500

    return "OK", 200


@app.get("/notify")
def notify():
    line_helper.notify()
    return jsonify({"status": "success"}), 200

@app.route("/esp32/audio-count", methods=["GET"])
def audio_count():
    return str(len(audio_files)), 200

@app.route("/esp32/audio-download", methods=["GET"])
def audio_download():
    index = request.args.get("index")
    filename = f"./static/audio/{audio_files[int(index)]}.wav"
    return send_file(
        filename,
        mimetype="audio/wav"
    )

@app.route("/esp32/check-poo", methods=["POST"])
def check_poo():
    device_id = request.headers.get("X-Device-ID")
    byte_data = request.get_data()
    print(f"收到便便照片, device_id: {device_id}, 資料大小: {len(byte_data)} bytes")
    
    image_queue.put(byte_data, timeout=1)

    image_array = np.frombuffer(byte_data, dtype=np.uint8)
    image = cv2.imdecode(image_array, cv2.IMREAD_COLOR)
    results = poo_model.predict(image, verbose=False)
    result = results[0]
    
    class_id = int(result.boxes[0].cls[0]) if len(result.boxes) > 0 else -1
    class_name = result.names[class_id] if class_id != -1 else "未偵測到便便"
    print(f"便便類型: {class_name} (class_id: {class_id})")
    return poo_type_map[class_id], 200

@app.route("/esp32/urgent-call", methods=["GET"])
def urgent_call():
    device_id = request.headers.get("X-Device-ID")
    # device_id = "debug_1"
    address = "測試地址"
    print(f"收到緊急呼叫, device_id: {device_id}")

    user_id = os.environ["LINE_DEBUG_USER_ID"]
    group_id = os.environ["LINE_DEBUG_GROUP_ID"]
    text = f"🚨廁所裝置 {device_id} 發出緊急呼叫！\n\n{{family}} 請立刻致電關心！\n\n {{hospital}} 請立刻派人到 {address}"

    line_helper.notify()

    return jsonify({"status": "success"}), 200

@app.route("/csi", methods=["GET"])
def csi_index():
    return render_template("csi-display.html")

@app.route("/csi-reset", methods=["GET"])
def csi_reset():
    state_machine.reset_warnings()
    return "ok"

@app.route("/esp32/csi-state", methods=["GET"])
def get_csi_state():
    return csi_state.copy()

@app.route("/esp32/csi-radar", methods=["POST"])
def receive_csi_radar():
    data = request.get_json()

    if not data:
        return jsonify({
            "success": False,
            "message": "No JSON data received"
        }), 400

    timestamp = datetime.now()
    someone = data.get("someone")
    motion = data.get("motion")
    print(f"CSI received: someone: {someone}    motion:{motion}    time: {timestamp}")

    csi_state["someone"] = someone
    csi_state["motion"] = motion
    csi_state["timestamp"] = timestamp
    state_machine.update(someone, motion)

    return jsonify({
        "success": True,
        "message": "Motion event received"
    }), 200

def csi_monitor():
    while True:
        state_machine.check_long_static(seconds=5)
        snapshot = state_machine.snapshot()
        csi_state["state"] = snapshot["state"]
        csi_state["fast_empty"] = snapshot["fast_empty"]
        csi_state["long_static"] = snapshot["long_static"]
        csi_state["last_static"] = snapshot["last_static"]
        time.sleep(0.2)

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
    
    alert_thread = threading.Thread(
        target=csi_monitor,
        daemon=True
    )
    alert_thread.start()

    display_images(detect_objects=True)