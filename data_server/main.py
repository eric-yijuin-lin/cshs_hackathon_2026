from flask import Flask, jsonify, request, render_template
from datetime import datetime
import os
print("current working directory:", os.getcwd())

app = Flask(__name__)
app.network_info = {
    "ssid": "iPhone-YJL",
    "password": "12345678",
    "ip": "172.20.10.14",
    "port": "5000",
    "server_url": "http://172.20.10.14:5000",
}

@app.route("/hello", methods=["GET"])
def hello():
    return jsonify({"message": "hello"})

@app.route("/get-network-info", methods=["GET"])
def get_network_info():
    return jsonify(app.network_info)

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
        app.network_info["server_url"] = f"http://{app.network_info['ip']}:{app.network_info['port']}"

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

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)