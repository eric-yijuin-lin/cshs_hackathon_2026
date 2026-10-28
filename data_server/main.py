import os
import threading
import queue
from pathlib import Path
from datetime import datetime

import cv2
import numpy as np
from dotenv import load_dotenv
from flask import Flask, jsonify, request, render_template, abort
from ultralytics import YOLO

from linebot.v3 import WebhookHandler
from linebot.v3.exceptions import InvalidSignatureError
from linebot.v3.messaging import (
    Configuration,
    ApiClient,
    MessagingApi,
    ReplyMessageRequest,
    TextMessage,
    PushMessageRequest
)
from linebot.v3.webhooks import MessageEvent, TextMessageContent
from linebot.v3.messaging import MessagingApiBlob
from linebot.v3.webhooks import (
    ImageMessageContent,
    AudioMessageContent,
)

import network_helper
from roadtrace.tracer import PathTracer

load_dotenv()

app = Flask(__name__)

configuration = Configuration(
    access_token=os.environ["LINE_CHANNEL_ACCESS_TOKEN"]
)

handler = WebhookHandler(
    os.environ["LINE_CHANNEL_SECRET"]
)

image_queue = queue.Queue(maxsize=2)
road_tracer = PathTracer()

MODES = {"yolo", "upload", "agent"}
user_modes = {}

def display_images(detect_objects: bool):
    model = YOLO("./ai/yolo/YOLO26s.pt") if detect_objects else None
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
    device_id = request.headers.get("X-Device-ID", "Device-A")
    with open("./test.jpg", "rb") as f:
        img_bytes = f.read()
    road_tracer.trace_plate(device_id, img_bytes)
    return "ok"

@app.post("/webhook")
def webhook():
    body = request.get_data(as_text=True)
    signature = request.headers.get("X-Line-Signature", "")

    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        abort(400)

    return "OK", 200



@handler.add(MessageEvent, message=TextMessageContent)
def handle_text_message(event):
    user_id = event.source.user_id
    user_text = event.message.text

    print(f"收到 LINE 訊息：{user_text}")

    # 判斷是否為指令
    if user_text.startswith(("/", "／")):
        command = user_text[1:].strip().lower()

        if command in MODES:
            user_modes[user_id] = command
            reply_text = f"已切換至 {command} 模式"
        else:
            reply_text = f"未知指令：{command}"

    else:
        reply_text = f"Flask 收到：{user_text}"

    # 回覆 LINE 訊息
    with ApiClient(configuration) as api_client:
        line_bot_api = MessagingApi(api_client)

        line_bot_api.reply_message(
            ReplyMessageRequest(
                reply_token=event.reply_token,
                messages=[
                    TextMessage(text=reply_text)
                ],
            )
        )

@handler.add(MessageEvent, message=ImageMessageContent)
def handle_image_message(event):
    message_id = event.message.id

    # 從 LINE 下載圖片
    with ApiClient(configuration) as api_client:
        blob_api = MessagingApiBlob(api_client)
        image_data = blob_api.get_message_content(message_id)

    # 建立儲存資料夾
    upload_dir = Path("uploads")
    upload_dir.mkdir(exist_ok=True)

    # 儲存圖片
    image_path = upload_dir / f"{message_id}.jpg"
    image_path.write_bytes(image_data)

    print(f"圖片已儲存：{image_path}")

    # 回覆使用者
    with ApiClient(configuration) as api_client:
        line_bot_api = MessagingApi(api_client)

        line_bot_api.reply_message(
            ReplyMessageRequest(
                reply_token=event.reply_token,
                messages=[
                    TextMessage(text="圖片已儲存！")
                ],
            )
        )

@handler.add(MessageEvent, message=AudioMessageContent)
def handle_audio_message(event):
    message_id = event.message.id
    duration = event.message.duration

    # 從 LINE 下載音訊
    with ApiClient(configuration) as api_client:
        blob_api = MessagingApiBlob(api_client)
        audio_data = blob_api.get_message_content(message_id)

    # 建立儲存資料夾
    upload_dir = Path("uploads")
    upload_dir.mkdir(exist_ok=True)

    # 儲存音訊
    audio_path = upload_dir / f"{message_id}.m4a"
    audio_path.write_bytes(audio_data)

    print(f"語音已儲存：{audio_path}")
    print(f"語音長度：{duration} ms")

    # 回覆使用者
    with ApiClient(configuration) as api_client:
        line_bot_api = MessagingApi(api_client)

        line_bot_api.reply_message(
            ReplyMessageRequest(
                reply_token=event.reply_token,
                messages=[
                    TextMessage(text="語音已儲存！")
                ],
            )
        )

@app.get("/notify")
def notify():
    user_id = os.environ["LINE_DEBUG_USER_ID"]

    with ApiClient(configuration) as api_client:
        line_bot_api = MessagingApi(api_client)

        line_bot_api.push_message(
            PushMessageRequest(
                to=user_id,
                messages=[
                    TextMessage(text="這是 Flask 主動推送的測試訊息！")
                ],
            )
        )

    return {"status": "sent"}

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