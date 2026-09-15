
#include <WiFiClientSecure.h>
#include <WiFiClient.h>
#include <HTTPClient.h>
#include "cameraSetup.h"
#include "networkSetup.h"

NetworkConfig networkConfig;

// String workingSSID = "";
// String workingPassword = "";
// String workingServerUrl = "";

const int serverPort = 80;
const int cameraInitRetry = 10;
const int httpInterval = 5000;

void avoidBrownOut(int seconds);
String getServerName();
bool takeAndUploadPhoto();

void setup() {
  Serial.begin(115200);
  initCamera(); // 設定並初始化相機
  avoidBrownOut(5); // 等待數秒避免電壓不穩
  if (!initNetwork(networkConfig)) { // 連接 wifi
    Serial.println("Failed to initialize network. Restart after 5 seconds.");
    delay(5000);
    ESP.restart();
  }
}

void loop() {
  takeAndUploadPhoto();
  delay(httpInterval);
}


void avoidBrownOut(int seconds) {
  // 不關閉 brown out detector，避免電壓不夠 esp32 硬撐找不到 bug
  // WRITE_PERI_REG(RTC_CNTL_BROWN_OUT_REG, 0); 
  Serial.print("waiting for a moment, avoiding brown out");
  for (int i=0; i<seconds; i++)
  {
    Serial.print(".");
    delay(1000);
  }
  Serial.println();
}

bool takeAndUploadPhoto() {
    // 1. 拍照
    unsigned long captureStart = millis();

    camera_fb_t* fb = esp_camera_fb_get();

    if (!fb) {
        Serial.println("Camera capture failed");
        return false;
    }

    unsigned long captureTime = millis() - captureStart;

    Serial.printf("Capture OK\n");
    Serial.printf("JPEG size: %u bytes\n", fb->len);
    Serial.printf("Capture time: %lu ms\n", captureTime);

    // 確認目前拿到的是 JPEG
    if (fb->format != PIXFORMAT_JPEG) {
        Serial.println("Captured image is not JPEG");
        esp_camera_fb_return(fb);
        return false;
    }

    // 2. 建立 HTTP Client
    WiFiClient client;
    HTTPClient http;
    String uploadUrl = workingServerUrl + "/esp32/image-upload";

    Serial.printf("Uploading to: %s\n", uploadUrl.c_str());
    if (!http.begin(client, uploadUrl)) {
        Serial.println("HTTP begin failed");
        esp_camera_fb_return(fb);
        return false;
    }

    // 3. 告訴 Server：Body 就是一張 JPEG
    http.addHeader("Content-Type", "image/jpeg");
    http.addHeader("X-Device-ID", deviceID);

    // 4. 直接把 framebuffer 當 POST body
    unsigned long uploadStart = millis();

    int httpCode = http.POST(fb->buf, fb->len);

    unsigned long uploadTime = millis() - uploadStart;

    // 5. 檢查結果
    if (httpCode > 0) {
        Serial.printf("HTTP response: %d\n", httpCode);
        Serial.printf("Upload time: %lu ms\n", uploadTime);

        String response = http.getString();
        Serial.printf("Server response: %s\n", response.c_str());
    }
    else {
        Serial.printf(
            "HTTP POST failed: %s\n",
            http.errorToString(httpCode).c_str()
        );
    }

    // 6. 關閉 HTTP
    http.end();

    // 7. 非常重要：把 framebuffer 還給 Camera
    esp_camera_fb_return(fb);

    return httpCode >= 200 && httpCode < 300;
}