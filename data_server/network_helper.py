NETWORK_INFO = {
    "ssid": "iPhone-YJL",
    "password": "12345678",
    "ip": "172.20.10.14",
    "port": "5000"
}

API_ROOT = f"http://{NETWORK_INFO['ip']}:{NETWORK_INFO['port']}/esp32"

PURPOSE_API = {
    "img_upload": [f"{API_ROOT}/image-upload"],
    "img_inference": [f"{API_ROOT}/image-inference"],
    "audio_ars": [f"{API_ROOT}/audio-ars"],
    "audio_tts": [f"{API_ROOT}/audio-tts"],
    "auto_car": [
        f"{API_ROOT}/target-gps",
        f"{API_ROOT}/shortest-path",
    ],
}

def get_network_info(purpose: str):
    if purpose not in PURPOSE_API:
        raise ValueError(f"Invalid purpose: {purpose}. Must be one of {list(PURPOSE_API.keys())}")
    
    result = {
        "ssid": NETWORK_INFO["ssid"],
        "password": NETWORK_INFO["password"],
        "api_urls": PURPOSE_API[purpose]
    }
    return result