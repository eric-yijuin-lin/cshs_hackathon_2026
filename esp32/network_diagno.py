import network
import urequests
import time

WIFI_STATUS = {
    network.STAT_IDLE: "STAT_IDLE",
    network.STAT_CONNECTING: "STAT_CONNECTING",
    network.STAT_GOT_IP: "STAT_GOT_IP",
    network.STAT_WRONG_PASSWORD: "STAT_WRONG_PASSWORD",
    network.STAT_NO_AP_FOUND: "STAT_NO_AP_FOUND",
    network.STAT_CONNECT_FAIL: "STAT_CONNECT_FAIL",
}

WIFI_SUGGETSTION = {
    network.STAT_IDLE: "閒置中，如果確定有執行 wifi.connect() 請等待",
    network.STAT_CONNECTING: "連線中，請等待",
    network.STAT_GOT_IP: "已經取得 IP，請等待",
    network.STAT_WRONG_PASSWORD: "密碼錯誤，請檢查密碼是否有錯",
    network.STAT_NO_AP_FOUND: "找不到 WIFI 熱點，請檢查 SSID 是否有錯",
    network.STAT_CONNECT_FAIL: "連線失敗，請或嘗試重開熱點與 ESP32",
}

def socket_check(host, port, timeout=10):
    import socket
    print("\n===== SOCKET CHECK =====")
    print("Host:", host)
    print("Port:", port)

    sock = None
    try:
        # DNS resolution
        print("[DNS] resolving...")

        addr_info = socket.getaddrinfo(
            host,
            port
        )

        if addr_info:
            print("[ADD]", addr_info)
        else:
            print("[DNS] failed: no address")
            return False

        address = addr_info[0][-1]
        print("[DNS] OK:", address)

        # TCP connection
        print("[TCP] connecting...")
        sock = socket.socket()
        sock.settimeout(timeout)
        sock.connect(address)
        print("[TCP] OK")

        return True

    except Exception as e:
        print("[SOCKET] FAIL:")
        print(type(e))
        print(repr(e))

        return False

    finally:
        if sock:
            try:
                sock.close()
            except:
                pass

# 連線 Wi-Fi

wifi = network.WLAN(network.STA_IF)
wifi.disconnect()
time.sleep(1)
wifi.active(False)
time.sleep(1)

wifi.active(True)
wifi.connect("iPhone-YJL", "123456789")
print("connnectiing to wifi...")
while not wifi.isconnected():
    status = WIFI_STATUS.get(wifi.status(), "UNKNOWN_STATUS")
    suggestion = WIFI_SUGGETSTION.get(wifi.status(), "UNKNOWN_STATUS")
    print(f"WIFI 狀態: {status}")
    print(f"WIFI 建議動作: {suggestion}")
    time.sleep(1)

print("Wi-Fi 已連線:", wifi.ifconfig())

# 發送 HTTP GET 請求
host = "172.25.216.180"
port = 5000
path = "/hello"
url = f"http://{host}:{port}{path}"
try:
    print(f"requesting to: {url}")
    res = urequests.get(url)
    print(res.text)
except Exception as e:
    print("type =", type(e))
    print("str  =", str(e))
    print("repr =", repr(e))
    print("args =", e.args[0])
    
    if e.args[0] == 113:
        socket_check(host, port)


