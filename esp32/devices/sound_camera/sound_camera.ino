#include <WiFiClient.h>
#include <HTTPClient.h>
#include <networkHelper.h>
#include <cameraSetup.h>
#include <SoundLevel.h>

#define SOUND_THRESHOLD 90.0

char* deviceID = "Device-A";

NetworkConfig networkConfig;

SoundLevel sound(
  42, // SCK
  41, // WS
  21, // SD
  104.0, // offset_L
  104.0 //offset_R
);

void setup() {
  Serial.begin(115200);
  Serial.print("wait 5 sec to avoid brown out.");
  delay(5000);

  bool network_ok = true;
  bool camera_ok = true;
  bool sound_ok = true;

  if (!initNetwork("sound_snapshot", networkConfig)) { // 連接 wifi
    Serial.println("Failed to initialize network.");
    network_ok = false;
  }
  delay(1000);

  if (!initCamera()) { 
    Serial.println("Failed to initialize camera.");
    camera_ok = false;
  }
  delay(1000);

  if (!sound.begin()) {
    Serial.println("Failed to initialize sound sensor.");
    sound_ok = false;
  }

  if (network_ok && camera_ok && sound_ok) {
    Serial.println("All devices initialized successfully.");
  } else {
    Serial.println("Initialization failed, restart after 10 seconds...");
    delay(10000);
    ESP.restart();
  }
}

void loop() {
  // Serial.println("TEST");
  // delay(1000);
  SoundReading micL, micR;
  if (sound.update(micL, micR))
  {
    // 暫時只用左聲道的數據
    Serial.printf("Mic L SPL: %.1f\n", micL.dbSPL);
    Serial.printf("Mic L dBA: %.1f\n", micL.dBA);
    
    if (micL.dbSPL > SOUND_THRESHOLD) {
      Serial.println("Sound level exceeded threshold, capturing image...");
      captureAndSendImage(networkConfig, micL.dbSPL);
    }
  }
}

bool captureAndSendImage(NetworkConfig config, double soundLevel) {
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
    String uploadUrl = networkConfig.api_urls[0]; // purpose 為 img_inference，使用 api_urls[0] 作為上傳 URL

    Serial.printf("Uploading to: %s\n", uploadUrl.c_str());
    if (!http.begin(client, uploadUrl)) {
        Serial.println("HTTP begin failed");
        esp_camera_fb_return(fb);
        return false;
    }

    // 3. 告訴 Server：Body 就是一張 JPEG
    http.addHeader("Content-Type", "image/jpeg");
    http.addHeader("X-Device-ID", deviceID);
    http.addHeader("X-Sound-Level", String(soundLevel));

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